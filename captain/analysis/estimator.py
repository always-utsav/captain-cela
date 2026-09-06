"""CELA causal estimation — CEE + paired replay + bottleneck.

Implements the core CELA causal estimation pipeline:

1. Controlled paired replay (factual vs counterfactual)
2. CEE (Counterfactual Evidence-Flow Effect) estimation
3. Uncertainty quantification
4. Propagation profile
5. Bottleneck identification

**CEE measures the observed difference under the specified
intervention and replay assumptions.**

It does NOT prove the channel is "the true cause."

The correct interpretation is:
    "Under the specified intervention, execution environment,
    replay protocol, and evaluator, blocking this evidence-flow
    channel changed the measured failure outcome by CEE."

**Stage 14 does NOT implement:**
- Cascade optimization (Stage 15)
- Benchmark suites (Stage 16)
- Semantic provenance
"""

from __future__ import annotations

import enum
import math
import random
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from captain.agent.tools import ToolRegistry, create_default_tool_registry
from captain.evidence.graph import EvidenceFlowGraph
from captain.failures.model import Candidate, ChannelIntervention
from captain.intervention.model import Intervention, InterventionSet, InterventionType
from captain.models.enums import EventType
from captain.models.execution import ExecutionRun
from captain.models.ids import _is_deterministic, _next_deterministic_id
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

# ===================================================================
# ID generation
# ===================================================================


def _gen_trial_id() -> str:
    if _is_deterministic():
        return _next_deterministic_id("trial_")
    return f"trial_{uuid.uuid4().hex}"


def _gen_result_id() -> str:
    if _is_deterministic():
        return _next_deterministic_id("cee_")
    return f"cee_{uuid.uuid4().hex}"


# ===================================================================
# Outcome model
# ===================================================================


class Outcome(BaseModel):
    """Binary failure outcome for a single run.

    Y=1: failure occurred.  Y=0: failure did not occur.
    """

    run_id: str
    failed: bool
    evaluator: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Paired trial
# ===================================================================


class TrialStatus(enum.StrEnum):
    SUCCESS = "success"
    REPLAY_ERROR = "replay_error"
    INVALID_INTERVENTION = "invalid_intervention"


class PairedTrial(BaseModel):
    """One paired factual/counterfactual experiment.

    Does NOT duplicate ExecutionRun contents — stores IDs only.
    """

    trial_id: str = Field(default_factory=_gen_trial_id)
    baseline_run_id: str
    counterfactual_run_id: str = ""
    candidate_id: str = ""
    intervention_id: str = ""
    baseline_outcome: bool = False
    counterfactual_outcome: bool = False
    status: TrialStatus = TrialStatus.SUCCESS
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# CEE result
# ===================================================================


class CEEResult(BaseModel):
    """Estimated Counterfactual Evidence-Flow Effect.

    CEE(e) = P(Y=1) - P(Y=1|do(C_e=∅))

    Positive: blocking reduces failure probability.
    Zero: no measured change.
    Negative: blocking increases failure probability.
    """

    result_id: str = Field(default_factory=_gen_result_id)
    candidate_id: str
    source_evidence_id: str = ""
    target_evidence_id: str = ""
    cee: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    num_trials: int = 0
    num_valid_trials: int = 0
    trials: list[PairedTrial] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Propagation profile
# ===================================================================


class PropagationProfile(BaseModel):
    """CEE values along a candidate lineage.

    For L = (e1, ..., ek): Π(L) = [CEE(e1), ..., CEE(ek)]
    """

    edge_ids: list[str] = Field(default_factory=list)
    cee_values: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Bottleneck result
# ===================================================================


class BottleneckResult(BaseModel):
    """Estimated causal propagation bottleneck.

    The candidate with strongest supported measured effect.
    Subject to documented replay and evaluator assumptions.
    """

    candidate_id: str = ""
    source_evidence_id: str = ""
    target_evidence_id: str = ""
    cee: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    num_trials: int = 0
    supported: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Channel-to-event bridge
# ===================================================================


