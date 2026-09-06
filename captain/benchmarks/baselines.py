"""CELA benchmark baselines and methods -- Stage 16.

Baseline methods (B1-B5), CELA configurations (A1-A5), and
an evaluation-only exhaustive oracle.

All methods implement the same BaselineMethod interface and
receive identical inputs. No method receives ground-truth
causal labels.

The oracle is NOT a baseline. It is used ONLY for computing
regret (optimality gap) as a diagnostic metric.
"""

from __future__ import annotations

import abc
import itertools
import random
import uuid
from typing import Any

from pydantic import BaseModel, Field

from captain.analysis.cascade import (
    CascadeEstimator,
    CostModel,
    GreedyCascadeSelector,
)
from captain.analysis.estimator import (
    CEEEstimator,
    FailureEvaluator,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    ChannelIntervention,
    Failure,
)
from captain.models.execution import ExecutionRun
from captain.models.ids import _is_deterministic, _next_deterministic_id

# ===================================================================
# Baseline interface
# ===================================================================


class MethodSelection(BaseModel):
    """Output of a baseline or CELA method.

    Contains the selected intervention channels and metadata.
    """

    method_name: str
    selected: list[str] = Field(default_factory=list)
    ranked: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    replay_count: int = 0


class BaselineMethod(abc.ABC):
    """Abstract interface for all benchmark methods.

    All methods receive identical inputs: candidates, failure,
    evidence graph, and optional parameters. No method receives
    ground-truth causal labels.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Method identifier."""

    @abc.abstractmethod
    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        """Select intervention channels."""


# ===================================================================
# B1: Random baseline
# ===================================================================


class RandomBaseline(BaselineMethod):
    """B1: Deterministic random selection.

    Uses deterministic seed derivation: seed = scenario_seed * 1000 + 100 + d.
    Performs multiple draws and returns the best (highest count of selected).
    """

    def __init__(self, scenario_seed: int = 42, draws: int = 5) -> None:
        self._seed = scenario_seed
        self._draws = max(1, draws)

    @property
    def name(self) -> str:
        return "B1_random"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        k = min(k, len(candidates))
        best_selection: list[str] = []
        ids = [c.intervention_id for c in candidates]

        for d in range(self._draws):
            draw_seed = self._seed * 1000 + 100 + d
            rng = random.Random(draw_seed)  # noqa: S311
            shuffled = list(ids)
            rng.shuffle(shuffled)
            selection = shuffled[:k]
            # Keep the draw (all are equally valid for random)
            if not best_selection:
                best_selection = selection

        return MethodSelection(
            method_name=self.name,
            selected=best_selection,
            ranked=best_selection,
            metadata={"draws": self._draws, "seed": self._seed},
        )


# ===================================================================
# B2: Provenance-only baseline
# ===================================================================


class ProvenanceOnlyBaseline(BaselineMethod):
    """B2: Top-k by Stage 13 screening score.

    Uses FailureAnalyzer's structural provenance scoring.
    Does NOT use counterfactual replay or CEE.
    """

    @property
    def name(self) -> str:
        return "B2_provenance"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        # Get candidates with screening scores from FailureAnalyzer
        analyzer = FailureAnalyzer(evidence_graph, failure)
        scored_candidates = analyzer.candidates()

        # Map candidate_id -> screening_score
        score_map: dict[str, float] = {}
        for sc in scored_candidates:
            score_map[sc.candidate_id] = sc.screening_score

        # Map intervention candidate_id -> score
        scored: list[tuple[str, float]] = []
        for ci in candidates:
            score = score_map.get(ci.candidate_id, 0.0)
            scored.append((ci.intervention_id, score))

        # Sort by score descending, then lexicographic ID for tie-breaking
        scored.sort(key=lambda x: (-x[1], x[0]))
        ranked = [s[0] for s in scored]
        selected = ranked[: min(k, len(ranked))]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=ranked,
        )


# ===================================================================
# B3: CEE-Rank baseline
# ===================================================================


