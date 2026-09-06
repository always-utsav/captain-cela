"""CELA benchmark runner and metrics -- Stage 16.

Orchestrates benchmark execution: scenario generation, method
application, counterfactual replay, and metric computation.

Separately reports three evaluation dimensions:
- Attribution: did the method identify causal channels?
- Localization: did it identify origin/propagation/actuator?
- Prevention: did the intervention actually prevent failure?

These are NEVER collapsed into a single score.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from captain.analysis.cascade import CascadeEstimator, CostModel
from captain.benchmarks.baselines import (
    BaselineMethod,
    CEERankBaseline,
    CELAMethod,
    CostAwareBaseline,
    ExhaustiveOracle,
    GraphStructuralBaseline,
    MethodSelection,
    OracleResult,
    ProvenanceOnlyBaseline,
    RandomBaseline,
)
from captain.benchmarks.scenarios import (
    BenchmarkScenario,
    ScenarioGroundTruth,
    get_evaluator,
)

# ===================================================================
# Metric models
# ===================================================================


class AttributionMetrics(BaseModel):
    """Attribution evaluation: did the method identify causal channels?"""

    causal_precision: float = 0.0
    causal_recall: float = 0.0
    causal_f1: float = 0.0
    recall_at_1: float = 0.0
    recall_at_k: float = 0.0
    k: int = 1


class LocalizationMetrics(BaseModel):
    """Localization: origin, propagation, actuator identification."""

    origin_recall: float = 0.0
    propagation_recall: float = 0.0
    actuator_recall: float = 0.0


class PreventionMetrics(BaseModel):
    """Prevention: did the intervention prevent the failure?"""

    failure_prevention_rate: float = 0.0
    prevention_set_recall: float = 0.0
    cee_set: float = 0.0


class DiscriminationMetrics(BaseModel):
    """Discrimination: distractor avoidance."""

    distractor_false_selection_rate: float | None = None


class InteractionMetrics(BaseModel):
    """Interaction: complementarity and redundancy."""

    complementary_group_recovery_rate: float | None = None
    redundancy_group_coverage: float | None = None


class EfficiencyMetrics(BaseModel):
    """Efficiency: cost and computational effort."""

    intervention_cost: float = 0.0
    utility: float = 0.0
    set_size: int = 0
    replay_count: int = 0


class OptimalityMetrics(BaseModel):
    """Optimality gap relative to exhaustive oracle."""

    regret: float | None = None
    oracle_objective: float = 0.0
    method_objective: float = 0.0


class BenchmarkMetrics(BaseModel):
    """Complete metrics for one method on one scenario."""

    attribution: AttributionMetrics = Field(default_factory=AttributionMetrics)
    localization: LocalizationMetrics = Field(default_factory=LocalizationMetrics)
    prevention: PreventionMetrics = Field(default_factory=PreventionMetrics)
    discrimination: DiscriminationMetrics = Field(default_factory=DiscriminationMetrics)
    interaction: InteractionMetrics = Field(default_factory=InteractionMetrics)
    efficiency: EfficiencyMetrics = Field(default_factory=EfficiencyMetrics)
    optimality: OptimalityMetrics = Field(default_factory=OptimalityMetrics)


# ===================================================================
# Result models
# ===================================================================


class MethodResult(BaseModel):
    """One method's result on one scenario."""

    scenario_id: str
    method_name: str
    selection: MethodSelection
    metrics: BenchmarkMetrics
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    """Complete benchmark run result.

    Contains all method results across all scenarios.
    Serializable via Pydantic for reproducibility.
    """

    results: list[MethodResult] = Field(default_factory=list)
    oracle_results: dict[str, OracleResult] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Metric evaluator
# ===================================================================


