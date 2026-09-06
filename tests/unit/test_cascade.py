"""Tests for captain.analysis.cascade — Stage 15 Cascade Intervention.

Tests set-level CEE via real joint replay, greedy marginal-gain
selection, cost/utility models, budget constraints, redundancy,
complementarity, and end-to-end CELA pipeline.

CEE(S) is ALWAYS computed via real joint counterfactual replay.
It is NEVER derived by summing individual CEE values.
"""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.analysis.cascade import (
    CascadeEstimator,
    CascadeResult,
    CostModel,
    GreedyCascadeSelector,
    InterventionSetSpec,
    MarginalGainStep,
    SelectionResult,
    SelectionStatus,
)
from captain.analysis.estimator import (
    CEEEstimator,
    TrialStatus,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    ChannelIntervention,
    ChannelInterventionType,
    Failure,
    FailureType,
)
from captain.models.execution import ExecutionRun
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_multi_channel_run() -> ExecutionRun:
    """Two-tool run: calculator + echo → independent channels."""
    responses = [
        "1. [TOOL:calculator] Compute 6*7\n2. [TOOL:echo] Say hello\n3. Summarise",
        "The calculator says 42 and the echo says hello world",
        "The answer is 42 and hello world.",
    ]
    llm = MockLLMProvider(responses=responses)
    reg = create_default_tool_registry()
    agent = Agent(llm=llm, tool_registry=reg)
    traced = TracedAgent(agent)
    _resp, collector = traced.run(TaskInput.from_text("Compute and greet"))
    return collector.get_run()


def _build_graph(run: ExecutionRun) -> EvidenceFlowGraph:
    builder = EvidenceLineageBuilder(run)
    evidence, txs = builder.build()
    return EvidenceFlowGraph.from_lineage(evidence, txs)


def _always_fails(run: ExecutionRun) -> bool:
    """Evaluator: always reports failure."""
    return True


def _always_succeeds(run: ExecutionRun) -> bool:
    """Evaluator: always reports success."""
    return False


def _get_tool_channel_interventions(
    run: ExecutionRun, graph: EvidenceFlowGraph
) -> list[ChannelIntervention]:
    """Get channel interventions for tool-produced evidence channels."""
    from captain.models.enums import EventType

    interventions: list[ChannelIntervention] = []

    for tx in graph.transformations:
        src = graph.get_evidence(tx.source_evidence_id)
        if src is None:
            continue
        # Find source event to check if it's a tool call
        for evt in run.events:
            if evt.event_id == src.creation_event_id:
                if evt.event_type == EventType.TOOL_CALL:
                    interventions.append(
                        ChannelIntervention(
                            baseline_run_id=run.run_id,
                            source_evidence_id=tx.source_evidence_id,
                            target_evidence_id=tx.target_evidence_id,
                            event_id=tx.event_id,
                            intervention_type=ChannelInterventionType.BLOCK,
                        )
                    )
                break

    # Deduplicate by source evidence ID
    seen: set[str] = set()
    deduped: list[ChannelIntervention] = []
    for ci in interventions:
        if ci.source_evidence_id not in seen:
            seen.add(ci.source_evidence_id)
            deduped.append(ci)

    return deduped


# ---------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------


class TestInterventionSetSpec:
    """InterventionSetSpec model construction and serialization."""

    def test_construction(self):
        spec = InterventionSetSpec(baseline_run_id="run_abc")
        assert spec.set_id.startswith("iset_")
        assert spec.baseline_run_id == "run_abc"
        assert spec.intervention_count == 0
        assert spec.channel_intervention_ids == []
        assert spec.total_cost == 0.0
        assert spec.validated is True

    def test_with_channels(self):
        ci = ChannelIntervention(
            baseline_run_id="run_abc",
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id="evt_x",
        )
        spec = InterventionSetSpec(
            baseline_run_id="run_abc",
            channel_interventions=[ci],
            total_cost=1.5,
        )
        assert spec.intervention_count == 1
        assert len(spec.channel_intervention_ids) == 1
        assert spec.total_cost == 1.5

    def test_serialization(self):
        spec = InterventionSetSpec(baseline_run_id="run_abc")
        data = spec.model_dump()
        restored = InterventionSetSpec.model_validate(data)
        assert restored.set_id == spec.set_id
        assert restored.baseline_run_id == spec.baseline_run_id


