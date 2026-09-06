"""CELA cascade intervention — set-level CEE + greedy selection.

Stage 15 extends individual channel-level CEE (Stage 14) to
**set-level** intervention:

    CEE(S)  =  P(Y=1) - P(Y=1 | do(C_S))

where S = {e1, ..., ek} is a set of evidence-flow channels.

**CEE(S) is NOT computed by summing individual CEE values.**

    CEE(S) != Sum CEE(e)

Set-level effects are estimated through REAL joint counterfactual
replay: all channels in S are blocked in a SINGLE counterfactual
execution, and the evaluator confirms the outcome.

**Stage 15 does NOT claim:**

- global optimality of selected sets;
- minimum intervention sets;
- formal causal interaction decomposition.

The greedy selection finds the **best supported set under the
configured search procedure**, not a provably optimal set.

**Stage 15 does NOT implement:**

- Benchmark suites (Stage 16)
- Semantic provenance
- External LLM services
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from pydantic import BaseModel, Field

from captain.agent.tools import ToolRegistry, create_default_tool_registry
from captain.analysis.estimator import (
    FailureEvaluator,
    PairedTrial,
    TrialStatus,
    channel_to_intervention,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.failures.model import ChannelIntervention
from captain.intervention.model import Intervention, InterventionSet
from captain.models.execution import ExecutionRun
from captain.models.ids import _is_deterministic, _next_deterministic_id
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

# ===================================================================
# ID generation
# ===================================================================


def _gen_set_id() -> str:
    if _is_deterministic():
        return _next_deterministic_id("iset_")
    return f"iset_{uuid.uuid4().hex}"


def _gen_cascade_id() -> str:
    if _is_deterministic():
        return _next_deterministic_id("casc_")
    return f"casc_{uuid.uuid4().hex}"


def _gen_selection_id() -> str:
    if _is_deterministic():
        return _next_deterministic_id("sel_")
    return f"sel_{uuid.uuid4().hex}"


# ===================================================================
# Intervention set specification
# ===================================================================


class InterventionSetSpec(BaseModel):
    """Canonical specification for a set of channel interventions.

    References Stage 13 ChannelIntervention objects by ID and value.
    Does NOT duplicate full ExecutionRun/Evidence objects.

    Attributes:
        set_id: Unique ``iset_``-prefixed identifier.
        baseline_run_id: The observed run identity.
        channel_interventions: The channel interventions in this set.
        total_cost: Sum of intervention costs.
        validated: Whether all interventions passed validation.
        metadata: Additional context.
    """

    set_id: str = Field(default_factory=_gen_set_id)
    baseline_run_id: str
    channel_interventions: list[ChannelIntervention] = Field(default_factory=list)
    total_cost: float = 0.0
    validated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def intervention_count(self) -> int:
        """Number of channel interventions in this set."""
        return len(self.channel_interventions)

    @property
    def channel_intervention_ids(self) -> list[str]:
        """Sorted list of channel intervention IDs."""
        return sorted(ci.intervention_id for ci in self.channel_interventions)


# ===================================================================
# Cost model
# ===================================================================


class CostModel(BaseModel):
    """Configurable intervention cost model.

    **This is an experimental cost model, not a claim about
    real-world intervention difficulty.**

    Cost is additive:  Cost(S) = Sum cost(e)

    The default cost is 1.0 per channel.  Per-channel overrides
    can be specified via ``channel_costs``.

    If future work requires non-additive cost, the interface can
    be extended without breaking existing usage.

    Attributes:
        default_cost: Per-channel default cost.
        channel_costs: Optional per-intervention-id cost overrides.
    """

    default_cost: float = 1.0
    channel_costs: dict[str, float] = Field(default_factory=dict)

    def cost(self, channel: ChannelIntervention) -> float:
        """Return the cost for a single channel intervention."""
        return self.channel_costs.get(channel.intervention_id, self.default_cost)

    def total_cost(self, channels: list[ChannelIntervention]) -> float:
        """Return the total additive cost for a set of channels."""
        return sum(self.cost(c) for c in channels)


# ===================================================================
# Cascade result
# ===================================================================


class CascadeResult(BaseModel):
    """Set-level CEE result from joint counterfactual replay.

    CEE(S) is estimated from REAL paired joint outcomes.
    It is NOT calculated by summing individual CEE values.

    ``prevented`` is evaluator-confirmed: Y_baseline=1, Y_cf=0.
    Structural graph disconnection != observed causal prevention.

    Attributes:
        result_id: Unique ``casc_``-prefixed identifier.
        set_id: The InterventionSetSpec identity.
        baseline_run_id: The observed run.
        channel_intervention_ids: Sorted IDs of channels in the set.
        cee: CEE_hat(S) — set-level point estimate.
        ci_lower: Lower confidence bound.
        ci_upper: Upper confidence bound.
        num_trials: Total trials attempted.
        num_valid_trials: Trials with valid outcomes.
        trials: Individual paired trial records.
        total_cost: Sum of intervention costs.
        utility: U(S) = CEE(S) - lambda*Cost(S).
        prevented: Evaluator-confirmed prevention (Y_cf=0).
        prevention_rate: Fraction of valid trials where Y_cf=0.
        supported: Whether estimate is statistically supported.
        metadata: Additional context.
    """

    result_id: str = Field(default_factory=_gen_cascade_id)
    set_id: str = ""
    baseline_run_id: str = ""
    channel_intervention_ids: list[str] = Field(default_factory=list)
    cee: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    num_trials: int = 0
    num_valid_trials: int = 0
    trials: list[PairedTrial] = Field(default_factory=list)
    total_cost: float = 0.0
    utility: float = 0.0
    prevented: bool = False
    prevention_rate: float = 0.0
    supported: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Selection status
# ===================================================================


class SelectionStatus(enum.StrEnum):
    """Outcome status for greedy cascade selection."""

    SUCCESS = "success"
    NO_SUPPORTED_SOLUTION = "no_supported_solution"
    EVALUATION_BUDGET_EXHAUSTED = "evaluation_budget_exhausted"


# ===================================================================
# Marginal gain step
# ===================================================================


class MarginalGainStep(BaseModel):
    """Audit record for one greedy selection step.

    Preserves sufficient information to reconstruct:
    CEE(S), CEE(S U {e}), and D(e|S) for each candidate.
    """

    step_index: int = 0
    current_set_ids: list[str] = Field(default_factory=list)
    current_cee: float = 0.0
    candidate_id: str = ""
    candidate_cee_with: float = 0.0
    marginal_gain: float = 0.0
    candidate_cost: float = 0.0
    selected: bool = False
    reason: str = ""


# ===================================================================
# Selection result
# ===================================================================


class SelectionResult(BaseModel):
    """Output of greedy cascade intervention selection.

    The selected set is the **best supported set found under the
    configured search procedure**.  It is NOT claimed to be globally
    optimal.

    Attributes:
        selection_id: Unique ``sel_``-prefixed identifier.
        selected_set: The selected intervention set (None if none found).
        cascade_result: Set-level CEE for the selected set.
        selection_method: Always "greedy_marginal_gain".
        selection_steps: Audit trail of each greedy step.
        total_cost: Cost of selected set.
        utility: U(S) = CEE(S) - lambda*Cost(S).
        budget: Budget constraint (None if unconstrained).
        lambda_cost: Cost penalty weight.
        prevented: Evaluator-confirmed prevention.
        prevention_rate: Empirical prevention rate.
        status: Selection outcome status.
        evaluations_used: Total set-level evaluations performed.
        max_evaluations: Evaluation budget.
        metadata: Additional context.
    """

    selection_id: str = Field(default_factory=_gen_selection_id)
    selected_set: InterventionSetSpec | None = None
    cascade_result: CascadeResult | None = None
    selection_method: str = "greedy_marginal_gain"
    selection_steps: list[MarginalGainStep] = Field(default_factory=list)
    total_cost: float = 0.0
    utility: float = 0.0
    budget: float | None = None
    lambda_cost: float = 0.0
    prevented: bool = False
    prevention_rate: float = 0.0
    status: SelectionStatus = SelectionStatus.NO_SUPPORTED_SOLUTION
    evaluations_used: int = 0
    max_evaluations: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Cascade estimator
# ===================================================================


class CascadeEstimator:
    """Estimates set-level CEE via joint paired counterfactual replay.

    For an intervention set S = {e1, ..., ek}:

        CEE_hat(S) = (1/N) Sum [Y_r - Y_r_cf(S)]

    All channels in S are blocked in ONE counterfactual replay.
    CEE(S) is NOT calculated by summing individual CEE values.

    Structural graph disconnection != observed causal prevention.
    Prevention is evaluator-confirmed through actual replay.

    Usage::

        estimator = CascadeEstimator(
            baseline_run=run,
            evaluator=my_evaluator,
            evidence_graph=graph,
        )
        result = estimator.estimate_set(channels)
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
        lambda_cost: float = 0.0,
        cost_model: CostModel | None = None,
    ) -> None:
        self._baseline = baseline_run
        self._evaluator = evaluator
        self._graph = evidence_graph
        self._registry = tool_registry or create_default_tool_registry()
        self._num_trials = max(1, num_trials)
        self._confidence_level = confidence_level
        self._lambda_cost = lambda_cost
        self._cost_model = cost_model or CostModel()

    def estimate_set(
        self,
        channels: list[ChannelIntervention],
    ) -> CascadeResult:
        """Estimate set-level CEE via joint paired replay.

        All channels are blocked in ONE counterfactual execution.
        The evaluator confirms the outcome.

        Returns a CascadeResult with set-level CEE_hat(S),
        prevention status, utility, and trial details.
        """
        if not channels:
            return CascadeResult(
                baseline_run_id=self._baseline.run_id,
                supported=False,
                metadata={"reason": "empty_set"},
            )

        set_spec = InterventionSetSpec(
            baseline_run_id=self._baseline.run_id,
            channel_interventions=list(channels),
            total_cost=self._cost_model.total_cost(channels),
        )

        trials: list[PairedTrial] = []
        baseline_failed = self._evaluator(self._baseline)

        for _ in range(self._num_trials):
            trial = self._run_joint_trial(channels, baseline_failed)
            trials.append(trial)

        valid = [t for t in trials if t.status == TrialStatus.SUCCESS]
        n_valid = len(valid)

        if n_valid == 0:
            return CascadeResult(
                set_id=set_spec.set_id,
                baseline_run_id=self._baseline.run_id,
                channel_intervention_ids=set_spec.channel_intervention_ids,
                num_trials=len(trials),
                num_valid_trials=0,
                trials=trials,
                total_cost=set_spec.total_cost,
                supported=False,
            )

        # CEE_hat(S) = (1/N) Sum [Y_r - Y_r_cf(S)]
        diffs = [
            (1 if t.baseline_outcome else 0) - (1 if t.counterfactual_outcome else 0)
            for t in valid
        ]
        cee_hat = sum(diffs) / n_valid

        # Prevention: Y_baseline=1, Y_cf=0 (evaluator-confirmed)
        prevented_count = sum(
            1 for t in valid if t.baseline_outcome and not t.counterfactual_outcome
        )
        prevention_rate = prevented_count / n_valid

        # Confidence interval (reuse Stage 14 paired bootstrap logic)
        ci_lo, ci_hi = self._confidence_interval(diffs, n_valid)

        # Utility: U(S) = CEE(S) - lambda*Cost(S)
        total_cost = set_spec.total_cost
        utility = cee_hat - self._lambda_cost * total_cost

        return CascadeResult(
            set_id=set_spec.set_id,
            baseline_run_id=self._baseline.run_id,
            channel_intervention_ids=set_spec.channel_intervention_ids,
            cee=cee_hat,
            ci_lower=ci_lo,
            ci_upper=ci_hi,
            num_trials=len(trials),
            num_valid_trials=n_valid,
            trials=trials,
            total_cost=total_cost,
            utility=utility,
            prevented=prevention_rate > 0,
            prevention_rate=prevention_rate,
            supported=n_valid > 0,
        )

    def _run_joint_trial(
        self,
        channels: list[ChannelIntervention],
        baseline_failed: bool,
    ) -> PairedTrial:
        """Execute one paired trial with joint channel intervention.

        All channels are bridged to event-level interventions and
        applied in a SINGLE counterfactual replay.
        """
        # Bridge each channel → event intervention (true channel-level)
        event_interventions = []
        for ch in channels:
            intv = channel_to_intervention(ch, self._baseline, self._graph)
            event_interventions.append(intv)

        # Deduplicate by target_id (same event targeted by multiple channels)
        seen_targets: set[str] = set()
        deduped: list[Intervention] = []
        for intv in event_interventions:
            if intv.target_id not in seen_targets:
                seen_targets.add(intv.target_id)
                deduped.append(intv)

        iset = InterventionSet(
            baseline_run_id=self._baseline.run_id,
            interventions=deduped,
        )

        # Execute ONE counterfactual replay with all interventions
        result = CounterfactualReplayEngine.replay(
            self._baseline,
            iset,
            tool_registry=self._registry,
        )

        set_ids = sorted(ch.intervention_id for ch in channels)
        set_id_str = ",".join(set_ids[:3])

        if result.status == ReplayStatus.REJECTED:
            return PairedTrial(
                baseline_run_id=self._baseline.run_id,
                candidate_id=set_id_str,
                baseline_outcome=baseline_failed,
                status=TrialStatus.INVALID_INTERVENTION,
                error_message=result.rejection_reason or "Intervention rejected",
            )

        if result.status == ReplayStatus.FAILED or result.counterfactual_run is None:
            return PairedTrial(
                baseline_run_id=self._baseline.run_id,
                candidate_id=set_id_str,
                baseline_outcome=baseline_failed,
                status=TrialStatus.REPLAY_ERROR,
                error_message=result.rejection_reason or "Replay failed",
            )

        cf_run = result.counterfactual_run
        cf_failed = self._evaluator(cf_run)

        return PairedTrial(
            baseline_run_id=self._baseline.run_id,
            counterfactual_run_id=cf_run.run_id,
            candidate_id=set_id_str,
            baseline_outcome=baseline_failed,
            counterfactual_outcome=cf_failed,
            status=TrialStatus.SUCCESS,
            metadata={
                "joint_replay": True,
                "channel_count": len(channels),
                "intervention_count": len(deduped),
            },
        )

    def _confidence_interval(
        self,
        diffs: list[int],
        n: int,
    ) -> tuple[float, float]:
        """Compute confidence interval for paired binary diffs.

        Reuses Stage 14 paired bootstrap logic.
        """
        import math
        import random

        if n <= 1:
            point = sum(diffs) / max(n, 1)
            return (point, point)

        rng = random.Random(42)  # noqa: S311
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
# Greedy cascade selector
# ===================================================================


