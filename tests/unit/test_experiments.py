"""Stage 17 experiment tests.

Tests cover:
1. Deterministic experiment reproduction
2. Independent scenario seed generation
3. Aggregate metric calculation
4. Bootstrap CI determinism
5. Insufficient-sample CI handling
6. Paired comparison correctness
7. Multiple-comparison correction (Holm-Bonferroni)
8. Effect-size calculation
9. Oracle regret aggregation
10. Failure classification
11. Reproducibility metadata
12. Serialization round-trip
13. A1-A5 experiment execution
14. B1-B5 experiment execution
15. Sensitivity configuration
16. Full small end-to-end experiment
"""

from __future__ import annotations

from captain.experiments.runner import (
    ExperimentConfig,
    ExperimentResult,
    ExperimentRunner,
    _generate_instances,
)
from captain.experiments.statistics import (
    AggregateSummary,
    ComparisonResult,
    ConfidenceInterval,
    FailureAccount,
    SensitivityPoint,
    bootstrap_ci,
    compute_ablation_ladder,
    compute_aggregate,
    compute_sensitivity,
    holm_bonferroni,
    paired_comparison,
)

# ===================================================================
# 1. Deterministic experiment reproduction
# ===================================================================


class TestDeterministicReproduction:
    def test_same_seed_same_structure(self) -> None:
        cfg = ExperimentConfig(
            master_seed=99,
            instances_per_family=2,
            families=["BF-A"],
            methods=["B1", "B2"],
        )
        r1 = ExperimentRunner(cfg).run()
        r2 = ExperimentRunner(cfg).run()

        # Same number of results
        assert len(r1.family_results["BF-A"].results) == len(r2.family_results["BF-A"].results)
        # Same methods
        m1 = sorted(r1.overall_aggregates.keys())
        m2 = sorted(r2.overall_aggregates.keys())
        assert m1 == m2
        # Same number of scenarios per method
        for mname in m1:
            n1 = r1.overall_aggregates[mname].n_scenarios
            n2 = r2.overall_aggregates[mname].n_scenarios
            assert n1 == n2
        # Same metadata
        assert r1.metadata.total_scenarios == r2.metadata.total_scenarios


# ===================================================================
# 2. Independent scenario seed generation
# ===================================================================


class TestScenarioSeedGeneration:
    def test_different_instances_different_seeds(self) -> None:
        instances = _generate_instances("BF-A", 3, master_seed=42)
        assert len(instances) == 3
        # Each instance should have a different seed
        seeds = [s.seed for s in instances]
        assert len(set(seeds)) == 3

    def test_different_families_different_seeds(self) -> None:
        a_instances = _generate_instances("BF-A", 2, master_seed=42)
        b_instances = _generate_instances("BF-B", 2, master_seed=42)
        a_seeds = {s.seed for s in a_instances}
        b_seeds = {s.seed for s in b_instances}
        assert a_seeds != b_seeds


# ===================================================================
# 3. Aggregate metric calculation
# ===================================================================


class TestAggregateMetric:
    def test_basic_aggregate(self) -> None:
        agg = compute_aggregate("test", [1.0, 2.0, 3.0, 4.0, 5.0])
        assert agg.n == 5
        assert agg.mean == 3.0
        assert agg.median == 3.0
        assert agg.min_val == 1.0
        assert agg.max_val == 5.0
        assert agg.std > 0

    def test_empty_aggregate(self) -> None:
        agg = compute_aggregate("test", [])
        assert agg.n == 0
        assert agg.mean == 0.0

    def test_single_value(self) -> None:
        agg = compute_aggregate("test", [42.0])
        assert agg.n == 1
        assert agg.mean == 42.0
        assert agg.median == 42.0


# ===================================================================
# 4. Bootstrap CI determinism
# ===================================================================