def channel_to_intervention(
    channel: ChannelIntervention,
    baseline_run: ExecutionRun,
    evidence_graph: EvidenceFlowGraph | None = None,
) -> Intervention:
    """Bridge a channel intervention to a Stage 9 event intervention.

    **Stage 14.1 — True channel-level intervention.**

    When an EvidenceFlowGraph is provided, this function resolves the
    SOURCE evidence's producing event and targets it directly:

    - If the source was produced by a TOOL_RESULT event, uses
      TOOL_RESULT_OVERRIDE on that specific event.  This blocks
      only A's contribution while preserving C→B (where C was
      produced by a different event).

    - If the source was produced by a REASONING/OUTPUT/PLANNING
      event, uses EVENT_OUTPUT_OVERRIDE on the source's producing
      event.

    **Why this achieves channel-level semantics:**
    Each tool call produces a distinct TOOL_RESULT event.  Overriding
    one tool's result event does NOT affect other tools' results.
    Therefore BLOCK(A→B) preserves C→B when A and C come from
    different tool results.

    **Remaining limitation:** If two channels originate from the SAME
    source event (same TOOL_RESULT or same REASONING step produces
    multiple artifacts), overriding that event blocks all channels
    from that source.  In the Stage 1 reference agent, each tool call
    produces exactly one result artifact, so this does not arise for
    tool-mediated channels.

    When no EvidenceFlowGraph is provided, falls back to event-level
    override on the mediating event (pre-14.1 behavior).
    """
    # --- True channel-level path (Stage 14.1) ---
    if evidence_graph is not None:
        source_evi = evidence_graph.get_evidence(channel.source_evidence_id)
        if source_evi is not None:
            source_event_id = source_evi.creation_event_id
            source_event = None
            for evt in baseline_run.events:
                if evt.event_id == source_event_id:
                    source_event = evt
                    break

            if source_event is not None:
                # Determine target event and intervention type
                target_event_id = source_event_id
                intv_type = InterventionType.EVENT_OUTPUT_OVERRIDE

                if source_event.event_type == EventType.TOOL_RESULT:
                    intv_type = InterventionType.TOOL_RESULT_OVERRIDE
                    target_event_id = source_event_id
                elif source_event.event_type == EventType.TOOL_CALL:
                    # Source evidence produced by TOOL_CALL; find the
                    # corresponding TOOL_RESULT child event (replay engine
                    # requires TOOL_RESULT_OVERRIDE targets TOOL_RESULT).
                    for evt in baseline_run.events:
                        if (
                            evt.event_type == EventType.TOOL_RESULT
                            and evt.parent_event_id == source_event_id
                        ):
                            target_event_id = evt.event_id
                            intv_type = InterventionType.TOOL_RESULT_OVERRIDE
                            break

                return Intervention(
                    intervention_type=intv_type,
                    baseline_run_id=channel.baseline_run_id,
                    target_id=target_event_id,
                    replacement_value="",
                    description=(
                        f"Channel BLOCK: {channel.source_evidence_id[:16]}"
                        f"→{channel.target_evidence_id[:16]}"
                        f" via source {target_event_id[:16]}"
                    ),
                    metadata={
                        "channel_intervention_id": channel.intervention_id,
                        "source_evidence_id": channel.source_evidence_id,
                        "target_evidence_id": channel.target_evidence_id,
                        "source_event_id": source_event_id,
                        "target_event_id": target_event_id,
                        "source_event_type": source_event.event_type.value,
                        "intervention_type": "channel_block",
                        "channel_level": True,
                        "mechanism": (
                            "Targets source evidence producing event, "
                            "not mediating event. Preserves other channels "
                            "through the same mediating event."
                        ),
                    },
                )

    # --- Fallback: event-level (pre-14.1 behavior) ---
    return Intervention(
        intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
        baseline_run_id=channel.baseline_run_id,
        target_id=channel.event_id,
        replacement_value="",
        description=(
            f"Channel BLOCK (event-level fallback): "
            f"{channel.source_evidence_id[:16]}"
            f"→{channel.target_evidence_id[:16]} via {channel.event_id[:16]}"
        ),
        metadata={
            "channel_intervention_id": channel.intervention_id,
            "source_evidence_id": channel.source_evidence_id,
            "target_evidence_id": channel.target_evidence_id,
            "intervention_type": "channel_block",
            "channel_level": False,
            "mechanism": (
                "Event-level fallback. If the mediating event has "
                "multiple independent channels, all are affected."
            ),
        },
    )