class CEERankBaseline(BaselineMethod):
    """B3: Top-k by individual CEE(e).

    Ranks by individual channel CEE. No set-level optimization.
    Requires counterfactual replay.
    """

    @property
    def name(self) -> str:
        return "B3_cee_rank"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        analyzer = FailureAnalyzer(evidence_graph, failure)
        scored_candidates = analyzer.candidates()
        cee_estimator = CEEEstimator(run, evaluator, evidence_graph=evidence_graph, num_trials=1)

        # Compute individual CEE for each candidate
        cee_scores: list[tuple[str, float]] = []
        replay_count = 0

        # Match by (source_evidence_id, target_evidence_id) pair
        cand_map: dict[tuple[str, str], Any] = {}
        for sc in scored_candidates:
            key = (sc.source_evidence_id, sc.target_evidence_id)
            cand_map[key] = sc

        for ci in candidates:
            key = (ci.source_evidence_id, ci.target_evidence_id)
            cand = cand_map.get(key)
            if cand is None:
                cee_scores.append((ci.intervention_id, 0.0))
                continue
            result = cee_estimator.estimate(cand, ci)
            replay_count += 1
            cee_scores.append((ci.intervention_id, result.cee))

        # Sort by CEE descending, then lexicographic
        cee_scores.sort(key=lambda x: (-x[1], x[0]))
        ranked = [s[0] for s in cee_scores]
        selected = ranked[: min(k, len(ranked))]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=ranked,
            replay_count=replay_count,
        )


# ===================================================================
# B4: Graph-structural baseline
# ===================================================================


class GraphStructuralBaseline(BaselineMethod):
    """B4: Top-k by minimum graph distance to failure.

    Closest channels to failure are selected first.
    Does NOT use counterfactual replay.
    """

    @property
    def name(self) -> str:
        return "B4_graph_structural"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        analyzer = FailureAnalyzer(evidence_graph, failure)
        scored_candidates = analyzer.candidates()

        # Map candidate_id -> graph_distance
        dist_map: dict[str, int] = {}
        for sc in scored_candidates:
            dist_map[sc.candidate_id] = sc.graph_distance

        scored: list[tuple[str, int]] = []
        for ci in candidates:
            dist = dist_map.get(ci.candidate_id, 999)
            scored.append((ci.intervention_id, dist))

        # Sort by distance ascending (closer = better), then lexicographic
        scored.sort(key=lambda x: (x[1], x[0]))
        ranked = [s[0] for s in scored]
        selected = ranked[: min(k, len(ranked))]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=ranked,
        )


# ===================================================================
# B5: Cost-aware structural baseline
# ===================================================================


class CostAwareBaseline(BaselineMethod):
    """B5: Top-k by screening_score / cost.

    Structural provenance heuristic penalized by cost.
    Does NOT use counterfactual replay.
    """

    @property
    def name(self) -> str:
        return "B5_cost_aware"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        cm = cost_model or CostModel()
        analyzer = FailureAnalyzer(evidence_graph, failure)
        scored_candidates = analyzer.candidates()

        score_map: dict[str, float] = {}
        for sc in scored_candidates:
            score_map[sc.candidate_id] = sc.screening_score

        scored: list[tuple[str, float]] = []
        for ci in candidates:
            raw_score = score_map.get(ci.candidate_id, 0.0)
            cost = max(cm.cost(ci), 0.001)
            efficiency = raw_score / cost
            scored.append((ci.intervention_id, efficiency))

        scored.sort(key=lambda x: (-x[1], x[0]))
        ranked = [s[0] for s in scored]

        # Apply budget constraint if set
        if budget is not None:
            ci_map = {ci.intervention_id: ci for ci in candidates}
            feasible: list[str] = []
            total = 0.0
            for cid in ranked:
                ci_val = ci_map.get(cid)
                if ci_val is None:
                    continue
                c = cm.cost(ci_val)
                if total + c <= budget:
                    feasible.append(cid)
                    total += c
                if len(feasible) >= k:
                    break
            selected = feasible
        else:
            selected = ranked[: min(k, len(ranked))]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=ranked,
        )


# ===================================================================
# CELA method (A1-A5)
# ===================================================================