class TestBootstrapCI:
    def test_deterministic(self) -> None:
        vals = [0.5, 0.6, 0.7, 0.8, 0.9]
        ci1 = bootstrap_ci("f1", vals, seed=42)
        ci2 = bootstrap_ci("f1", vals, seed=42)
        assert ci1.ci_lower == ci2.ci_lower
        assert ci1.ci_upper == ci2.ci_upper

    def test_ci_contains_mean(self) -> None:
        vals = [0.5, 0.6, 0.7, 0.8, 0.9]
        ci = bootstrap_ci("f1", vals, seed=42)
        assert ci.ci_lower <= ci.point_estimate <= ci.ci_upper

    def test_confidence_level_stored(self) -> None:
        ci = bootstrap_ci("f1", [1.0, 2.0, 3.0], confidence_level=0.90)
        assert ci.confidence_level == 0.90


# ===================================================================
# 5. Insufficient-sample CI handling
# ===================================================================


class TestInsufficientSampleCI:
    def test_insufficient_returns_flag(self) -> None:
        ci = bootstrap_ci("f1", [0.5], min_samples=3)
        assert ci.sufficient is False
        assert ci.n_bootstrap == 0
        assert ci.n_samples == 1

    def test_empty_returns_insufficient(self) -> None:
        ci = bootstrap_ci("f1", [], min_samples=3)
        assert ci.sufficient is False
        assert ci.point_estimate == 0.0

    def test_sufficient_returns_flag(self) -> None:
        ci = bootstrap_ci("f1", [0.5, 0.6, 0.7], min_samples=3)
        assert ci.sufficient is True
        assert ci.n_bootstrap > 0


# ===================================================================
# 6. Paired comparison correctness
# ===================================================================


class TestPairedComparison:
    def test_identical_values_not_significant(self) -> None:
        vals = [0.5, 0.6, 0.7, 0.8, 0.9]
        comp = paired_comparison("A", "B", "f1", vals, vals)
        assert comp.mean_diff == 0.0
        assert comp.significant is False

    def test_clearly_different_values(self) -> None:
        a = [0.9, 0.95, 0.85, 0.92, 0.88, 0.91]
        b = [0.1, 0.15, 0.05, 0.12, 0.08, 0.11]
        comp = paired_comparison("A", "B", "f1", a, b)
        assert comp.mean_diff > 0
        assert comp.p_value < 0.05

    def test_insufficient_pairs(self) -> None:
        comp = paired_comparison("A", "B", "f1", [0.5], [0.3], min_pairs=3)
        assert comp.sufficient is False


# ===================================================================
# 7. Multiple-comparison correction (Holm-Bonferroni)
# ===================================================================


class TestHolmBonferroni:
    def test_adjusts_p_values(self) -> None:
        results = [
            ComparisonResult(
                method_a="A",
                method_b="B",
                metric_name="f1",
                test_name="test",
                p_value=0.01,
            ),
            ComparisonResult(
                method_a="A",
                method_b="B",
                metric_name="recall",
                test_name="test",
                p_value=0.04,
            ),
            ComparisonResult(
                method_a="A",
                method_b="B",
                metric_name="precision",
                test_name="test",
                p_value=0.03,
            ),
        ]
        corrected = holm_bonferroni(results, alpha=0.05)

        # Adjusted p-values should be >= raw p-values
        for orig, corr in zip(results, corrected, strict=True):
            assert corr.adjusted_p_value >= orig.p_value

        # Correction method recorded
        assert all(c.correction_method == "holm_bonferroni" for c in corrected)

    def test_preserves_original_order(self) -> None:
        results = [
            ComparisonResult(
                method_a="A",
                method_b="B",
                metric_name="f1",
                test_name="test",
                p_value=0.04,
            ),
            ComparisonResult(
                method_a="A",
                method_b="B",
                metric_name="recall",
                test_name="test",
                p_value=0.01,
            ),
        ]
        corrected = holm_bonferroni(results)
        assert corrected[0].metric_name == "f1"
        assert corrected[1].metric_name == "recall"

    def test_empty_list(self) -> None:
        assert holm_bonferroni([]) == []


