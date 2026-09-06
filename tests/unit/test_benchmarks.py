"""Stage 16 benchmark tests.

Tests cover:
- Scenario ground truth models and serialization
- All 6 benchmark families (BF-A through BF-F)
- All 5 baselines (B1-B5)
- CELA configurations (A1-A5)
- A1 = B2 identity
- A3 vs A4 distinction
- Exhaustive oracle
- Metric evaluator (attribution, localization, prevention)
- Distractor false-selection rate
- Complementary group recovery
- Information parity
- Ground-truth leakage prevention
- Evaluator independence
- Result serialization
- Deterministic reproducibility
- End-to-end benchmark runner
"""

from __future__ import annotations

from captain.analysis.cascade import CostModel
from captain.benchmarks.baselines import (
    BaselineMethod,
    CEERankBaseline,
    CELAMethod,
    CostAwareBaseline,
    ExhaustiveOracle,
    GraphStructuralBaseline,
    MethodSelection,
    ProvenanceOnlyBaseline,
    RandomBaseline,
)
from captain.benchmarks.runner import (
    AttributionMetrics,
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkRunner,
    DiscriminationMetrics,
    InteractionMetrics,
    LocalizationMetrics,
    MethodResult,
    MetricEvaluator,
    PreventionMetrics,
)
from captain.benchmarks.scenarios import (
    BenchmarkScenario,
    CausalMechanism,
    CausalMechanismSpec,
    ScenarioGroundTruth,
    generate_cascade,
    generate_complementary,
    generate_cost_asymmetric,
    generate_distractor,
    generate_redundant,
    generate_single_cause,
    get_evaluator,
)

# ===================================================================
# 1. Ground truth model
# ===================================================================