class MetricEvaluator:
    """Computes all benchmark metrics.

    Compares method selections against ScenarioGroundTruth.
    Ground truth is used ONLY here, never by methods.
    """

    def compute(
        self,
        selection: MethodSelection,
        ground_truth: ScenarioGroundTruth,
        *,
        k: int = 1,
        cee_set: float = 0.0,
        prevention_rate: float = 0.0,
        cost_model: CostModel | None = None,
        lambda_cost: float = 0.0,
        oracle_result: OracleResult | None = None,
    ) -> BenchmarkMetrics:
        """Compute complete metrics from selection vs ground truth."""
        selected = set(selection.selected)
        ranked = selection.ranked

        attribution = self._compute_attribution(selected, ranked, ground_truth, k=k)
        localization = self._compute_localization(selected, ground_truth)
        prevention = self._compute_prevention(
            selected, ground_truth, cee_set=cee_set, prevention_rate=prevention_rate
        )
        discrimination = self._compute_discrimination(selected, ground_truth)
        interaction = self._compute_interaction(selected, ground_truth)
        efficiency = self._compute_efficiency(
            selection,
            ground_truth,
            cost_model=cost_model,
            lambda_cost=lambda_cost,
            cee_set=cee_set,
        )
        optimality = self._compute_optimality(
            cee_set,
            oracle_result,
            lambda_cost=lambda_cost,
            cost=efficiency.intervention_cost,
        )

        return BenchmarkMetrics(
            attribution=attribution,
            localization=localization,
            prevention=prevention,
            discrimination=discrimination,
            interaction=interaction,
            efficiency=efficiency,
            optimality=optimality,
        )

    def _compute_attribution(
        self,
        selected: set[str],
        ranked: list[str],
        gt: ScenarioGroundTruth,
        *,
        k: int = 1,
    ) -> AttributionMetrics:
        causal = set(gt.causal_channel_ids)

        precision = len(selected & causal) / len(selected) if selected else 0.0
        recall = len(selected & causal) / len(causal) if causal else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Recall@1
        recall_1 = 1.0 if ranked and ranked[0] in causal else 0.0

        # Recall@K: fraction of causal channels in top-K
        top_k = set(ranked[:k])
        recall_k = len(top_k & causal) / len(causal) if causal else 0.0

        return AttributionMetrics(
            causal_precision=precision,
            causal_recall=recall,
            causal_f1=f1,
            recall_at_1=recall_1,
            recall_at_k=recall_k,
            k=k,
        )

    def _compute_localization(
        self,
        selected: set[str],
        gt: ScenarioGroundTruth,
    ) -> LocalizationMetrics:
        origin = set(gt.causal_origin_ids)
        prop = set(gt.propagation_channel_ids)
        actuator = set(gt.failure_actuator_ids)

        origin_r = len(selected & origin) / len(origin) if origin else 0.0
        prop_r = len(selected & prop) / len(prop) if prop else 0.0
        act_r = len(selected & actuator) / len(actuator) if actuator else 0.0

        return LocalizationMetrics(
            origin_recall=origin_r,
            propagation_recall=prop_r,
            actuator_recall=act_r,
        )

    def _compute_prevention(
        self,
        selected: set[str],
        gt: ScenarioGroundTruth,
        *,
        cee_set: float = 0.0,
        prevention_rate: float = 0.0,
    ) -> PreventionMetrics:
        # Find best-matching required prevention set
        best_recall = 0.0
        for req_set in gt.required_prevention_sets:
            req = set(req_set)
            if req:
                r = len(selected & req) / len(req)
                best_recall = max(best_recall, r)

        return PreventionMetrics(
            failure_prevention_rate=prevention_rate,
            prevention_set_recall=best_recall,
            cee_set=cee_set,
        )

    def _compute_discrimination(
        self,
        selected: set[str],
        gt: ScenarioGroundTruth,
    ) -> DiscriminationMetrics:
        irrelevant = set(gt.irrelevant_channel_ids)
        if not irrelevant:
            return DiscriminationMetrics(distractor_false_selection_rate=None)

        dfsr = len(selected & irrelevant) / len(irrelevant)
        return DiscriminationMetrics(distractor_false_selection_rate=dfsr)

    def _compute_interaction(
        self,
        selected: set[str],
        gt: ScenarioGroundTruth,
    ) -> InteractionMetrics:
        # Complementary group recovery
        comp_rate: float | None = None
        if gt.complementary_groups:
            recovered = sum(1 for group in gt.complementary_groups if selected & set(group))
            comp_rate = recovered / len(gt.complementary_groups)

        # Redundancy group coverage
        red_rate: float | None = None
        if gt.redundancy_groups:
            covered = sum(1 for group in gt.redundancy_groups if set(group) <= selected)
            red_rate = covered / len(gt.redundancy_groups)

        return InteractionMetrics(
            complementary_group_recovery_rate=comp_rate,
            redundancy_group_coverage=red_rate,
        )

    def _compute_efficiency(
        self,
        selection: MethodSelection,
        gt: ScenarioGroundTruth,
        *,
        cost_model: CostModel | None = None,
        lambda_cost: float = 0.0,
        cee_set: float = 0.0,
    ) -> EfficiencyMetrics:
        cm = cost_model or CostModel()
        costs = gt.channel_costs

        total_cost = sum(costs.get(cid, cm.default_cost) for cid in selection.selected)
        utility = cee_set - lambda_cost * total_cost

        return EfficiencyMetrics(
            intervention_cost=total_cost,
            utility=utility,
            set_size=len(selection.selected),
            replay_count=selection.replay_count,
        )

    def _compute_optimality(
        self,
        cee_set: float,
        oracle_result: OracleResult | None,
        *,
        lambda_cost: float = 0.0,
        cost: float = 0.0,
    ) -> OptimalityMetrics:
        if oracle_result is None:
            return OptimalityMetrics()

        if oracle_result.objective_type == "utility":
            method_obj = cee_set - lambda_cost * cost
        else:
            method_obj = cee_set

        regret = oracle_result.optimal_objective - method_obj

        return OptimalityMetrics(
            regret=max(regret, 0.0),
            oracle_objective=oracle_result.optimal_objective,
            method_objective=method_obj,
        )