# ===================================================================
# 8. Effect-size calculation
# ===================================================================


class TestEffectSize:
    def test_effect_size_computed(self) -> None:
        a = [0.9, 0.85, 0.92, 0.88, 0.91, 0.87]
        b = [0.1, 0.15, 0.12, 0.08, 0.11, 0.13]
        comp = paired_comparison("A", "B", "f1", a, b)
        assert comp.effect_size is not None
        assert comp.effect_size_name == "paired_cohens_d"
        assert comp.effect_size > 0  # A is much better

    def test_zero_diff_zero_effect(self) -> None:
        vals = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        comp = paired_comparison("A", "B", "f1", vals, vals)
        assert comp.effect_size == 0.0


# ===================================================================
# 9. Oracle regret aggregation
# ===================================================================


class TestOracleRegretAggregation:
    def test_oracle_aggregates_computed(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=3,
            families=["BF-A"],
            methods=["B1", "B2"],
            run_oracle=True,
        )
        result = ExperimentRunner(cfg).run()
        assert "oracle_objective" in result.oracle_aggregates
        assert result.oracle_aggregates["oracle_objective"].n >= 1


# ===================================================================
# 10. Failure classification
# ===================================================================


class TestFailureClassification:
    def test_successful_runs_counted(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=2,
            families=["BF-A"],
            methods=["B1"],
        )
        result = ExperimentRunner(cfg).run()
        assert result.failure_account.successful > 0
        assert result.failure_account.total_evaluations > 0

    def test_failure_account_model(self) -> None:
        fa = FailureAccount(total_evaluations=10, successful=8, replay_failure=2)
        assert fa.total_evaluations == 10
        assert fa.successful == 8


# ===================================================================
# 11. Reproducibility metadata
# ===================================================================


class TestReproducibilityMetadata:
    def test_metadata_populated(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=2,
            families=["BF-A"],
            methods=["B1"],
        )
        result = ExperimentRunner(cfg).run()
        meta = result.metadata
        assert meta.master_seed == 42
        assert meta.total_scenarios == 2
        assert meta.experiment_id != ""
        assert meta.start_time != ""
        assert meta.end_time != ""


# ===================================================================
# 12. Serialization round-trip
# ===================================================================


class TestSerializationRoundTrip:
    def test_experiment_result_serializes(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=2,
            families=["BF-A"],
            methods=["B1", "B2"],
        )
        result = ExperimentRunner(cfg).run()
        data = result.model_dump()
        restored = ExperimentResult.model_validate(data)
        assert restored.metadata.master_seed == 42
        assert len(restored.family_results) == 1

    def test_aggregate_summary_serializes(self) -> None:
        agg = compute_aggregate("f1", [0.5, 0.6, 0.7])
        data = agg.model_dump()
        restored = AggregateSummary.model_validate(data)
        assert restored.n == 3

    def test_ci_serializes(self) -> None:
        ci = bootstrap_ci("f1", [0.5, 0.6, 0.7])
        data = ci.model_dump()
        restored = ConfidenceInterval.model_validate(data)
        assert restored.sufficient is True


# ===================================================================
# 13. A1-A5 experiment execution
# ===================================================================


class TestCELAExecution:
    def test_a1_through_a5_run(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=2,
            families=["BF-A"],
            methods=["A1", "A2", "A3", "A4", "A5"],
        )
        result = ExperimentRunner(cfg).run()
        method_names = {
            mr.method_name for br in result.family_results.values() for mr in br.results
        }
        assert "A1_cela" in method_names
        assert "A2_cela" in method_names
        assert "A3_cela" in method_names
        assert "A4_cela" in method_names
        assert "A5_cela" in method_names


# ===================================================================
# 14. B1-B5 experiment execution
# ===================================================================


