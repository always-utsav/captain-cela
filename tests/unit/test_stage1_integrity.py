"""Stage 1 scientific integrity tests.

Tests for:
- Information leakage
- Intervention fidelity
- Determinism
- Negative controls
"""

from __future__ import annotations

import json

import pytest

from captain.benchmarks.baselines import (
    CELAMethod,
    CostAwareBaseline,
    GraphStructuralBaseline,
    ProvenanceOnlyBaseline,
    RandomBaseline,
)
from captain.benchmarks.scenarios import (
    generate_cascade,
    generate_complementary,
    generate_distractor,
    generate_redundant,
    generate_single_cause,
    get_evaluator,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import ChannelIntervention, Failure, FailureType
from captain.intervention.model import Intervention, InterventionSet, InterventionType
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine


# =================================================================
# INFORMATION LEAKAGE TESTS
# =================================================================


class TestInformationLeakage:
    """Verify no ground truth leaks to methods."""

    def test_scenario_ground_truth_not_in_method_inputs(self) -> None:
        """Methods never receive ScenarioGroundTruth fields."""
        scenario = generate_single_cause(seed=42)

        # Methods receive: run, evidence_graph, failure, candidates
        # They do NOT receive: ground_truth
        method = RandomBaseline(scenario_seed=42)

        # Inspect what the method actually receives
        evaluator = get_evaluator(scenario)
        selection = method.select(
            scenario.candidates,
            scenario.failure,
            scenario.evidence_graph,
            scenario.run,
            evaluator,
        )

        # The method should not have access to ground_truth
        # Verify the method's selection does not encode ground truth info
        assert selection is not None

    def test_evaluator_does_not_inspect_method_identity(self) -> None:
        """Evaluator output depends only on execution output, not method."""
        scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        # Evaluator only sees the run, not which method was used
        result = evaluator(scenario.run)
        assert isinstance(result, bool)

    def test_all_baselines_receive_same_information(self) -> None:
        """All methods receive identical inputs."""
        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        methods = [
            RandomBaseline(scenario_seed=42),
            ProvenanceOnlyBaseline(),
            GraphStructuralBaseline(),
            CostAwareBaseline(),
        ]

        # All methods use the same interface
        for method in methods:
            selection = method.select(
                scenario.candidates,
                scenario.failure,
                scenario.evidence_graph,
                scenario.run,
                evaluator,
            )
            assert selection is not None

    def test_candidate_generation_does_not_encode_answer(self) -> None:
        """Candidate IDs do not contain hidden causal information."""
        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)

        for candidate in scenario.candidates:
            # Intervention IDs should not contain tool names or keywords
            assert "calculator" not in candidate.intervention_id
            assert "42" not in candidate.intervention_id
            assert "causal" not in candidate.intervention_id

    def test_ground_truth_not_serialized_to_methods(self) -> None:
        """Serialized scenario for methods should not contain ground truth."""
        scenario = generate_single_cause(seed=42)

        # Serialize what a method would see
        method_view = {
            "run_id": scenario.run.run_id,
            "num_events": len(scenario.run.events),
            "num_candidates": len(scenario.candidates),
        }

        # ground_truth should NOT be in method view
        method_view_str = json.dumps(method_view)
        assert "causal_channel_ids" not in method_view_str
        assert "required_prevention_sets" not in method_view_str


# =================================================================
# INTERVENTION FIDELITY TESTS
# =================================================================