# ===================================================================
# Benchmark runner
# ===================================================================


class BenchmarkRunner:
    """Orchestrates the complete benchmark pipeline.

    For each scenario and method:
    1. Method selects intervention channels (no ground truth)
    2. Selected set is evaluated via real counterfactual replay
    3. Metrics are computed against ground truth (post-hoc only)
    4. Oracle computes optimal for regret

    All methods receive identical inputs.
    """

    def __init__(
        self,
        *,
        k: int = 3,
        max_set_size: int = 3,
        lambda_cost: float = 0.1,
    ) -> None:
        self._k = k
        self._max_set_size = max_set_size
        self._lambda_cost = lambda_cost

    def run(
        self,
        scenarios: list[BenchmarkScenario],
        methods: list[BaselineMethod] | None = None,
        *,
        run_oracle: bool = True,
    ) -> BenchmarkResult:
        """Execute the complete benchmark."""
        if methods is None:
            methods = self._default_methods(scenarios)

        all_results: list[MethodResult] = []
        oracle_results: dict[str, OracleResult] = {}

        for scenario in scenarios:
            evaluator = get_evaluator(scenario)
            gt = scenario.ground_truth
            cost_model = CostModel(channel_costs=gt.channel_costs) if gt.channel_costs else None

            # Run oracle for regret computation
            oracle_res: OracleResult | None = None
            if run_oracle:
                oracle = ExhaustiveOracle()
                oracle_res = oracle.find_optimal(
                    scenario.candidates,
                    scenario.run,
                    evaluator,
                    scenario.evidence_graph,
                    max_set_size=self._max_set_size,
                    budget=gt.budget,
                    lambda_cost=self._lambda_cost,
                    cost_model=cost_model,
                )
                oracle_results[scenario.scenario_id] = oracle_res

            # Run each method
            for method in methods:
                selection = method.select(
                    scenario.candidates,
                    scenario.failure,
                    scenario.evidence_graph,
                    scenario.run,
                    evaluator,
                    k=self._k,
                    cost_model=cost_model,
                    budget=gt.budget,
                    lambda_cost=self._lambda_cost,
                )

                # Evaluate selected set via real replay
                cee_set = 0.0
                prevention_rate = 0.0
                if selection.selected:
                    ci_map = {ci.intervention_id: ci for ci in scenario.candidates}
                    selected_cis = [ci_map[cid] for cid in selection.selected if cid in ci_map]
                    if selected_cis:
                        cascade_est = CascadeEstimator(
                            scenario.run,
                            evaluator,
                            evidence_graph=scenario.evidence_graph,
                            num_trials=1,
                            cost_model=cost_model,
                        )
                        cascade_result = cascade_est.estimate_set(selected_cis)
                        cee_set = cascade_result.cee
                        prevention_rate = cascade_result.prevention_rate

                # Compute metrics
                metric_eval = MetricEvaluator()
                metrics = metric_eval.compute(
                    selection,
                    gt,
                    k=self._k,
                    cee_set=cee_set,
                    prevention_rate=prevention_rate,
                    cost_model=cost_model,
                    lambda_cost=self._lambda_cost,
                    oracle_result=oracle_res,
                )

                all_results.append(
                    MethodResult(
                        scenario_id=scenario.scenario_id,
                        method_name=method.name,
                        selection=selection,
                        metrics=metrics,
                    )
                )

        return BenchmarkResult(
            results=all_results,
            oracle_results=oracle_results,
        )

    def _default_methods(
        self,
        scenarios: list[BenchmarkScenario],
    ) -> list[BaselineMethod]:
        """Build default method set: B1-B5 + A2-A5."""
        seed = scenarios[0].seed if scenarios else 42
        return [
            RandomBaseline(scenario_seed=seed),
            ProvenanceOnlyBaseline(),
            CEERankBaseline(),
            GraphStructuralBaseline(),
            CostAwareBaseline(),
            # A1 = B2, not included separately to avoid double-counting
            CELAMethod(level=2),
            CELAMethod(level=3),
            CELAMethod(level=4),
            CELAMethod(level=5),
        ]