class TestBaselineExecution:
    def test_b1_through_b5_run(self) -> None:
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=2,
            families=["BF-A"],
            methods=["B1", "B2", "B3", "B4", "B5"],
        )
        result = ExperimentRunner(cfg).run()
        method_names = {
            mr.method_name for br in result.family_results.values() for mr in br.results
        }
        assert "B1_random" in method_names
        assert "B2_provenance" in method_names
        assert "B3_cee_rank" in method_names
        assert "B4_graph_structural" in method_names
        assert "B5_cost_aware" in method_names


# ===================================================================
# 15. Sensitivity configuration
# ===================================================================


class TestSensitivityConfig:
    def test_sensitivity_point_model(self) -> None:
        sp = SensitivityPoint(
            parameter_name="k",
            parameter_value=3,
            metric_name="f1",
            metric_value=0.8,
            n_instances=5,
        )
        assert sp.parameter_name == "k"

    def test_sensitivity_result_stability(self) -> None:
        points = [
            SensitivityPoint(
                parameter_name="k",
                parameter_value=i,
                metric_name="f1",
                metric_value=0.8 + 0.01 * i,
            )
            for i in range(5)
        ]
        sr = compute_sensitivity("k", "f1", "A4_cela", points)
        assert sr.parameter_name == "k"
        assert sr.is_stable  # Low variation


# ===================================================================
# 16. Full small end-to-end experiment
# ===================================================================


class TestFullEndToEnd:
    def test_complete_experiment(self) -> None:
        """Full experiment with all families and several methods."""
        cfg = ExperimentConfig(
            master_seed=42,
            instances_per_family=3,
            families=["BF-A", "BF-B", "BF-C"],
            methods=["B1", "B2", "A2", "A4"],
            run_oracle=True,
            bootstrap_resamples=100,  # Reduced for speed
        )
        result = ExperimentRunner(cfg).run()

        # All families present
        assert "BF-A" in result.family_results
        assert "BF-B" in result.family_results
        assert "BF-C" in result.family_results

        # Aggregates computed
        assert len(result.overall_aggregates) == 4
        for _mname, ma in result.overall_aggregates.items():
            assert ma.n_scenarios > 0
            assert "causal_f1" in ma.summaries

        # Family aggregates
        assert len(result.family_aggregates) == 3

        # Oracle results
        assert len(result.oracle_aggregates) > 0

        # Comparisons (3 instances >= min_pairs)
        assert len(result.comparisons) > 0
        # All corrected
        assert all(c.correction_method == "holm_bonferroni" for c in result.comparisons)

        # CIs computed
        for _mname, ma in result.overall_aggregates.items():
            if "causal_f1" in ma.confidence_intervals:
                ci = ma.confidence_intervals["causal_f1"]
                assert ci.sufficient is True
                assert ci.ci_lower <= ci.ci_upper

        # Ablation computed
        assert len(result.ablation_steps) > 0

        # Failure accounting
        assert result.failure_account.successful > 0

        # Metadata
        assert result.metadata.total_scenarios == 9  # 3 families * 3 instances

        # Serialization
        data = result.model_dump()
        restored = ExperimentResult.model_validate(data)
        assert restored.metadata.master_seed == 42


# ===================================================================
# Additional: Ablation ladder
# ===================================================================


class TestAblationLadder:
    def test_ablation_steps_computed(self) -> None:
        level_values = {
            "A1_cela": [0.3, 0.4, 0.35],
            "A2_cela": [0.5, 0.6, 0.55],
            "A4_cela": [0.7, 0.8, 0.75],
        }
        steps = compute_ablation_ladder("causal_f1", level_values)
        assert len(steps) == 2  # A1->A2, A2->A4
        assert steps[0].from_config == "A1_cela"
        assert steps[0].to_config == "A2_cela"
        assert steps[0].delta > 0
        # Comparison performed (n=3 >= min_pairs)
        assert steps[0].comparison is not None

    def test_empty_ladder(self) -> None:
        steps = compute_ablation_ladder("f1", {})
        assert steps == []