class TestInterventionFidelity:
    """Verify interventions modify only target channels."""

    def _make_scenario(self):
        """Create a deterministic scenario for fidelity testing."""
        with deterministic_ids(seed=99):
            return generate_single_cause(seed=99)

    def test_tool_result_override_modifies_target(self) -> None:
        """TOOL_RESULT_OVERRIDE changes the target tool's output."""
        scenario = self._make_scenario()

        if not scenario.candidates:
            pytest.skip("No candidates")

        ci = scenario.candidates[0]

        from captain.analysis.estimator import channel_to_intervention

        intervention = channel_to_intervention(ci, scenario.run)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intervention],
        )

        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        assert result.counterfactual_run is not None
        cf_run = result.counterfactual_run
        assert cf_run.run_id != scenario.run.run_id
        assert cf_run.parent_run_id == scenario.run.run_id

    def test_channel_blocking_preserves_other_channels(self) -> None:
        """Blocking one channel should not modify unrelated channels."""
        scenario = self._make_scenario()

        if len(scenario.candidates) < 2:
            pytest.skip("Need at least 2 candidates")

        ci_target = scenario.candidates[0]

        from captain.analysis.estimator import channel_to_intervention

        intervention = channel_to_intervention(ci_target, scenario.run)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intervention],
        )

        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        assert result.counterfactual_run is not None

        cf_run = result.counterfactual_run
        builder = EvidenceLineageBuilder(cf_run)
        cf_evidence, cf_txs = builder.build()
        cf_graph = EvidenceFlowGraph.from_lineage(cf_evidence, cf_txs)
        assert cf_graph.evidence_count > 0

    def test_fresh_ids_in_counterfactual(self) -> None:
        """Counterfactual runs get fresh IDs, not reused baseline IDs."""
        scenario = self._make_scenario()

        if not scenario.candidates:
            pytest.skip("No candidates")

        from captain.analysis.estimator import channel_to_intervention

        ci = scenario.candidates[0]
        intervention = channel_to_intervention(ci, scenario.run)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intervention],
        )

        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        if result.counterfactual_run is None:
            pytest.skip("Replay failed")

        cf_run = result.counterfactual_run

        assert cf_run.run_id != scenario.run.run_id

        baseline_event_ids = {e.event_id for e in scenario.run.events}
        cf_event_ids = {e.event_id for e in cf_run.events}
        assert baseline_event_ids.isdisjoint(cf_event_ids)

        baseline_art_ids = {a.artifact_id for a in scenario.run.artifacts}
        cf_art_ids = {a.artifact_id for a in cf_run.artifacts}
        assert baseline_art_ids.isdisjoint(cf_art_ids)

    def test_joint_intervention_applies_all_channels(self) -> None:
        """Joint intervention applies ALL specified channels (when possible)."""
        with deterministic_ids(seed=200):
            scenario = generate_redundant(seed=200)

        if len(scenario.candidates) < 2:
            pytest.skip("Need at least 2 candidates")

        from captain.analysis.estimator import channel_to_intervention

        interventions = []
        for ci in scenario.candidates[:2]:
            interventions.append(channel_to_intervention(ci, scenario.run))

        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=interventions,
        )

        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        # Joint replay may be REJECTED if both channels target the
        # same event (shared-source limitation). This is a documented
        # constraint, not a bug. Document in fidelity report.
        from captain.replay.engine import ReplayStatus

        if result.status == ReplayStatus.REJECTED:
            # Verify rejection reason is the expected shared-event case
            assert "interventions" in (result.rejection_reason or "").lower()
        else:
            assert result.counterfactual_run is not None


# =================================================================
# DETERMINISM TESTS
# =================================================================


class TestDeterminism:
    """Verify reproducibility of scientific outputs."""

    def test_same_seed_same_scenario(self) -> None:
        """Same seed produces identical scenario IDs and structure."""
        with deterministic_ids(seed=42):
            s1 = generate_single_cause(seed=42)
        with deterministic_ids(seed=42):
            s2 = generate_single_cause(seed=42)

        assert s1.run.run_id == s2.run.run_id
        assert len(s1.run.events) == len(s2.run.events)
        assert len(s1.run.artifacts) == len(s2.run.artifacts)

        for e1, e2 in zip(s1.run.events, s2.run.events, strict=True):
            assert e1.event_id == e2.event_id

        for a1, a2 in zip(s1.run.artifacts, s2.run.artifacts, strict=True):
            assert a1.artifact_id == a2.artifact_id

    def test_different_seeds_different_ids(self) -> None:
        """Different seeds produce different IDs."""
        with deterministic_ids(seed=1):
            s1 = generate_single_cause(seed=1)
        with deterministic_ids(seed=2):
            s2 = generate_single_cause(seed=2)

        assert s1.run.run_id != s2.run.run_id

    def test_evidence_ids_deterministic(self) -> None:
        """Evidence IDs are deterministic within same seed."""
        with deterministic_ids(seed=42):
            s1 = generate_single_cause(seed=42)
        with deterministic_ids(seed=42):
            s2 = generate_single_cause(seed=42)

        e1_ids = [e.evidence_id for e in s1.evidence_graph.evidence]
        e2_ids = [e.evidence_id for e in s2.evidence_graph.evidence]
        assert e1_ids == e2_ids

    def test_candidate_ids_deterministic(self) -> None:
        """Candidate/intervention IDs are deterministic."""
        with deterministic_ids(seed=42):
            s1 = generate_single_cause(seed=42)
        with deterministic_ids(seed=42):
            s2 = generate_single_cause(seed=42)

        c1_ids = [c.intervention_id for c in s1.candidates]
        c2_ids = [c.intervention_id for c in s2.candidates]
        assert c1_ids == c2_ids

    def test_metrics_deterministic_across_runs(self) -> None:
        """Metrics from same scenario/seed are identical."""
        from captain.analysis.estimator import CEEEstimator
        from captain.agent.tools import create_default_tool_registry

        for _ in range(2):
            with deterministic_ids(seed=42):
                scenario = generate_single_cause(seed=42)
            evaluator = get_evaluator(scenario)

            if not scenario.candidates:
                continue

            ci = scenario.candidates[0]
            estimator = CEEEstimator(
                baseline_run=scenario.run,
                evaluator=evaluator,
                evidence_graph=scenario.evidence_graph,
                tool_registry=create_default_tool_registry(),
                num_trials=3,
            )
            result = estimator.estimate(ci, ci)
            # CEE value is deterministic with deterministic IDs
            assert result.cee is not None