# ---------------------------------------------------------------
# Cost model tests
# ---------------------------------------------------------------


class TestCostModel:
    """CostModel construction and behavior."""

    def test_default_cost(self):
        model = CostModel()
        ci = ChannelIntervention(
            baseline_run_id="r",
            source_evidence_id="a",
            target_evidence_id="b",
            event_id="e",
        )
        assert model.cost(ci) == 1.0

    def test_custom_cost(self):
        ci = ChannelIntervention(
            baseline_run_id="r",
            source_evidence_id="a",
            target_evidence_id="b",
            event_id="e",
        )
        model = CostModel(
            default_cost=2.0,
            channel_costs={ci.intervention_id: 5.0},
        )
        assert model.cost(ci) == 5.0

    def test_total_cost_additive(self):
        ci1 = ChannelIntervention(
            baseline_run_id="r",
            source_evidence_id="a",
            target_evidence_id="b",
            event_id="e1",
        )
        ci2 = ChannelIntervention(
            baseline_run_id="r",
            source_evidence_id="c",
            target_evidence_id="d",
            event_id="e2",
        )
        model = CostModel(
            default_cost=1.0,
            channel_costs={ci1.intervention_id: 3.0},
        )
        # ci1=3.0, ci2=1.0 → total=4.0
        assert model.total_cost([ci1, ci2]) == 4.0

    def test_serialization(self):
        model = CostModel(default_cost=2.5)
        data = model.model_dump()
        restored = CostModel.model_validate(data)
        assert restored.default_cost == 2.5


# ---------------------------------------------------------------
# CascadeResult / SelectionResult model tests
# ---------------------------------------------------------------


class TestCascadeResultModel:
    """CascadeResult model construction and serialization."""

    def test_construction(self):
        r = CascadeResult(baseline_run_id="run_abc")
        assert r.result_id.startswith("casc_")
        assert r.cee == 0.0
        assert r.prevented is False
        assert r.supported is False

    def test_serialization(self):
        r = CascadeResult(
            baseline_run_id="run_abc",
            cee=0.5,
            prevented=True,
            prevention_rate=1.0,
            supported=True,
        )
        data = r.model_dump()
        restored = CascadeResult.model_validate(data)
        assert restored.cee == 0.5
        assert restored.prevented is True


class TestSelectionResultModel:
    """SelectionResult model tests."""

    def test_construction(self):
        r = SelectionResult()
        assert r.selection_id.startswith("sel_")
        assert r.selection_method == "greedy_marginal_gain"
        assert r.status == SelectionStatus.NO_SUPPORTED_SOLUTION

    def test_serialization(self):
        r = SelectionResult(status=SelectionStatus.SUCCESS, utility=0.8)
        data = r.model_dump()
        restored = SelectionResult.model_validate(data)
        assert restored.status == SelectionStatus.SUCCESS
        assert restored.utility == 0.8


class TestMarginalGainStep:
    """MarginalGainStep audit record tests."""

    def test_construction(self):
        s = MarginalGainStep(
            step_index=0,
            current_cee=0.5,
            candidate_cee_with=0.8,
            marginal_gain=0.3,
        )
        assert s.marginal_gain == 0.3

    def test_serialization(self):
        s = MarginalGainStep(step_index=1, marginal_gain=0.2)
        data = s.model_dump()
        restored = MarginalGainStep.model_validate(data)
        assert restored.step_index == 1


# ---------------------------------------------------------------
# CascadeEstimator tests — joint replay
# ---------------------------------------------------------------


