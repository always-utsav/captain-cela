"""CELA experiment runner -- Stage 17.

Multi-instance experimental execution with reproducibility,
aggregate metrics, confidence intervals, statistical
comparisons, sensitivity analysis, and result serialization.

Reuses Stage 16 BenchmarkRunner, scenarios, baselines, and metrics.

Hierarchy:
    Experiment
      -> benchmark family
        -> scenario instance (independent experimental unit)
          -> method/configuration
            -> intervention evaluation
              -> replay/trial

The scenario instance is the primary independent experimental unit.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from captain.benchmarks.baselines import (
    BaselineMethod,
    CELAMethod,
    CostAwareBaseline,
    GraphStructuralBaseline,
    ProvenanceOnlyBaseline,
    RandomBaseline,
)
from captain.benchmarks.baselines import (
    CEERankBaseline as _CEERankBaseline,
)
from captain.benchmarks.runner import (
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkRunner,
)
from captain.benchmarks.scenarios import (
    BenchmarkScenario,
    generate_branching,
    generate_cascade,
    generate_complementary,
    generate_convergent,
    generate_cost_asymmetric,
    generate_distractor,
    generate_downstream_repair,
    generate_redundant,
    generate_root_vs_symptom,
    generate_shared_source,
    generate_single_cause,
)
from captain.experiments.statistics import (
    AblationStep,
    AggregateSummary,
    ComparisonResult,
    ConfidenceInterval,
    FailureAccount,
    SensitivityPoint,
    SensitivityResult,
    bootstrap_ci,
    compute_ablation_ladder,
    compute_aggregate,
    compute_sensitivity,
    holm_bonferroni,
    paired_comparison,
)

# ===================================================================
# Configuration
# ===================================================================


class ExperimentConfig(BaseModel):
    """Experiment configuration with modest defaults."""

    master_seed: int = 42
    instances_per_family: int = 5
    k: int = 2
    max_set_size: int = 3
    lambda_cost: float = 0.1
    max_replay_evaluations: int = 20
    bootstrap_resamples: int = 2000
    bootstrap_seed: int = 42
    confidence_level: float = 0.95
    comparison_alpha: float = 0.05
    min_samples_for_ci: int = 3
    run_oracle: bool = True
    families: list[str] = Field(
        default_factory=lambda: [
            "BF-A",
            "BF-B",
            "BF-C",
            "BF-D",
            "BF-E",
            "BF-F",
            "BF-G",
            "BF-H",
            "BF-I",
            "BF-J",
            "BF-K",
        ]
    )
    methods: list[str] = Field(
        default_factory=lambda: [
            "B1",
            "B2",
            "B3",
            "B4",
            "B5",
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
        ]
    )
    # Equivalences: documented, not double-counted in aggregate comparisons
    equivalences: dict[str, str] = Field(default_factory=lambda: {"A1": "B2", "A2": "B3"})


# ===================================================================
# Reproducibility metadata
# ===================================================================


class ReproducibilityMetadata(BaseModel):
    """Metadata for reproducible experiment runs."""

    experiment_id: str = ""
    master_seed: int = 0
    config: ExperimentConfig = Field(default_factory=ExperimentConfig)
    start_time: str = ""
    end_time: str = ""
    total_scenarios: int = 0
    total_method_evaluations: int = 0
    captain_version: str = "stage-17"


# ===================================================================
# Method aggregate results
# ===================================================================


class MethodAggregate(BaseModel):
    """Aggregate metrics for one method across all scenario instances."""

    method_name: str
    n_scenarios: int = 0
    summaries: dict[str, AggregateSummary] = Field(default_factory=dict)
    confidence_intervals: dict[str, ConfidenceInterval] = Field(default_factory=dict)


class FamilyAggregate(BaseModel):
    """Aggregate metrics for one benchmark family."""

    family: str
    n_instances: int = 0
    method_aggregates: dict[str, MethodAggregate] = Field(default_factory=dict)


# ===================================================================
# Experiment result
# ===================================================================


class ExperimentResult(BaseModel):
    """Complete experiment result. Serializable."""

    metadata: ReproducibilityMetadata = Field(default_factory=ReproducibilityMetadata)
    config: ExperimentConfig = Field(default_factory=ExperimentConfig)
    # Per-family results
    family_results: dict[str, BenchmarkResult] = Field(default_factory=dict)
    # Aggregate metrics
    overall_aggregates: dict[str, MethodAggregate] = Field(default_factory=dict)
    family_aggregates: dict[str, FamilyAggregate] = Field(default_factory=dict)
    # Statistical comparisons
    comparisons: list[ComparisonResult] = Field(default_factory=list)
    # Ablation analysis
    ablation_steps: list[AblationStep] = Field(default_factory=list)
    # Oracle aggregates
    oracle_aggregates: dict[str, AggregateSummary] = Field(default_factory=dict)
    # Sensitivity results
    sensitivity_results: list[SensitivityResult] = Field(default_factory=list)
    # Failure accounting
    failure_account: FailureAccount = Field(default_factory=FailureAccount)


# ===================================================================
# Scenario generation
# ===================================================================

# Family -> generator function
_FAMILY_GENERATORS: dict[str, Any] = {
    "BF-A": generate_single_cause,
    "BF-B": generate_redundant,
    "BF-C": generate_complementary,
    "BF-D": generate_distractor,
    "BF-E": generate_cascade,
    "BF-F": generate_cost_asymmetric,
    "BF-G": generate_shared_source,
    "BF-H": generate_branching,
    "BF-I": generate_convergent,
    "BF-J": generate_root_vs_symptom,
    "BF-K": generate_downstream_repair,
}


def _generate_instances(
    family: str,
    n_instances: int,
    master_seed: int,
) -> list[BenchmarkScenario]:
    """Generate multiple independent scenario instances for a family."""
    if family not in _FAMILY_GENERATORS:
        return []
    gen = _FAMILY_GENERATORS[family]

    instances: list[BenchmarkScenario] = []
    for i in range(n_instances):
        # Deterministic seed derivation
        # Deterministic family offset (avoid hash() which is randomized)
        family_offset = list(_FAMILY_GENERATORS.keys()).index(family) * 100
        instance_seed = master_seed * 10000 + family_offset + i
        scenario = gen(seed=instance_seed)
        instances.append(scenario)

    return instances


# ===================================================================
# Method construction
# ===================================================================


def _build_methods(
    config: ExperimentConfig,
    scenario_seed: int,
) -> list[BaselineMethod]:
    """Build method instances from config."""
    method_map: dict[str, BaselineMethod] = {
        "B1": RandomBaseline(scenario_seed=scenario_seed),
        "B2": ProvenanceOnlyBaseline(),
        "B3": _CEERankBaseline(),
        "B4": GraphStructuralBaseline(),
        "B5": CostAwareBaseline(),
        "A1": CELAMethod(level=1),
        "A2": CELAMethod(level=2),
        "A3": CELAMethod(level=3),
        "A4": CELAMethod(level=4),
        "A5": CELAMethod(level=5),
    }
    return [method_map[m] for m in config.methods if m in method_map]


# ===================================================================
# Metric extraction
# ===================================================================

# Primary metrics to track
PRIMARY_METRICS = [
    "causal_precision",
    "causal_recall",
    "causal_f1",
    "recall_at_1",
    "failure_prevention_rate",
    "prevention_set_recall",
    "cee_set",
]

SECONDARY_METRICS = [
    "origin_recall",
    "distractor_false_selection_rate",
    "complementary_group_recovery_rate",
    "redundancy_group_coverage",
    "intervention_cost",
    "set_size",
    "replay_count",
    "regret",
    "utility",
]

ALL_METRICS = PRIMARY_METRICS + SECONDARY_METRICS


def _extract_metric(metrics: BenchmarkMetrics, metric_name: str) -> float | None:
    """Extract a named metric value from BenchmarkMetrics."""
    mapping: dict[str, Any] = {
        "causal_precision": metrics.attribution.causal_precision,
        "causal_recall": metrics.attribution.causal_recall,
        "causal_f1": metrics.attribution.causal_f1,
        "recall_at_1": metrics.attribution.recall_at_1,
        "recall_at_k": metrics.attribution.recall_at_k,
        "failure_prevention_rate": metrics.prevention.failure_prevention_rate,
        "prevention_set_recall": metrics.prevention.prevention_set_recall,
        "cee_set": metrics.prevention.cee_set,
        "origin_recall": metrics.localization.origin_recall,
        "propagation_recall": metrics.localization.propagation_recall,
        "actuator_recall": metrics.localization.actuator_recall,
        "distractor_false_selection_rate": metrics.discrimination.distractor_false_selection_rate,
        "complementary_group_recovery_rate": metrics.interaction.complementary_group_recovery_rate,
        "redundancy_group_coverage": metrics.interaction.redundancy_group_coverage,
        "intervention_cost": metrics.efficiency.intervention_cost,
        "set_size": float(metrics.efficiency.set_size),
        "replay_count": float(metrics.efficiency.replay_count),
        "regret": metrics.optimality.regret,
        "utility": metrics.efficiency.utility,
    }
    return mapping.get(metric_name)


# ===================================================================
# Experiment runner
# ===================================================================


class ExperimentRunner:
    """Multi-instance experiment runner with statistical analysis.

    Reuses Stage 16 BenchmarkRunner for per-scenario evaluation.
    Adds multi-instance generation, aggregation, confidence intervals,
    paired comparisons, and sensitivity analysis.
    """

    def __init__(self, config: ExperimentConfig | None = None) -> None:
        self._config = config or ExperimentConfig()

    def run(self) -> ExperimentResult:
        """Execute the full experiment."""
        config = self._config
        start_time = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Generate scenarios
        all_family_scenarios: dict[str, list[BenchmarkScenario]] = {}
        total_scenarios = 0

        for family in config.families:
            instances = _generate_instances(
                family, config.instances_per_family, config.master_seed
            )
            all_family_scenarios[family] = instances
            total_scenarios += len(instances)

        # Build methods
        methods = _build_methods(config, config.master_seed)

        # Run benchmark per family
        family_results: dict[str, BenchmarkResult] = {}
        failure_account = FailureAccount()
        total_evals = 0

        benchmark_runner = BenchmarkRunner(
            k=config.k,
            max_set_size=config.max_set_size,
            lambda_cost=config.lambda_cost,
        )

        for family, scenarios in all_family_scenarios.items():
            if not scenarios:
                continue

            try:
                result = benchmark_runner.run(scenarios, methods, run_oracle=config.run_oracle)
                family_results[family] = result
                failure_account.successful += len(result.results)
                total_evals += len(result.results)
                failure_account.total_evaluations += len(result.results)
            except Exception:
                failure_account.invalid_scenario += len(scenarios)
                failure_account.total_evaluations += len(scenarios)
                failure_account.exclusion_reasons[f"{family}_execution_error"] = len(scenarios)

        # Compute aggregates
        overall_aggregates = self._compute_overall_aggregates(family_results, methods)
        family_aggregates = self._compute_family_aggregates(family_results, methods)

        # Oracle aggregates
        oracle_aggregates = self._compute_oracle_aggregates(family_results)

        # Statistical comparisons: each method vs B1 (random)
        comparisons = self._compute_comparisons(family_results, methods)

        # Ablation analysis
        ablation_steps = self._compute_ablation(family_results)

        end_time = time.strftime("%Y-%m-%dT%H:%M:%S")

        metadata = ReproducibilityMetadata(
            experiment_id=f"exp_{config.master_seed}_{total_scenarios}",
            master_seed=config.master_seed,
            config=config,
            start_time=start_time,
            end_time=end_time,
            total_scenarios=total_scenarios,
            total_method_evaluations=total_evals,
        )

        return ExperimentResult(
            metadata=metadata,
            config=config,
            family_results=family_results,
            overall_aggregates=overall_aggregates,
            family_aggregates=family_aggregates,
            comparisons=comparisons,
            ablation_steps=ablation_steps,
            oracle_aggregates=oracle_aggregates,
            failure_account=failure_account,
        )

    def _collect_method_values(
        self,
        family_results: dict[str, BenchmarkResult],
        method_name: str,
        metric_name: str,
    ) -> list[float]:
        """Collect metric values for a method across all scenarios."""
        values: list[float] = []
        for _family, br in family_results.items():
            for mr in br.results:
                if mr.method_name == method_name:
                    val = _extract_metric(mr.metrics, metric_name)
                    if val is not None:
                        values.append(val)
        return values

    def _compute_overall_aggregates(
        self,
        family_results: dict[str, BenchmarkResult],
        methods: list[BaselineMethod],
    ) -> dict[str, MethodAggregate]:
        """Compute aggregate metrics for each method across all families."""
        config = self._config
        aggregates: dict[str, MethodAggregate] = {}

        for method in methods:
            mname = method.name
            summaries: dict[str, AggregateSummary] = {}
            cis: dict[str, ConfidenceInterval] = {}

            for metric in ALL_METRICS:
                values = self._collect_method_values(family_results, mname, metric)
                if values:
                    summaries[metric] = compute_aggregate(metric, values)
                    cis[metric] = bootstrap_ci(
                        metric,
                        values,
                        confidence_level=config.confidence_level,
                        n_bootstrap=config.bootstrap_resamples,
                        seed=config.bootstrap_seed,
                        min_samples=config.min_samples_for_ci,
                    )

            n_scenarios = sum(
                1 for br in family_results.values() for mr in br.results if mr.method_name == mname
            )

            aggregates[mname] = MethodAggregate(
                method_name=mname,
                n_scenarios=n_scenarios,
                summaries=summaries,
                confidence_intervals=cis,
            )

        return aggregates

    def _compute_family_aggregates(
        self,
        family_results: dict[str, BenchmarkResult],
        methods: list[BaselineMethod],
    ) -> dict[str, FamilyAggregate]:
        """Compute per-family aggregates."""
        config = self._config
        result: dict[str, FamilyAggregate] = {}

        for family, br in family_results.items():
            method_aggs: dict[str, MethodAggregate] = {}

            for method in methods:
                mname = method.name
                family_mrs = [mr for mr in br.results if mr.method_name == mname]

                summaries: dict[str, AggregateSummary] = {}
                cis: dict[str, ConfidenceInterval] = {}

                for metric in ALL_METRICS:
                    values: list[float] = []
                    for mr in family_mrs:
                        val = _extract_metric(mr.metrics, metric)
                        if val is not None:
                            values.append(val)

                    if values:
                        summaries[metric] = compute_aggregate(metric, values)
                        cis[metric] = bootstrap_ci(
                            metric,
                            values,
                            confidence_level=config.confidence_level,
                            n_bootstrap=config.bootstrap_resamples,
                            seed=config.bootstrap_seed,
                            min_samples=config.min_samples_for_ci,
                        )

                method_aggs[mname] = MethodAggregate(
                    method_name=mname,
                    n_scenarios=len(family_mrs),
                    summaries=summaries,
                    confidence_intervals=cis,
                )

            n_instances = len({mr.scenario_id for mr in br.results})
            result[family] = FamilyAggregate(
                family=family,
                n_instances=n_instances,
                method_aggregates=method_aggs,
            )

        return result

    def _compute_oracle_aggregates(
        self,
        family_results: dict[str, BenchmarkResult],
    ) -> dict[str, AggregateSummary]:
        """Aggregate oracle results across scenarios."""
        objectives: list[float] = []
        sets_evaluated: list[float] = []

        for _family, br in family_results.items():
            for _sid, orc in br.oracle_results.items():
                objectives.append(orc.optimal_objective)
                sets_evaluated.append(float(orc.sets_evaluated))

        result: dict[str, AggregateSummary] = {}
        if objectives:
            result["oracle_objective"] = compute_aggregate("oracle_objective", objectives)
            result["oracle_sets_evaluated"] = compute_aggregate(
                "oracle_sets_evaluated", sets_evaluated
            )
        return result

    def _compute_comparisons(
        self,
        family_results: dict[str, BenchmarkResult],
        methods: list[BaselineMethod],
    ) -> list[ComparisonResult]:
        """Compute paired comparisons between methods.

        Compares each method against B1 (random baseline) on primary metrics.
        Also compares adjacent CELA levels.
        Applies Holm-Bonferroni correction.
        """
        config = self._config
        all_comparisons: list[ComparisonResult] = []

        # Find B1 name
        b1_name = ""
        method_names: list[str] = []
        for m in methods:
            method_names.append(m.name)
            if isinstance(m, RandomBaseline):
                b1_name = m.name

        if not b1_name:
            return []

        # Compare each non-B1 method vs B1 on primary metrics
        for metric in PRIMARY_METRICS:
            b1_values = self._collect_method_values(family_results, b1_name, metric)

            for mname in method_names:
                if mname == b1_name:
                    continue
                # Skip documented equivalences to avoid double-counting
                m_values = self._collect_method_values(family_results, mname, metric)

                comp = paired_comparison(
                    mname,
                    b1_name,
                    metric,
                    m_values,
                    b1_values,
                    alpha=config.comparison_alpha,
                    seed=config.bootstrap_seed,
                )
                if comp.sufficient:
                    all_comparisons.append(comp)

        # Apply Holm-Bonferroni correction
        if all_comparisons:
            all_comparisons = holm_bonferroni(all_comparisons, alpha=config.comparison_alpha)

        return all_comparisons

    def _compute_ablation(
        self,
        family_results: dict[str, BenchmarkResult],
    ) -> list[AblationStep]:
        """Compute ablation analysis across the A1-A5 ladder."""
        config = self._config
        all_steps: list[AblationStep] = []

        for metric in PRIMARY_METRICS:
            level_values: dict[str, list[float]] = {}
            for level in ["A1_cela", "A2_cela", "A3_cela", "A4_cela", "A5_cela"]:
                values = self._collect_method_values(family_results, level, metric)
                if values:
                    level_values[level] = values

            steps = compute_ablation_ladder(
                metric,
                level_values,
                alpha=config.comparison_alpha,
                seed=config.bootstrap_seed,
            )
            all_steps.extend(steps)

        return all_steps

    def run_sensitivity(
        self,
        parameter_name: str,
        parameter_values: list[Any],
        *,
        base_config: ExperimentConfig | None = None,
        target_metric: str = "causal_f1",
        target_method: str = "A4_cela",
    ) -> list[SensitivityResult]:
        """Run sensitivity analysis for one parameter.

        Generates experiments with each parameter value and collects
        the target metric for the target method.
        """
        cfg = base_config or self._config
        points: list[SensitivityPoint] = []

        for val in parameter_values:
            # Create modified config
            modified = cfg.model_copy(update={parameter_name: val})
            runner = ExperimentRunner(config=modified)
            result = runner.run()

            # Extract metric
            agg = result.overall_aggregates.get(target_method)
            metric_val = 0.0
            n_instances = 0
            if agg and target_metric in agg.summaries:
                metric_val = agg.summaries[target_metric].mean
                n_instances = agg.summaries[target_metric].n

            points.append(
                SensitivityPoint(
                    parameter_name=parameter_name,
                    parameter_value=val,
                    metric_name=target_metric,
                    metric_value=metric_val,
                    n_instances=n_instances,
                )
            )

        return [compute_sensitivity(parameter_name, target_metric, target_method, points)]