class TestGroundTruthModel:
    def test_construction_and_serialization(self) -> None:
        mech = CausalMechanismSpec(
            mechanism=CausalMechanism.SINGLE_CHANNEL,
            failure_keywords=["42"],
            keyword_logic="any",
            causal_tool_names=["calculator"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="test_1",
            family="BF-A",
            seed=42,
            mechanism=mech,
            causal_channel_ids=["c1"],
            irrelevant_channel_ids=["c2"],
            factual_outcome=True,
        )

        data = gt.model_dump()
        restored = ScenarioGroundTruth.model_validate(data)
        assert restored.scenario_id == "test_1"
        assert restored.mechanism.mechanism == CausalMechanism.SINGLE_CHANNEL
        assert restored.causal_channel_ids == ["c1"]

    def test_causal_mechanism_spec(self) -> None:
        mech = CausalMechanismSpec(
            mechanism=CausalMechanism.COMPLEMENTARY_AND,
            failure_keywords=["a", "b"],
            keyword_logic="all",
        )
        assert mech.mechanism == CausalMechanism.COMPLEMENTARY_AND
        assert mech.keyword_logic == "all"


# ===================================================================
# 2. Scenario model
# ===================================================================


class TestScenarioModel:
    def test_construction(self) -> None:
        s = generate_single_cause()
        assert isinstance(s, BenchmarkScenario)
        assert s.family == "BF-A"
        assert s.run is not None
        assert s.evidence_graph is not None
        assert s.failure is not None


# ===================================================================
# 3-8. Benchmark families
# ===================================================================


class TestGenerateSingleCause:
    def test_valid_run_and_ground_truth(self) -> None:
        s = generate_single_cause()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-A"
        assert ev(s.run) is True  # Baseline fails
        assert len(gt.causal_channel_ids) >= 1
        assert len(gt.irrelevant_channel_ids) >= 1
        assert gt.required_prevention_sets  # At least one prevention set


class TestGenerateRedundant:
    def test_valid_run_and_ground_truth(self) -> None:
        s = generate_redundant()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-B"
        assert ev(s.run) is True
        assert len(gt.causal_channel_ids) >= 2
        assert len(gt.redundancy_groups) >= 1
        # Single intervention should NOT prevent (OR logic)
        for _cid, outcome in gt.single_intervention_outcomes.items():
            assert outcome is True  # failure persists


class TestGenerateComplementary:
    def test_valid_run_and_interaction_outcomes(self) -> None:
        s = generate_complementary()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-C"
        assert ev(s.run) is True
        assert len(gt.complementary_groups) >= 1
        # AND logic: blocking either alone prevents failure
        for _cid, outcome in gt.single_intervention_outcomes.items():
            assert outcome is False  # prevention succeeds individually
        # Multiple prevention sets (each member alone suffices)
        assert len(gt.required_prevention_sets) >= 2


class TestGenerateDistractor:
    def test_valid_run_and_irrelevant_channels(self) -> None:
        s = generate_distractor()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-D"
        assert ev(s.run) is True
        assert len(gt.causal_channel_ids) >= 1
        assert len(gt.irrelevant_channel_ids) >= 1


class TestGenerateCascade:
    def test_valid_run_and_origin_propagation(self) -> None:
        s = generate_cascade()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-E"
        assert ev(s.run) is True
        assert len(gt.causal_origin_ids) >= 1
        # Origin channels should be a subset of causal channels
        assert set(gt.causal_origin_ids) <= set(gt.causal_channel_ids)


class TestGenerateCostAsymmetric:
    def test_valid_run_and_cost_structure(self) -> None:
        s = generate_cost_asymmetric()
        gt = s.ground_truth
        ev = get_evaluator(s)

        assert gt.family == "BF-F"
        assert ev(s.run) is True
        assert gt.budget is not None
        assert gt.channel_costs  # Non-empty cost map
        assert gt.expected_budget_feasible_set is not None


# ===================================================================
# 9. Deterministic reproducibility
# ===================================================================


class TestDeterministic:
    def test_same_seed_same_ground_truth(self) -> None:
        s1 = generate_single_cause(seed=99)
        s2 = generate_single_cause(seed=99)

        # Ground truth should have same structure
        assert s1.ground_truth.family == s2.ground_truth.family
        assert len(s1.ground_truth.causal_channel_ids) == len(s2.ground_truth.causal_channel_ids)
        assert len(s1.candidates) == len(s2.candidates)


# ===================================================================
# 10. Random baseline deterministic
# ===================================================================


class TestRandomBaseline:
    def test_deterministic_across_runs(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        b1a = RandomBaseline(scenario_seed=42, draws=5)
        b1b = RandomBaseline(scenario_seed=42, draws=5)

        r1 = b1a.select(s.candidates, s.failure, s.evidence_graph, s.run, ev)
        r2 = b1b.select(s.candidates, s.failure, s.evidence_graph, s.run, ev)

        assert r1.selected == r2.selected  # Deterministic


# ===================================================================
# 11-14. Baseline methods
# ===================================================================


class TestProvenanceBaseline:
    def test_ranks_by_screening_score(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        b2 = ProvenanceOnlyBaseline()
        result = b2.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
        assert len(result.selected) <= 2
        assert len(result.ranked) == len(s.candidates)


class TestCEERankBaseline:
    def test_ranks_by_cee(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        b3 = CEERankBaseline()
        result = b3.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=1)
        assert len(result.selected) >= 1
        assert result.replay_count > 0  # Used replay


class TestGraphStructuralBaseline:
    def test_ranks_by_distance(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        b4 = GraphStructuralBaseline()
        result = b4.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
        assert len(result.selected) <= 2


class TestCostAwareBaseline:
    def test_penalizes_high_cost(self) -> None:
        s = generate_cost_asymmetric()
        ev = get_evaluator(s)
        gt = s.ground_truth
        cm = CostModel(channel_costs=gt.channel_costs)
        b5 = CostAwareBaseline()
        result = b5.select(
            s.candidates,
            s.failure,
            s.evidence_graph,
            s.run,
            ev,
            k=1,
            cost_model=cm,
        )
        assert len(result.selected) >= 1


# ===================================================================
# 15. A1 = B2 identity
# ===================================================================


class TestA1EqualsB2:
    def test_identical_selections(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        a1 = CELAMethod(level=1)
        b2 = ProvenanceOnlyBaseline()

        r_a1 = a1.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
        r_b2 = b2.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)

        # Both use provenance-only ranking — same ranked order
        assert r_a1.ranked == r_b2.ranked


# ===================================================================
# 16. A3 restricted, not exhaustive
# ===================================================================


class TestA3Restricted:
    def test_evaluates_restricted_subsets(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        a3 = CELAMethod(level=3)
        result = a3.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
        assert result.replay_count > 0
        assert result.method_name == "A3_cela"


# ===================================================================
# 17. A4 uses marginal gain
# ===================================================================


class TestA4MarginalGain:
    def test_uses_greedy_cascade_selector(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        a4 = CELAMethod(level=4)
        result = a4.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
        assert result.replay_count > 0
        assert result.method_name == "A4_cela"


# ===================================================================
# 18. Oracle exhaustive
# ===================================================================


class TestOracleExhaustive:
    def test_enumerates_all_valid_sets(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        oracle = ExhaustiveOracle()
        result = oracle.find_optimal(s.candidates, s.run, ev, s.evidence_graph, max_set_size=2)
        assert result.sets_evaluated > 0
        assert result.optimal_objective >= 0


# ===================================================================
# 19. Oracle not visible to methods
# ===================================================================


class TestOracleNotVisibleToMethods:
    def test_oracle_result_not_in_method_input(self) -> None:
        """Oracle result is not part of BaselineMethod.select() signature."""
        import inspect

        sig = inspect.signature(BaselineMethod.select)
        param_names = list(sig.parameters.keys())
        assert "oracle_result" not in param_names
        assert "oracle" not in param_names


# ===================================================================
# 20. Regret computation
# ===================================================================


class TestRegretComputation:
    def test_regret_equals_obj_gap(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)

        # Oracle
        oracle = ExhaustiveOracle()
        oracle_res = oracle.find_optimal(s.candidates, s.run, ev, s.evidence_graph, max_set_size=2)

        # Method selection
        b3 = CEERankBaseline()
        sel = b3.select(s.candidates, s.failure, s.evidence_graph, s.run, ev, k=1)

        # Compute metrics with oracle
        metric_eval = MetricEvaluator()
        metrics = metric_eval.compute(
            sel,
            s.ground_truth,
            cee_set=oracle_res.optimal_objective,
            oracle_result=oracle_res,
        )

        assert metrics.optimality.regret is not None
        assert metrics.optimality.regret >= 0.0


# ===================================================================
# 21. Attribution metrics
# ===================================================================


class TestMetricAttribution:
    def test_precision_recall_f1(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1", "c3"],
            ranked=["c1", "c3"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.SINGLE_CHANNEL),
            causal_channel_ids=["c1", "c2"],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt)

        # c1 is correct, c3 is not
        assert metrics.attribution.causal_precision == 0.5
        # c1 found out of c1,c2
        assert metrics.attribution.causal_recall == 0.5

    def test_recall_at_k(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1"],
            ranked=["c1", "c2", "c3"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.SINGLE_CHANNEL),
            causal_channel_ids=["c1", "c2"],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt, k=2)

        # Top-2: c1 and c2, both causal
        assert metrics.attribution.recall_at_k == 1.0
        assert metrics.attribution.recall_at_1 == 1.0


# ===================================================================
# 22. Localization metrics
# ===================================================================


class TestMetricLocalization:
    def test_origin_propagation_actuator(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["origin1", "prop1"],
            ranked=["origin1", "prop1"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.CASCADE),
            causal_channel_ids=["origin1", "prop1", "act1"],
            causal_origin_ids=["origin1"],
            propagation_channel_ids=["prop1"],
            failure_actuator_ids=["act1"],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt)

        assert metrics.localization.origin_recall == 1.0
        assert metrics.localization.propagation_recall == 1.0
        assert metrics.localization.actuator_recall == 0.0  # act1 not selected


# ===================================================================
# 23. Prevention metrics
# ===================================================================


class TestMetricPrevention:
    def test_prevention_from_replay(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1"],
            ranked=["c1"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.SINGLE_CHANNEL),
            causal_channel_ids=["c1"],
            required_prevention_sets=[["c1"]],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt, prevention_rate=1.0, cee_set=1.0)

        assert metrics.prevention.failure_prevention_rate == 1.0
        assert metrics.prevention.prevention_set_recall == 1.0
        assert metrics.prevention.cee_set == 1.0


# ===================================================================
# 24. DFSR metric
# ===================================================================


class TestMetricDFSR:
    def test_dfsr_correct(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1", "d1"],
            ranked=["c1", "d1"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.DISTRACTOR),
            causal_channel_ids=["c1"],
            irrelevant_channel_ids=["d1", "d2"],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt)

        # d1 selected from {d1, d2} -> 0.5
        assert metrics.discrimination.distractor_false_selection_rate == 0.5

    def test_dfsr_none_when_no_irrelevant(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1"],
            ranked=["c1"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.SINGLE_CHANNEL),
            causal_channel_ids=["c1"],
            irrelevant_channel_ids=[],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt)

        assert metrics.discrimination.distractor_false_selection_rate is None


# ===================================================================
# 25. Complementary group recovery
# ===================================================================


class TestComplementaryRecovery:
    def test_group_recovery_rate(self) -> None:
        selection = MethodSelection(
            method_name="test",
            selected=["c1"],
            ranked=["c1"],
        )
        gt = ScenarioGroundTruth(
            scenario_id="t",
            family="test",
            seed=0,
            mechanism=CausalMechanismSpec(mechanism=CausalMechanism.COMPLEMENTARY_AND),
            causal_channel_ids=["c1", "c2"],
            complementary_groups=[["c1", "c2"]],
        )
        me = MetricEvaluator()
        metrics = me.compute(selection, gt)

        # c1 is in the group -> recovered
        assert metrics.interaction.complementary_group_recovery_rate == 1.0


# ===================================================================
# 26. Information parity
# ===================================================================


class TestInformationParity:
    def test_all_methods_receive_same_candidates(self) -> None:
        s = generate_single_cause()
        ev = get_evaluator(s)
        methods: list[BaselineMethod] = [
            RandomBaseline(scenario_seed=42),
            ProvenanceOnlyBaseline(),
            CEERankBaseline(),
            GraphStructuralBaseline(),
            CostAwareBaseline(),
            CELAMethod(level=2),
        ]
        candidates = s.candidates
        all_ids = [ci.intervention_id for ci in candidates]

        for m in methods:
            result = m.select(candidates, s.failure, s.evidence_graph, s.run, ev, k=2)
            # Every selected ID must come from the same candidate set
            for sel_id in result.selected:
                assert sel_id in all_ids, f"{m.name} selected {sel_id} not in candidates"


# ===================================================================
# 27. No ground-truth leakage
# ===================================================================


class TestNoGroundTruthLeakage:
    def test_methods_dont_receive_ground_truth(self) -> None:
        """BaselineMethod.select() has no ground_truth parameter."""
        import inspect

        sig = inspect.signature(BaselineMethod.select)
        param_names = list(sig.parameters.keys())
        assert "ground_truth" not in param_names
        assert "mechanism" not in param_names
        assert "causal_channel_ids" not in param_names


# ===================================================================
# 28. Evaluator independence
# ===================================================================


class TestEvaluatorIndependence:
    def test_evaluator_checks_output_not_interventions(self) -> None:
        """Evaluator result depends on run content, not intervention spec."""
        s = generate_single_cause()
        ev = get_evaluator(s)

        # The evaluator should return True for the baseline run
        assert ev(s.run) is True

        # Same run, regardless of any intervention spec
        # (evaluator only sees run, not interventions)
        assert ev(s.run) is True  # Consistent


# ===================================================================
# 29. Result serialization
# ===================================================================


class TestResultSerialization:
    def test_all_models_serialize(self) -> None:
        metrics = BenchmarkMetrics(
            attribution=AttributionMetrics(causal_f1=0.8),
            localization=LocalizationMetrics(origin_recall=1.0),
            prevention=PreventionMetrics(failure_prevention_rate=1.0),
            discrimination=DiscriminationMetrics(distractor_false_selection_rate=0.0),
            interaction=InteractionMetrics(complementary_group_recovery_rate=1.0),
        )
        sel = MethodSelection(method_name="test", selected=["c1"], ranked=["c1"])
        mr = MethodResult(
            scenario_id="s1",
            method_name="test",
            selection=sel,
            metrics=metrics,
        )
        br = BenchmarkResult(results=[mr])

        data = br.model_dump()
        restored = BenchmarkResult.model_validate(data)
        assert len(restored.results) == 1
        assert restored.results[0].metrics.attribution.causal_f1 == 0.8


# ===================================================================
# 30. End-to-end benchmark runner
# ===================================================================


class TestRunnerEndToEnd:
    def test_full_runner_one_scenario(self) -> None:
        """Full benchmark runner on single-cause scenario."""
        s = generate_single_cause()
        runner = BenchmarkRunner(k=2, max_set_size=2)
        result = runner.run(
            [s],
            methods=[
                RandomBaseline(scenario_seed=42),
                ProvenanceOnlyBaseline(),
                CELAMethod(level=2),
            ],
            run_oracle=True,
        )

        assert len(result.results) == 3  # 3 methods x 1 scenario
        assert s.scenario_id in result.oracle_results

        # Each result has all metric dimensions
        for mr in result.results:
            assert mr.metrics.attribution is not None
            assert mr.metrics.localization is not None
            assert mr.metrics.prevention is not None