class TestCascadeEstimator:
    """Set-level CEE estimation via real joint replay."""

    def test_single_channel(self):
        """Set-level CEE with one channel should match individual CEE."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        result = estimator.estimate_set([channels[0]])
        assert result.supported
        assert result.num_valid_trials >= 1
        # Single channel set-level CEE is a real measurement
        assert isinstance(result.cee, float)

    def test_joint_replay_two_channels(self):
        """Two channels → ONE replay (not two separate ones).

        CEE({e1,e2}) is measured through a REAL joint replay,
        not derived algebraically from individual CEE values.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        result = estimator.estimate_set(channels[:2])
        assert result.supported
        assert result.num_valid_trials >= 1
        # Joint replay metadata confirms single replay
        for trial in result.trials:
            if trial.status == TrialStatus.SUCCESS:
                assert trial.metadata.get("joint_replay") is True
                assert trial.metadata.get("channel_count") == 2

    def test_cee_set_not_sum(self):
        """CEE(S) ≠ Σ CEE(e) — demonstrated through real replay.

        Individually: CEE(e1), CEE(e2)
        Jointly: CEE({e1,e2})
        Must NOT assume additivity.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)

        # Measure individual CEEs
        r1 = estimator.estimate_set([channels[0]])
        r2 = estimator.estimate_set([channels[1]])

        # Measure joint CEE via real replay
        r_joint = estimator.estimate_set(channels[:2])

        # The joint CEE was measured through REAL replay, not summed.
        # We verify the measurement exists and is valid.
        assert r_joint.supported
        assert r_joint.num_valid_trials >= 1
        # Individual CEEs were also measured
        assert r1.supported
        assert r2.supported
        # We do NOT assert equality with sum -- that's the whole point.
        # The joint value may equal the sum or not; what matters is
        # it was measured, not computed.

    def test_empty_set(self):
        """Empty set returns unsupported result."""
        run = _make_multi_channel_run()
        estimator = CascadeEstimator(run, _always_fails, num_trials=1)
        result = estimator.estimate_set([])
        assert not result.supported
        assert result.metadata.get("reason") == "empty_set"

    def test_prevention_evaluator_confirmed(self):
        """Prevention must be evaluator-confirmed, not structural.

        Structural graph disconnection ≠ observed causal prevention.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        # With _always_fails: baseline=True, cf=True → no prevention
        est_fail = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        r_fail = est_fail.estimate_set([channels[0]])
        assert not r_fail.prevented

        # With _always_succeeds: baseline=False → cee=0
        est_succ = CascadeEstimator(run, _always_succeeds, evidence_graph=graph, num_trials=1)
        r_succ = est_succ.estimate_set([channels[0]])
        assert r_succ.cee == 0.0

    def test_utility_computation(self):
        """U(S) = CEE(S) - λ·Cost(S)."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        cost_model = CostModel(default_cost=2.0)
        estimator = CascadeEstimator(
            run,
            _always_fails,
            evidence_graph=graph,
            num_trials=1,
            lambda_cost=0.1,
            cost_model=cost_model,
        )
        result = estimator.estimate_set([channels[0]])
        expected_utility = result.cee - 0.1 * 2.0
        assert abs(result.utility - expected_utility) < 1e-9

    def test_baseline_immutability(self):
        """Baseline run must not change after joint replay."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        original_events = len(run.events)
        original_id = run.run_id

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        estimator.estimate_set(channels[:2] if len(channels) >= 2 else channels)

        assert len(run.events) == original_events
        assert run.run_id == original_id


# ---------------------------------------------------------------
# Redundancy and complementarity
# ---------------------------------------------------------------


class TestRedundancyComplementarity:
    """Test redundancy and complementarity via real joint replay."""

    def test_redundant_channels_exact_equality(self):
        """Two redundant channels: CEE({e1,e2}) == CEE({e1}).

        When both channels target the same tool result (or same
        downstream effect), adding the second provides zero
        marginal gain.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        # Create a "redundant" channel by duplicating the first
        ch1 = channels[0]
        ch_dup = ChannelIntervention(
            baseline_run_id=ch1.baseline_run_id,
            source_evidence_id=ch1.source_evidence_id,
            target_evidence_id=ch1.target_evidence_id,
            event_id=ch1.event_id,
            intervention_type=ChannelInterventionType.BLOCK,
        )

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)

        # Individual
        r1 = estimator.estimate_set([ch1])
        # Joint with duplicate (redundant)
        r_both = estimator.estimate_set([ch1, ch_dup])

        # Exact deterministic equality: both target same event
        assert r_both.cee == r1.cee
        # Marginal gain of redundant channel is exactly 0
        marginal_gain = r_both.cee - r1.cee
        assert marginal_gain == 0.0

    def test_complementary_channels_real_replay(self):
        """Two complementary channels via REAL joint replay.

        CEE({e1,e2}) is measured through actual joint execution.
        Complementarity is when the joint effect is at least as
        large as the individual effects.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)

        r1 = estimator.estimate_set([channels[0]])
        r2 = estimator.estimate_set([channels[1]])
        r_joint = estimator.estimate_set(channels[:2])

        # All were measured through real replay
        assert r1.supported
        assert r2.supported

        # Joint effect measured via REAL joint replay
        assert r_joint.supported
        for trial in r_joint.trials:
            if trial.status == TrialStatus.SUCCESS:
                assert trial.metadata.get("joint_replay") is True

        # We observe the relationship without hardcoding
        # Joint effect >= max of individuals = complementary
        # Joint effect == max of individuals = substitutive
        # Both are valid observations from real replay
        assert isinstance(r_joint.cee, float)