# ===================================================================
# Failure evaluator type
# ===================================================================

FailureEvaluator = Callable[[ExecutionRun], bool]
"""A function that returns True if the run failed.

Ground-truth or deterministic evaluators are preferred.
Do NOT use an LLM judge as the authoritative evaluator.
"""


# ===================================================================
# CEE Estimator
# ===================================================================


class CEEEstimator:
    """Estimates Counterfactual Evidence-Flow Effect via paired replay.

    Usage::

        estimator = CEEEstimator(
            baseline_run=run,
            evaluator=my_evaluator,
        )
        result = estimator.estimate(candidate, channel_intervention)
    """

    def __init__(
        self,
        baseline_run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        evidence_graph: EvidenceFlowGraph | None = None,
        tool_registry: ToolRegistry | None = None,
        num_trials: int = 1,
        confidence_level: float = 0.95,
    ) -> None:
        self._baseline = baseline_run
        self._evaluator = evaluator
        self._graph = evidence_graph
        self._registry = tool_registry or create_default_tool_registry()
        self._num_trials = max(1, num_trials)
        self._confidence_level = confidence_level

    def estimate(
        self,
        candidate: Candidate,
        channel_intervention: ChannelIntervention,
    ) -> CEEResult:
        """Estimate CEE for a candidate channel via paired replay.

        Returns a CEEResult with point estimate, confidence interval,
        and trial details.
        """
        trials: list[PairedTrial] = []
        baseline_failed = self._evaluator(self._baseline)

        for _ in range(self._num_trials):
            trial = self._run_paired_trial(candidate, channel_intervention, baseline_failed)
            trials.append(trial)

        valid = [t for t in trials if t.status == TrialStatus.SUCCESS]
        n_valid = len(valid)

        if n_valid == 0:
            return CEEResult(
                candidate_id=candidate.candidate_id,
                source_evidence_id=candidate.source_evidence_id,
                target_evidence_id=candidate.target_evidence_id,
                cee=0.0,
                num_trials=len(trials),
                num_valid_trials=0,
                trials=trials,
            )

        # CEE_hat = (1/N) Σ [Y_r - Y_r_cf]
        diffs = [
            (1 if t.baseline_outcome else 0) - (1 if t.counterfactual_outcome else 0)
            for t in valid
        ]
        cee_hat = sum(diffs) / n_valid

        ci_lo, ci_hi = self._confidence_interval(diffs, n_valid)

        return CEEResult(
            candidate_id=candidate.candidate_id,
            source_evidence_id=candidate.source_evidence_id,
            target_evidence_id=candidate.target_evidence_id,
            cee=cee_hat,
            ci_lower=ci_lo,
            ci_upper=ci_hi,
            num_trials=len(trials),
            num_valid_trials=n_valid,
            trials=trials,
        )

    def _run_paired_trial(
        self,
        candidate: Candidate,
        channel_intervention: ChannelIntervention,
        baseline_failed: bool,
    ) -> PairedTrial:
        """Execute one paired trial."""
        # Bridge channel → event intervention (true channel-level when graph available)
        event_intv = channel_to_intervention(channel_intervention, self._baseline, self._graph)
        iset = InterventionSet(
            baseline_run_id=self._baseline.run_id,
            interventions=[event_intv],
        )

        # Execute counterfactual replay
        result = CounterfactualReplayEngine.replay(
            self._baseline,
            iset,
            tool_registry=self._registry,
        )

        if result.status == ReplayStatus.REJECTED:
            return PairedTrial(
                baseline_run_id=self._baseline.run_id,
                candidate_id=candidate.candidate_id,
                intervention_id=channel_intervention.intervention_id,
                baseline_outcome=baseline_failed,
                status=TrialStatus.INVALID_INTERVENTION,
                error_message=result.rejection_reason or "Intervention rejected",
            )

        if result.status == ReplayStatus.FAILED or result.counterfactual_run is None:
            return PairedTrial(
                baseline_run_id=self._baseline.run_id,
                candidate_id=candidate.candidate_id,
                intervention_id=channel_intervention.intervention_id,
                baseline_outcome=baseline_failed,
                status=TrialStatus.REPLAY_ERROR,
                error_message=result.rejection_reason or "Replay failed",
            )

        cf_run = result.counterfactual_run
        cf_failed = self._evaluator(cf_run)

        return PairedTrial(
            baseline_run_id=self._baseline.run_id,
            counterfactual_run_id=cf_run.run_id,
            candidate_id=candidate.candidate_id,
            intervention_id=channel_intervention.intervention_id,
            baseline_outcome=baseline_failed,
            counterfactual_outcome=cf_failed,
            status=TrialStatus.SUCCESS,
            metadata={
                "baseline_run_id": self._baseline.run_id,
                "counterfactual_run_id": cf_run.run_id,
                "parent_run_id": cf_run.parent_run_id or "",
            },
        )

    def _confidence_interval(
        self,
        diffs: list[int],
        n: int,
    ) -> tuple[float, float]:
        """Compute confidence interval for paired binary diffs.

        For N=1: no meaningful interval, returns point estimate.
        For small N: paired bootstrap.
        """
        if n <= 1:
            point = sum(diffs) / max(n, 1)
            return (point, point)

        # Paired bootstrap CI
        rng = random.Random(42)  # Deterministic seed  # noqa: S311
        n_boot = 1000
        boot_means: list[float] = []

        for _ in range(n_boot):
            sample = [rng.choice(diffs) for _ in range(n)]
            boot_means.append(sum(sample) / n)

        boot_means.sort()
        alpha = 1.0 - self._confidence_level
        lo_idx = max(0, math.floor(alpha / 2 * n_boot))
        hi_idx = min(n_boot - 1, math.ceil((1 - alpha / 2) * n_boot) - 1)

        return (boot_means[lo_idx], boot_means[hi_idx])