class GreedyCascadeSelector:
    """Greedy marginal-gain cascade intervention selection.

    **This is NOT globally optimal.**  It is a greedy procedure
    that selects the **best supported set found under the configured
    search procedure**.

    Algorithm:

    1. Start with S = {}.
    2. For each candidate e not in S, estimate CEE(S U {e}).
    3. Compute marginal gain: D(e|S) = CEE(S U {e}) - CEE(S).
    4. Select e with largest positive D, subject to cost/budget.
    5. Add e to S.
    6. Repeat until:
       - failure prevention achieved;
       - budget exhausted;
       - no positive supported marginal gain;
       - maximum set size reached;
       - evaluation budget exhausted.

    Supports two modes:

    - **Budget-constrained**: maximize CEE(S) s.t. Cost(S) <= B.
    - **Utility-based**: maximize U(S) = CEE(S) - lambda*Cost(S).

    Deterministic tie-breaking: lower cost, then lexicographic ID.

    Usage::

        selector = GreedyCascadeSelector(
            cascade_estimator=estimator,
            cost_model=cost_model,
            budget=5.0,
        )
        result = selector.select(candidates)
    """

    def __init__(
        self,
        cascade_estimator: CascadeEstimator,
        cost_model: CostModel | None = None,
        *,
        max_set_size: int = 5,
        budget: float | None = None,
        lambda_cost: float = 0.0,
        max_evaluations: int = 100,
    ) -> None:
        self._estimator = cascade_estimator
        self._cost_model = cost_model or CostModel()
        self._max_set_size = max(1, max_set_size)
        self._budget = budget
        self._lambda_cost = lambda_cost
        self._max_evaluations = max(1, max_evaluations)

    def select(
        self,
        candidates: list[ChannelIntervention],
    ) -> SelectionResult:
        """Execute greedy marginal-gain cascade selection.

        Returns a SelectionResult with the selected set, CEE(S),
        utility, prevention status, and full audit trail.

        If no supported set satisfies constraints, returns
        status=NO_SUPPORTED_SOLUTION.

        If evaluation budget is exhausted before completion,
        returns status=EVALUATION_BUDGET_EXHAUSTED with best
        set found so far.
        """
        if not candidates:
            return SelectionResult(
                budget=self._budget,
                lambda_cost=self._lambda_cost,
                max_evaluations=self._max_evaluations,
                status=SelectionStatus.NO_SUPPORTED_SOLUTION,
                metadata={"reason": "no_candidates"},
            )

        selected: list[ChannelIntervention] = []
        remaining = list(candidates)
        all_steps: list[MarginalGainStep] = []
        evaluations_used = 0
        current_cee = 0.0
        step_idx = 0
        budget_exhausted = False

        while len(selected) < self._max_set_size and remaining and not budget_exhausted:
            # Evaluate marginal gain for each remaining candidate
            best_candidate: ChannelIntervention | None = None
            best_gain = -float("inf")
            best_cee_with = 0.0
            best_cost = float("inf")
            step_records: list[MarginalGainStep] = []

            for cand in remaining:
                cand_cost = self._cost_model.cost(cand)
                current_cost = self._cost_model.total_cost(selected)

                # Budget check: skip if adding would exceed budget
                if self._budget is not None and current_cost + cand_cost > self._budget:
                    step_records.append(
                        MarginalGainStep(
                            step_index=step_idx,
                            current_set_ids=[c.intervention_id for c in selected],
                            current_cee=current_cee,
                            candidate_id=cand.intervention_id,
                            candidate_cee_with=0.0,
                            marginal_gain=0.0,
                            candidate_cost=cand_cost,
                            selected=False,
                            reason="exceeds_budget",
                        )
                    )
                    continue

                # Check evaluation budget
                if evaluations_used >= self._max_evaluations:
                    return self._build_result(
                        selected,
                        current_cee,
                        all_steps + step_records,
                        evaluations_used,
                        SelectionStatus.EVALUATION_BUDGET_EXHAUSTED,
                    )

                # Estimate CEE(S U {e}) via real joint replay
                trial_set = [*list(selected), cand]
                cascade_result = self._estimator.estimate_set(trial_set)
                evaluations_used += 1
                cee_with = cascade_result.cee

                # Marginal gain: D(e|S) = CEE(S U {e}) - CEE(S)
                marginal = cee_with - current_cee

                step_records.append(
                    MarginalGainStep(
                        step_index=step_idx,
                        current_set_ids=[c.intervention_id for c in selected],
                        current_cee=current_cee,
                        candidate_id=cand.intervention_id,
                        candidate_cee_with=cee_with,
                        marginal_gain=marginal,
                        candidate_cost=cand_cost,
                        selected=False,
                        reason="evaluated",
                    )
                )

                # Selection criterion depends on mode
                if self._lambda_cost > 0:
                    # Utility mode: gain in utility
                    utility_gain = marginal - self._lambda_cost * cand_cost
                    is_better = utility_gain > best_gain or (
                        utility_gain == best_gain
                        and (
                            cand_cost < best_cost
                            or (
                                cand_cost == best_cost
                                and cand.intervention_id
                                < (best_candidate.intervention_id if best_candidate else "")
                            )
                        )
                    )
                    if is_better and utility_gain > 0:
                        best_candidate = cand
                        best_gain = utility_gain
                        best_cee_with = cee_with
                        best_cost = cand_cost
                else:
                    # Budget/CEE mode: largest marginal CEE gain
                    is_better = marginal > best_gain or (
                        marginal == best_gain
                        and (
                            cand_cost < best_cost
                            or (
                                cand_cost == best_cost
                                and cand.intervention_id
                                < (best_candidate.intervention_id if best_candidate else "")
                            )
                        )
                    )
                    if is_better and marginal > 0:
                        best_candidate = cand
                        best_gain = marginal
                        best_cee_with = cee_with
                        best_cost = cand_cost

            # No positive marginal gain found
            if best_candidate is None:
                all_steps.extend(step_records)
                break

            # Mark the selected candidate in step records
            for rec in step_records:
                if rec.candidate_id == best_candidate.intervention_id:
                    rec.selected = True
                    rec.reason = "selected"

            all_steps.extend(step_records)

            # Add best candidate to selected set
            selected.append(best_candidate)
            remaining = [
                c for c in remaining if c.intervention_id != best_candidate.intervention_id
            ]
            current_cee = best_cee_with
            step_idx += 1

            # Check if failure is already prevented
            # Re-evaluate with current set to get prevention status
            if evaluations_used < self._max_evaluations:
                final_result = self._estimator.estimate_set(selected)
                evaluations_used += 1
                if final_result.prevented:
                    return self._build_result(
                        selected,
                        final_result.cee,
                        all_steps,
                        evaluations_used,
                        SelectionStatus.SUCCESS,
                        cascade_result=final_result,
                    )

        # Build final result
        if selected:
            if evaluations_used < self._max_evaluations:
                final_result = self._estimator.estimate_set(selected)
                evaluations_used += 1
                return self._build_result(
                    selected,
                    final_result.cee,
                    all_steps,
                    evaluations_used,
                    SelectionStatus.SUCCESS,
                    cascade_result=final_result,
                )
            return self._build_result(
                selected,
                current_cee,
                all_steps,
                evaluations_used,
                SelectionStatus.EVALUATION_BUDGET_EXHAUSTED,
            )

        return self._build_result(
            selected,
            0.0,
            all_steps,
            evaluations_used,
            SelectionStatus.NO_SUPPORTED_SOLUTION,
        )

    def _build_result(
        self,
        selected: list[ChannelIntervention],
        cee: float,
        steps: list[MarginalGainStep],
        evaluations_used: int,
        status: SelectionStatus,
        *,
        cascade_result: CascadeResult | None = None,
    ) -> SelectionResult:
        """Construct the SelectionResult."""
        total_cost = self._cost_model.total_cost(selected) if selected else 0.0
        utility = cee - self._lambda_cost * total_cost

        spec: InterventionSetSpec | None = None
        if selected:
            spec = InterventionSetSpec(
                baseline_run_id=self._estimator._baseline.run_id,
                channel_interventions=list(selected),
                total_cost=total_cost,
            )

        prevented = cascade_result.prevented if cascade_result else False
        prevention_rate = cascade_result.prevention_rate if cascade_result else 0.0

        return SelectionResult(
            selected_set=spec,
            cascade_result=cascade_result,
            selection_method="greedy_marginal_gain",
            selection_steps=steps,
            total_cost=total_cost,
            utility=utility,
            budget=self._budget,
            lambda_cost=self._lambda_cost,
            prevented=prevented,
            prevention_rate=prevention_rate,
            status=status,
            evaluations_used=evaluations_used,
            max_evaluations=self._max_evaluations,
        )