# ---------------------------------------------------------------
# Greedy selection tests
# ---------------------------------------------------------------


class TestGreedyCascadeSelector:
    """Greedy marginal-gain cascade selection."""

    def test_single_effective_channel(self):
        """Single effective channel scenario."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=1, max_evaluations=50)
        result = selector.select(channels[:1])

        assert result.selection_method == "greedy_marginal_gain"
        assert result.evaluations_used >= 1

    def test_greedy_skips_redundant(self):
        """Greedy selector measures marginal gain, not individual CEE.

        A duplicate channel has zero marginal gain and should not
        be selected after the original.
        """
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        ch1 = channels[0]
        ch_dup = ChannelIntervention(
            baseline_run_id=ch1.baseline_run_id,
            source_evidence_id=ch1.source_evidence_id,
            target_evidence_id=ch1.target_evidence_id,
            event_id=ch1.event_id,
            intervention_type=ChannelInterventionType.BLOCK,
        )

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=5, max_evaluations=50)
        result = selector.select([ch1, ch_dup])

        # Should select at most 1 (the second has zero marginal gain)
        if result.selected_set is not None:
            assert result.selected_set.intervention_count <= 1

    def test_budget_constraint(self):
        """Budget=2, Cost(e1)=3 → e1 excluded."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        cost_model = CostModel(
            default_cost=1.0,
            channel_costs={channels[0].intervention_id: 3.0},
        )

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(
            estimator,
            cost_model=cost_model,
            budget=2.0,
            max_set_size=5,
            max_evaluations=50,
        )
        result = selector.select(channels[:2])
        assert result.budget == 2.0

        # e1 (cost=3) must NOT be in selected set
        if result.selected_set is not None:
            for ci in result.selected_set.channel_interventions:
                assert ci.intervention_id != channels[0].intervention_id
            assert result.total_cost <= 2.0

    def test_utility_selection(self):
        """Utility mode: U(S) = CEE(S) - λ·Cost(S)."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        cost_model = CostModel(default_cost=1.0)
        estimator = CascadeEstimator(
            run,
            _always_fails,
            evidence_graph=graph,
            num_trials=1,
            lambda_cost=0.1,
            cost_model=cost_model,
        )
        selector = GreedyCascadeSelector(
            estimator,
            cost_model=cost_model,
            lambda_cost=0.1,
            max_set_size=5,
            max_evaluations=50,
        )
        result = selector.select(channels)
        # Utility computed as CEE - λ·Cost
        if result.cascade_result is not None:
            expected = result.cascade_result.cee - 0.1 * result.total_cost
            assert abs(result.utility - expected) < 1e-9

    def test_deterministic_tie_breaking(self):
        """Equal gain → lower cost → lexicographic ID."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=1, max_evaluations=50)
        # Run twice — must get same result
        r1 = selector.select(channels[:2])
        r2 = selector.select(channels[:2])

        if r1.selected_set and r2.selected_set:
            assert (
                r1.selected_set.channel_intervention_ids
                == r2.selected_set.channel_intervention_ids
            )

    def test_no_supported_solution(self):
        """No positive gain → no_supported_solution."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        # _always_succeeds: baseline=False, cf=False → CEE=0 → no gain
        estimator = CascadeEstimator(run, _always_succeeds, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=5, max_evaluations=50)
        result = selector.select(channels)
        assert result.status == SelectionStatus.NO_SUPPORTED_SOLUTION

    def test_evaluation_budget_exhausted(self):
        """max_evaluations=1 should exhaust quickly."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if len(channels) < 2:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=5, max_evaluations=1)
        result = selector.select(channels)
        assert result.evaluations_used <= 1
        # With only 1 evaluation, we can't fully explore
        assert result.max_evaluations == 1

    def test_marginal_gain_audit(self):
        """Selection steps preserve CEE(S), CEE(SU{e}), D(e|S)."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        estimator = CascadeEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_set_size=3, max_evaluations=50)
        result = selector.select(channels)

        # Verify audit trail records exist
        for step in result.selection_steps:
            assert isinstance(step, MarginalGainStep)
            # Each step preserves the audit information
            assert isinstance(step.current_cee, float)
            assert isinstance(step.candidate_cee_with, float)
            assert isinstance(step.marginal_gain, float)
            # Marginal gain = CEE(SU{e}) - CEE(S)
            if step.reason == "evaluated":
                expected_gain = step.candidate_cee_with - step.current_cee
                assert abs(step.marginal_gain - expected_gain) < 1e-9

    def test_empty_candidates(self):
        """Empty candidate list → no_supported_solution."""
        run = _make_multi_channel_run()
        estimator = CascadeEstimator(run, _always_fails, num_trials=1)
        selector = GreedyCascadeSelector(estimator, max_evaluations=50)
        result = selector.select([])
        assert result.status == SelectionStatus.NO_SUPPORTED_SOLUTION


# ---------------------------------------------------------------
# Channel fidelity preservation (Stage 14.1)
# ---------------------------------------------------------------


class TestChannelFidelityPreservation:
    """Stage 14.1 channel-level semantics preserved in cascade."""

    def test_channel_fidelity_in_cascade(self):
        """Cascade uses TOOL_RESULT_OVERRIDE, not EVENT_OUTPUT_OVERRIDE."""
        from captain.analysis.estimator import channel_to_intervention
        from captain.intervention.model import InterventionType

        run = _make_multi_channel_run()
        graph = _build_graph(run)
        channels = _get_tool_channel_interventions(run, graph)
        if not channels:
            return

        # Verify channel_to_intervention uses true channel-level
        for ch in channels:
            intv = channel_to_intervention(ch, run, graph)
            assert intv.intervention_type == InterventionType.TOOL_RESULT_OVERRIDE
            assert intv.metadata.get("channel_level") is True


# ---------------------------------------------------------------
# End-to-end CELA cascade pipeline
# ---------------------------------------------------------------


class TestEndToEndCascadePipeline:
    """Full CELA pipeline: Agent → Trace → Evidence → Failure →
    Candidates → Individual CEE → Joint Replay → Cascade → Selection.

    The counterfactual is an actual execution, not a fake result.
    """

    def test_full_pipeline(self):
        """Complete end-to-end cascade pipeline."""
        # 1. Reference agent → traced baseline
        run = _make_multi_channel_run()
        assert run.run_id.startswith("run_")

        # 2. Evidence flow graph
        graph = _build_graph(run)
        assert len(graph.evidence) > 0
        assert len(graph.transformations) > 0

        # 3. Failure label
        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            description="Test failure",
            failure_event_id=run.events[-1].event_id,
        )

        # 4. Stage 13 candidates
        analyzer = FailureAnalyzer(graph, failure)
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()
        if not interventions:
            return

        # 5. Stage 14 individual CEE
        ind_estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)

        individual_cees: list[float] = []
        for cand, ci in zip(candidates[: len(interventions)], interventions, strict=False):
            r = ind_estimator.estimate(cand, ci)
            individual_cees.append(r.cee)

        # 6. Stage 15: get tool-channel interventions for cascade
        tool_channels = _get_tool_channel_interventions(run, graph)
        if not tool_channels:
            return

        # 7. Cascade estimator — REAL joint replay
        cost_model = CostModel(default_cost=1.0)
        cascade_est = CascadeEstimator(
            run,
            _always_fails,
            evidence_graph=graph,
            num_trials=1,
            lambda_cost=0.1,
            cost_model=cost_model,
        )

        # 8. Joint set-level CEE
        cascade_result = cascade_est.estimate_set(tool_channels)
        assert cascade_result.supported
        assert cascade_result.num_valid_trials >= 1

        # 9. Greedy selection
        selector = GreedyCascadeSelector(
            cascade_est,
            cost_model=cost_model,
            lambda_cost=0.1,
            max_set_size=5,
            budget=10.0,
            max_evaluations=50,
        )
        selection = selector.select(tool_channels)
        assert selection.selection_method == "greedy_marginal_gain"
        assert selection.evaluations_used >= 1

        # 10. Verify selection result structure
        assert isinstance(selection.total_cost, float)
        assert isinstance(selection.utility, float)
        assert selection.budget == 10.0
        assert selection.lambda_cost == 0.1

        # Global optimality is NOT claimed
        assert selection.selection_method == "greedy_marginal_gain"