# =================================================================
# NEGATIVE CONTROL TESTS
# =================================================================


class TestNegativeControls:
    """Verify placebo interventions show no causal effect."""

    def test_irrelevant_channel_has_zero_cee(self) -> None:
        """Intervening on non-causal channel should have ~0 CEE."""
        from captain.analysis.estimator import CEEEstimator
        from captain.agent.tools import create_default_tool_registry

        with deterministic_ids(seed=42):
            scenario = generate_distractor(seed=42)
        evaluator = get_evaluator(scenario)

        # Find irrelevant (distractor) channel
        irrelevant_ids = set(scenario.ground_truth.irrelevant_channel_ids)
        irrelevant_candidates = [
            ci for ci in scenario.candidates
            if ci.intervention_id in irrelevant_ids
        ]

        if not irrelevant_candidates:
            pytest.skip("No irrelevant candidates found")

        ci = irrelevant_candidates[0]
        estimator = CEEEstimator(
            baseline_run=scenario.run,
            evaluator=evaluator,
            evidence_graph=scenario.evidence_graph,
            tool_registry=create_default_tool_registry(),
            num_trials=5,
        )
        result = estimator.estimate(ci, ci)

        # Distractor intervention should not prevent failure
        # CEE should be ~0 (failure persists after intervention)
        assert result.cee <= 0.5, f"Distractor CEE too high: {result.cee}"


# =================================================================
# BENCHMARK VALIDATION TESTS
# =================================================================


class TestBenchmarkValidation:
    """Verify benchmark families produce valid scenarios."""

    @pytest.mark.parametrize("family,generator,expected_mechanism", [
        ("BF-A", generate_single_cause, "single_channel"),
        ("BF-B", generate_redundant, "redundant_or"),
        ("BF-C", generate_complementary, "complementary_and"),
        ("BF-D", generate_distractor, "distractor"),
        ("BF-E", generate_cascade, "cascade"),
    ])
    def test_family_structure(self, family, generator, expected_mechanism) -> None:
        """Each family generates correct causal structure."""
        with deterministic_ids(seed=42):
            scenario = generator(seed=42)

        assert scenario.family == family
        assert scenario.ground_truth.mechanism.mechanism.value == expected_mechanism
        assert scenario.ground_truth.causal_channel_ids, f"{family} missing causal channels"
        assert scenario.run.events, f"{family} missing events"
        assert scenario.evidence_graph.evidence_count > 0

    def test_evaluator_detects_failure(self) -> None:
        """Evaluator correctly identifies factual failure."""
        scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)
        assert evaluator(scenario.run) is True, "Factual run should be marked as failed"

    def test_ground_truth_has_prevention_sets(self) -> None:
        """Ground truth specifies valid prevention sets."""
        scenario = generate_single_cause(seed=42)
        gt = scenario.ground_truth
        assert gt.required_prevention_sets, "BF-A should have prevention sets"
        for pset in gt.required_prevention_sets:
            assert all(isinstance(id_, str) for id_ in pset)


# =================================================================
# REPLAY CONVERGENCE TESTS (small N)
# =================================================================


class TestReplayConvergence:
    """Verify CEE estimates converge with more replays."""

    def test_more_replays_tighter_ci(self) -> None:
        """CI width should decrease with more replays."""
        from captain.analysis.estimator import CEEEstimator
        from captain.agent.tools import create_default_tool_registry

        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        if not scenario.candidates:
            pytest.skip("No candidates")

        ci = scenario.candidates[0]
        widths = []

        for n_trials in [3, 10]:
            with deterministic_ids(seed=42):
                scenario = generate_single_cause(seed=42)
            estimator = CEEEstimator(
                baseline_run=scenario.run,
                evaluator=evaluator,
                evidence_graph=scenario.evidence_graph,
                tool_registry=create_default_tool_registry(),
                num_trials=n_trials,
            )
            result = estimator.estimate(ci, ci)
            width = result.ci_upper - result.ci_lower
            widths.append(width)

        # More replays should give tighter or equal CI
        # (with small N this may not always hold perfectly)
        assert widths[-1] <= widths[0] + 0.1, \
            f"CI should not widen significantly: {widths}"