# ===================================================================
# Bottleneck analyzer
# ===================================================================


class BottleneckAnalyzer:
    """Identifies the estimated causal propagation bottleneck.

    Selects the candidate with the highest supported CEE.
    """

    @staticmethod
    def select(
        results: list[CEEResult],
        *,
        min_trials: int = 1,
    ) -> BottleneckResult:
        """Select the bottleneck from CEE results.

        Only candidates with >= min_trials valid trials are eligible.
        Ties are broken deterministically by candidate_id.

        Returns unsupported result if no candidate qualifies.
        """
        eligible = [
            r for r in results if r.num_valid_trials >= min_trials and r.num_valid_trials > 0
        ]

        if not eligible:
            return BottleneckResult(supported=False)

        # Sort by CEE descending, then candidate_id for determinism
        eligible.sort(key=lambda r: (-r.cee, r.candidate_id))
        best = eligible[0]

        return BottleneckResult(
            candidate_id=best.candidate_id,
            source_evidence_id=best.source_evidence_id,
            target_evidence_id=best.target_evidence_id,
            cee=best.cee,
            ci_lower=best.ci_lower,
            ci_upper=best.ci_upper,
            num_trials=best.num_valid_trials,
            supported=True,
        )

    @staticmethod
    def propagation_profile(
        results: list[CEEResult],
    ) -> PropagationProfile:
        """Build propagation profile from ordered results.

        For L = (e1, ..., ek): Π(L) = [CEE(e1), ..., CEE(ek)]
        """
        sorted_results = sorted(results, key=lambda r: r.candidate_id)
        return PropagationProfile(
            edge_ids=[r.candidate_id for r in sorted_results],
            cee_values=[r.cee for r in sorted_results],
        )