class CELAMethod(BaselineMethod):
    """CELA configurations A1-A5.

    A1 = provenance-only control (same as B2)
    A2 = provenance + individual CEE
    A3 = provenance + set-level CEE (restricted subset evaluation)
    A4 = provenance + cascade optimization (greedy marginal-gain)
    A5 = CELA full (A4 + cost/utility)

    A3 evaluates subsets of top individual-CEE channels.
    A4 uses GreedyCascadeSelector. These are distinct procedures.
    """

    def __init__(self, level: int = 5) -> None:
        if level < 1 or level > 5:
            msg = f"CELA level must be 1-5, got {level}"
            raise ValueError(msg)
        self._level = level

    @property
    def name(self) -> str:
        return f"A{self._level}_cela"

    def select(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        if not candidates:
            return MethodSelection(method_name=self.name)

        if self._level == 1:
            return self._a1_provenance(candidates, failure, evidence_graph, run)

        if self._level == 2:
            return self._a2_individual_cee(
                candidates, failure, evidence_graph, run, evaluator, k=k
            )

        if self._level == 3:
            return self._a3_set_level(candidates, failure, evidence_graph, run, evaluator, k=k)

        if self._level == 4:
            return self._a4_cascade(candidates, failure, evidence_graph, run, evaluator, k=k)

        # level == 5
        return self._a5_full(
            candidates,
            failure,
            evidence_graph,
            run,
            evaluator,
            k=k,
            cost_model=cost_model,
            budget=budget,
            lambda_cost=lambda_cost,
        )

    def _a1_provenance(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
    ) -> MethodSelection:
        """A1: Same as B2 provenance-only."""
        b2 = ProvenanceOnlyBaseline()
        result = b2.select(candidates, failure, evidence_graph, run, lambda _r: True)
        result.method_name = self.name
        return result

    def _a2_individual_cee(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
    ) -> MethodSelection:
        """A2: Rank by individual CEE, select top-k."""
        b3 = CEERankBaseline()
        result = b3.select(candidates, failure, evidence_graph, run, evaluator, k=k)
        result.method_name = self.name
        return result

    def _a3_set_level(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
    ) -> MethodSelection:
        """A3: Restricted set-level CEE evaluation.

        Takes top-k individual CEE channels and evaluates
        subsets of those via CascadeEstimator. NOT exhaustive
        over all candidates -- only subsets of the top pool.
        NOT greedy marginal-gain.
        """
        # First get individual CEE ranking
        analyzer = FailureAnalyzer(evidence_graph, failure)
        scored_candidates = analyzer.candidates()
        cee_estimator = CEEEstimator(run, evaluator, evidence_graph=evidence_graph, num_trials=1)

        cand_map = {sc.candidate_id: sc for sc in scored_candidates}
        ci_map = {ci.intervention_id: ci for ci in candidates}

        cee_scores: list[tuple[str, float]] = []
        replay_count = 0

        for ci in candidates:
            cand = cand_map.get(ci.candidate_id)
            if cand is None:
                cee_scores.append((ci.intervention_id, 0.0))
                continue
            result = cee_estimator.estimate(cand, ci)
            replay_count += 1
            cee_scores.append((ci.intervention_id, result.cee))

        # Take top-k pool
        cee_scores.sort(key=lambda x: (-x[1], x[0]))
        pool_size = min(k + 1, len(cee_scores))
        pool_ids = [s[0] for s in cee_scores[:pool_size]]
        pool_cis = [ci_map[cid] for cid in pool_ids if cid in ci_map]

        # Evaluate subsets of size 1..k from pool
        cascade_est = CascadeEstimator(run, evaluator, evidence_graph=evidence_graph, num_trials=1)
        best_set: list[str] = []
        best_cee = -1.0

        for size in range(1, min(k, len(pool_cis)) + 1):
            for subset in itertools.combinations(pool_cis, size):
                subset_list = list(subset)
                cascade_res = cascade_est.estimate_set(subset_list)
                replay_count += 1
                if cascade_res.cee > best_cee:
                    best_cee = cascade_res.cee
                    best_set = [ci.intervention_id for ci in subset_list]

        ranked = [s[0] for s in cee_scores]

        return MethodSelection(
            method_name=self.name,
            selected=best_set,
            ranked=ranked,
            replay_count=replay_count,
            metadata={"best_set_cee": best_cee},
        )

    def _a4_cascade(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
    ) -> MethodSelection:
        """A4: Greedy marginal-gain via GreedyCascadeSelector."""
        cascade_est = CascadeEstimator(run, evaluator, evidence_graph=evidence_graph, num_trials=1)
        selector = GreedyCascadeSelector(cascade_est, max_set_size=k, max_evaluations=20)
        result = selector.select(candidates)

        selected: list[str] = []
        if result.selected_set is not None:
            selected = [ci.intervention_id for ci in result.selected_set.channel_interventions]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=selected,
            replay_count=result.evaluations_used,
            metadata={"status": result.status.value},
        )

    def _a5_full(
        self,
        candidates: list[ChannelIntervention],
        failure: Failure,
        evidence_graph: EvidenceFlowGraph,
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        *,
        k: int = 1,
        cost_model: CostModel | None = None,
        budget: float | None = None,
        lambda_cost: float = 0.0,
    ) -> MethodSelection:
        """A5: Full CELA with cost/utility awareness."""
        cm = cost_model or CostModel()
        lc = lambda_cost if lambda_cost > 0 else 0.1

        cascade_est = CascadeEstimator(
            run,
            evaluator,
            evidence_graph=evidence_graph,
            num_trials=1,
            lambda_cost=lc,
            cost_model=cm,
        )
        selector = GreedyCascadeSelector(
            cascade_est,
            cost_model=cm,
            max_set_size=k,
            budget=budget,
            lambda_cost=lc,
            max_evaluations=20,
        )
        result = selector.select(candidates)

        selected: list[str] = []
        if result.selected_set is not None:
            selected = [ci.intervention_id for ci in result.selected_set.channel_interventions]

        return MethodSelection(
            method_name=self.name,
            selected=selected,
            ranked=selected,
            replay_count=result.evaluations_used,
            metadata={
                "status": result.status.value,
                "utility": result.utility,
                "total_cost": result.total_cost,
            },
        )


# ===================================================================
# Exhaustive oracle (evaluation-only)
# ===================================================================


class OracleResult(BaseModel):
    """Result of exhaustive oracle search.

    The oracle is NOT a baseline. It is used ONLY for
    computing regret as a diagnostic metric.
    """

    oracle_id: str = Field(
        default_factory=lambda: (
            _next_deterministic_id("oracle_")
            if _is_deterministic()
            else f"oracle_{uuid.uuid4().hex[:12]}"
        )
    )
    optimal_set: list[str] = Field(default_factory=list)
    optimal_objective: float = 0.0
    sets_evaluated: int = 0
    objective_type: str = "effectiveness"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExhaustiveOracle:
    """Evaluation-only exhaustive intervention set search.

    Enumerates ALL valid intervention sets up to max_set_size
    and evaluates each via REAL joint counterfactual replay.

    NOT a baseline. NEVER visible to CELA or baselines.
    Used ONLY for computing regret (optimality gap).
    """

    def find_optimal(
        self,
        candidates: list[ChannelIntervention],
        run: ExecutionRun,
        evaluator: FailureEvaluator,
        evidence_graph: EvidenceFlowGraph,
        *,
        max_set_size: int = 3,
        objective: str = "effectiveness",
        budget: float | None = None,
        lambda_cost: float = 0.0,
        cost_model: CostModel | None = None,
    ) -> OracleResult:
        """Find optimal intervention set by exhaustive search."""
        if not candidates:
            return OracleResult(objective_type=objective)

        cm = cost_model or CostModel()
        cascade_est = CascadeEstimator(
            run,
            evaluator,
            evidence_graph=evidence_graph,
            num_trials=1,
            lambda_cost=lambda_cost,
            cost_model=cm,
        )

        best_set: list[str] = []
        best_obj = -float("inf")
        sets_evaluated = 0

        for size in range(1, min(max_set_size, len(candidates)) + 1):
            for subset in itertools.combinations(candidates, size):
                subset_list = list(subset)

                # Budget check
                if budget is not None:
                    total_cost = cm.total_cost(subset_list)
                    if total_cost > budget:
                        continue

                result = cascade_est.estimate_set(subset_list)
                sets_evaluated += 1

                # Compute objective
                if objective == "utility":
                    obj = result.cee - lambda_cost * cm.total_cost(subset_list)
                elif objective == "budget":
                    obj = result.cee
                else:  # effectiveness
                    obj = result.cee

                if obj > best_obj:
                    best_obj = obj
                    best_set = [ci.intervention_id for ci in subset_list]

        return OracleResult(
            optimal_set=best_set,
            optimal_objective=best_obj if best_obj > -float("inf") else 0.0,
            sets_evaluated=sets_evaluated,
            objective_type=objective,
        )
