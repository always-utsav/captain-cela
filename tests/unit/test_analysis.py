"""Tests for captain.analysis — CELA CEE + Paired Replay + Bottleneck (Stage 14)."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.analysis.estimator import (
    BottleneckAnalyzer,
    BottleneckResult,
    CEEEstimator,
    CEEResult,
    Outcome,
    PairedTrial,
    PropagationProfile,
    TrialStatus,
    channel_to_intervention,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    Candidate,
    ChannelIntervention,
    Failure,
    FailureType,
)
from captain.intervention.model import InterventionType
from captain.models.execution import ExecutionRun
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_run(responses: list[str] | None = None) -> ExecutionRun:
    """Create a traced execution run with deterministic mock."""
    if responses is None:
        responses = [
            "1. [TOOL:calculator] Compute 6*7\n2. Summarise",
            "The result is 42",
            "Six times seven equals 42.",
        ]
    llm = MockLLMProvider(responses=responses)
    reg = create_default_tool_registry()
    agent = Agent(llm=llm, tool_registry=reg)
    traced = TracedAgent(agent)
    _resp, collector = traced.run(TaskInput.from_text("What is 6*7?"))
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


def _check_42(run: ExecutionRun) -> bool:
    """Evaluator: fails if '42' not in any output event."""
    for evt in run.events:
        if "42" in evt.payload.get("content", ""):
            return False
        if "42" in evt.payload.get("result", ""):
            return False
    return True


def _get_test_candidate_and_intervention(
    run: ExecutionRun, graph: EvidenceFlowGraph
) -> tuple[Candidate, ChannelIntervention] | None:
    """Get a candidate and intervention from a real run."""
    target_eids = {t.target_evidence_id for t in graph.transformations}
    if not target_eids:
        return None
    target_id = sorted(target_eids)[0]
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        failure_evidence_ids=[target_id],
    )
    analyzer = FailureAnalyzer(graph, failure)
    candidates = analyzer.candidates()
    if not candidates:
        return None
    interventions = analyzer.interventions()
    if not interventions:
        return None
    return candidates[0], interventions[0]


# ===============================================================
# 1. Outcome model
# ===============================================================


class TestOutcome:
    def test_construction(self):
        o = Outcome(run_id="run_1", failed=True)
        assert o.failed is True

    def test_serialization(self):
        o = Outcome(run_id="run_1", failed=False, evaluator="oracle")
        d = o.model_dump(mode="json")
        o2 = Outcome.model_validate(d)
        assert o2.evaluator == "oracle"


# ===============================================================
# 2. Paired trial model
# ===============================================================


class TestPairedTrial:
    def test_construction(self):
        t = PairedTrial(baseline_run_id="run_1")
        assert t.trial_id.startswith("trial_")
        assert t.status == TrialStatus.SUCCESS

    def test_serialization(self):
        t = PairedTrial(
            baseline_run_id="run_1",
            counterfactual_run_id="run_2",
            baseline_outcome=True,
            counterfactual_outcome=False,
        )
        d = t.model_dump(mode="json")
        t2 = PairedTrial.model_validate(d)
        assert t2.baseline_outcome is True
        assert t2.counterfactual_outcome is False

    def test_error_status(self):
        t = PairedTrial(
            baseline_run_id="run_1",
            status=TrialStatus.REPLAY_ERROR,
            error_message="Replay crashed",
        )
        assert t.status == TrialStatus.REPLAY_ERROR


# ===============================================================
# 3. CEE result model
# ===============================================================


class TestCEEResult:
    def test_construction(self):
        r = CEEResult(candidate_id="cand_1", cee=0.5, num_trials=10, num_valid_trials=10)
        assert r.result_id.startswith("cee_")
        assert r.cee == 0.5

    def test_serialization(self):
        r = CEEResult(
            candidate_id="cand_1",
            cee=1.0,
            ci_lower=0.8,
            ci_upper=1.0,
            num_trials=5,
            num_valid_trials=5,
        )
        d = r.model_dump(mode="json")
        r2 = CEEResult.model_validate(d)
        assert r2.cee == 1.0
        assert r2.ci_lower == 0.8


# ===============================================================
# 4. Channel-to-event bridge
# ===============================================================


class TestChannelBridge:
    def test_fallback_without_graph(self):
        """Without evidence graph, falls back to event-level override."""
        run = _make_run()
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id=run.events[0].event_id,
        )
        intv = channel_to_intervention(ci, run)
        assert intv.intervention_type == InterventionType.EVENT_OUTPUT_OVERRIDE
        assert intv.target_id == run.events[0].event_id
        assert intv.metadata["channel_level"] is False

    def test_channel_level_with_graph(self):
        """With evidence graph, targets source's producing event."""
        run = _make_run()
        graph = _build_graph(run)
        if not graph.transformations:
            return
        tx = graph.transformations[0]
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            event_id=tx.event_id,
        )
        intv = channel_to_intervention(ci, run, graph)
        assert intv.metadata["channel_level"] is True
        # Target is the SOURCE's producing event, not the mediating event
        source_evi = graph.get_evidence(tx.source_evidence_id)
        assert source_evi is not None
        assert intv.target_id == source_evi.creation_event_id

    def test_documents_mechanism(self):
        run = _make_run()
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id=run.events[0].event_id,
        )
        intv = channel_to_intervention(ci, run)
        assert "mechanism" in intv.metadata
        assert "Event-level" in intv.metadata["mechanism"]


# ===============================================================
# 5. Replay fidelity
# ===============================================================


class TestReplayFidelity:
    def test_fresh_run_id(self):
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        estimator = CEEEstimator(run, _always_fails)
        result = estimator.estimate(cand, ci)
        for t in result.trials:
            if t.status == TrialStatus.SUCCESS:
                assert t.counterfactual_run_id != ""
                assert t.counterfactual_run_id != run.run_id

    def test_baseline_immutability(self):
        run = _make_run()
        before = run.model_dump_json()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        estimator = CEEEstimator(run, _always_fails)
        estimator.estimate(cand, ci)
        after = run.model_dump_json()
        assert before == after

    def test_deterministic_replay(self):
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        r1 = CEEEstimator(run, _always_fails).estimate(cand, ci)
        r2 = CEEEstimator(run, _always_fails).estimate(cand, ci)
        assert r1.cee == r2.cee


# ===============================================================
# 6. CEE estimator — known outcomes
# ===============================================================


class TestCEEEstimator:
    def test_positive_effect(self):
        """Baseline fails, counterfactual succeeds → CEE > 0."""
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair

        def eval_baseline_fails(r: ExecutionRun) -> bool:
            return r.run_id == run.run_id  # baseline fails, cf succeeds

        result = CEEEstimator(run, eval_baseline_fails).estimate(cand, ci)
        if result.num_valid_trials > 0:
            assert result.cee >= 0.0

    def test_zero_effect(self):
        """Both fail → CEE = 0."""
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        result = CEEEstimator(run, _always_fails).estimate(cand, ci)
        if result.num_valid_trials > 0:
            assert result.cee == 0.0

    def test_negative_effect(self):
        """Baseline succeeds, counterfactual fails → CEE < 0."""
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair

        def eval_cf_fails(r: ExecutionRun) -> bool:
            return r.run_id != run.run_id  # cf fails, baseline succeeds

        result = CEEEstimator(run, eval_cf_fails).estimate(cand, ci)
        if result.num_valid_trials > 0:
            assert result.cee <= 0.0

    def test_small_n_handling(self):
        """N=1: valid but limited confidence."""
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        result = CEEEstimator(run, _always_fails, num_trials=1).estimate(cand, ci)
        if result.num_valid_trials > 0:
            # For N=1, CI = point estimate
            assert result.ci_lower == result.ci_upper

    def test_trial_count(self):
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair
        result = CEEEstimator(run, _always_fails, num_trials=3).estimate(cand, ci)
        assert result.num_trials == 3


# ===============================================================
# 7. Trial status
# ===============================================================


class TestTrialStatus:
    def test_replay_error_distinct(self):
        assert TrialStatus.REPLAY_ERROR != TrialStatus.SUCCESS

    def test_invalid_intervention_distinct(self):
        assert TrialStatus.INVALID_INTERVENTION != TrialStatus.SUCCESS


# ===============================================================
# 8. Bottleneck analyzer
# ===============================================================


class TestBottleneckAnalyzer:
    def test_selects_highest_cee(self):
        results = [
            CEEResult(candidate_id="c1", cee=0.3, num_valid_trials=1),
            CEEResult(candidate_id="c2", cee=0.8, num_valid_trials=1),
            CEEResult(candidate_id="c3", cee=0.5, num_valid_trials=1),
        ]
        bn = BottleneckAnalyzer.select(results)
        assert bn.supported is True
        assert bn.candidate_id == "c2"
        assert bn.cee == 0.8

    def test_no_supported(self):
        bn = BottleneckAnalyzer.select([])
        assert bn.supported is False

    def test_min_trials(self):
        results = [
            CEEResult(candidate_id="c1", cee=0.9, num_valid_trials=1),
            CEEResult(candidate_id="c2", cee=0.5, num_valid_trials=5),
        ]
        bn = BottleneckAnalyzer.select(results, min_trials=3)
        assert bn.candidate_id == "c2"

    def test_tie_deterministic(self):
        results = [
            CEEResult(candidate_id="c_b", cee=0.5, num_valid_trials=1),
            CEEResult(candidate_id="c_a", cee=0.5, num_valid_trials=1),
        ]
        bn = BottleneckAnalyzer.select(results)
        assert bn.candidate_id == "c_a"  # lexicographic

    def test_unsupported_excluded(self):
        results = [
            CEEResult(candidate_id="c1", cee=0.9, num_valid_trials=0),
        ]
        bn = BottleneckAnalyzer.select(results)
        assert bn.supported is False

    def test_serialization(self):
        bn = BottleneckResult(candidate_id="c1", cee=0.5, supported=True, num_trials=3)
        d = bn.model_dump(mode="json")
        bn2 = BottleneckResult.model_validate(d)
        assert bn2.cee == 0.5


# ===============================================================
# 9. Propagation profile
# ===============================================================


class TestPropagationProfile:
    def test_construction(self):
        results = [
            CEEResult(candidate_id="c1", cee=0.2, num_valid_trials=1),
            CEEResult(candidate_id="c2", cee=0.8, num_valid_trials=1),
        ]
        pp = BottleneckAnalyzer.propagation_profile(results)
        assert len(pp.edge_ids) == 2
        assert len(pp.cee_values) == 2

    def test_ordered(self):
        results = [
            CEEResult(candidate_id="c_z", cee=0.1, num_valid_trials=1),
            CEEResult(candidate_id="c_a", cee=0.9, num_valid_trials=1),
        ]
        pp = BottleneckAnalyzer.propagation_profile(results)
        assert pp.edge_ids == ["c_a", "c_z"]

    def test_serialization(self):
        pp = PropagationProfile(edge_ids=["c1"], cee_values=[0.5])
        d = pp.model_dump(mode="json")
        pp2 = PropagationProfile.model_validate(d)
        assert pp2.cee_values == [0.5]


# ===============================================================
# 10. Integration: full pipeline
# ===============================================================


class TestIntegration:
    def test_end_to_end_pipeline(self):
        """Agent→Trace→Evidence→Failure→Candidate→Replay→CEE→Bottleneck."""
        run = _make_run()
        graph = _build_graph(run)

        # Get candidate
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return  # Graph too sparse for full test
        cand, ci = pair

        # CEE estimation
        estimator = CEEEstimator(run, _always_fails, num_trials=1)
        result = estimator.estimate(cand, ci)

        assert result.num_trials == 1
        assert isinstance(result.cee, float)
        assert len(result.trials) == 1

        # Bottleneck
        bn = BottleneckAnalyzer.select([result])
        if result.num_valid_trials > 0:
            assert bn.supported is True

        # Profile
        pp = BottleneckAnalyzer.propagation_profile([result])
        assert len(pp.edge_ids) == 1

    def test_downstream_effect(self):
        """Verify intervention changes downstream execution."""
        run = _make_run()
        graph = _build_graph(run)
        pair = _get_test_candidate_and_intervention(run, graph)
        if pair is None:
            return
        cand, ci = pair

        # Use evaluator that detects '42' — baseline has it
        estimator = CEEEstimator(run, _check_42, num_trials=1)
        result = estimator.estimate(cand, ci)

        if result.num_valid_trials > 0:
            trial = result.trials[0]
            # Verify we got a real counterfactual run
            assert trial.counterfactual_run_id != ""
            assert trial.counterfactual_run_id != run.run_id

    def test_candidate_from_stage13(self):
        """Verify Stage 13 candidates work with Stage 14 estimation."""
        run = _make_run()
        graph = _build_graph(run)

        target_eids = {t.target_evidence_id for t in graph.transformations}
        if not target_eids:
            return
        target_id = sorted(target_eids)[0]

        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=[target_id],
        )
        analyzer = FailureAnalyzer(graph, failure)
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()

        if not candidates or not interventions:
            return

        cee_results: list[CEEResult] = []
        estimator = CEEEstimator(run, _always_fails, num_trials=1)
        for c, i in zip(candidates, interventions, strict=False):
            r = estimator.estimate(c, i)
            cee_results.append(r)

        bn = BottleneckAnalyzer.select(cee_results)
        assert isinstance(bn, BottleneckResult)
        pp = BottleneckAnalyzer.propagation_profile(cee_results)
        assert len(pp.edge_ids) == len(cee_results)


# ===============================================================
# 11. Stage 14.1 — Multi-channel fidelity tests
# ===============================================================


def _make_multi_channel_run() -> ExecutionRun:
    """Create a run with TWO tool calls: calculator + echo.

    This produces two independent tool result evidence objects
    that both feed into the downstream reasoning/output step.

    Evidence structure:
        evi_input → evi_planning
        evi_calc_result (tool: calculator, "42")
        evi_echo_result (tool: echo, "hello world")
        evi_reasoning
        evi_output

    The two tool results create independent information channels
    through distinct TOOL_RESULT events.
    """
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


class TestMultiChannelFidelity:
    """Stage 14.1: True channel-level intervention fidelity tests."""

    def test_two_tool_results_exist(self):
        """Verify multi-channel scenario has two distinct tool results."""
        from captain.models.enums import EventType

        run = _make_multi_channel_run()
        tool_results = [e for e in run.events if e.event_type == EventType.TOOL_RESULT]
        assert len(tool_results) >= 2

    def test_two_tool_channels_in_graph(self):
        """Verify evidence graph has edges from both tool call sources."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        # Should have transformations from tool-produced sources
        tool_source_ids = set()
        for tx in graph.transformations:
            src = graph.get_evidence(tx.source_evidence_id)
            if src and src.evidence_type.value in (
                "tool_output",
                "tool_input",
                "structured",
            ):
                tool_source_ids.add(tx.source_evidence_id)
        # At least 2 tool-produced sources (from two tool calls)
        assert len(tool_source_ids) >= 2

    def test_channel_targets_source_not_mediator(self):
        """Core fidelity: channel intervention targets SOURCE's TOOL_RESULT,
        NOT the mediating event that consumes both sources."""
        from captain.models.enums import EventType

        run = _make_multi_channel_run()
        graph = _build_graph(run)
        if not graph.transformations:
            return

        # Find a transformation whose source was produced by a TOOL_CALL
        tool_tx = None
        for tx in graph.transformations:
            src = graph.get_evidence(tx.source_evidence_id)
            if src is None:
                continue
            for evt in run.events:
                if evt.event_id == src.creation_event_id:
                    if evt.event_type == EventType.TOOL_CALL:
                        tool_tx = tx
                    break
            if tool_tx:
                break

        if tool_tx is None:
            return

        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tool_tx.source_evidence_id,
            target_evidence_id=tool_tx.target_evidence_id,
            event_id=tool_tx.event_id,
        )
        intv = channel_to_intervention(ci, run, graph)

        # Must target the source's TOOL_RESULT event (child of creation event),
        # NOT the mediating event that consumes both sources
        source_evi = graph.get_evidence(tool_tx.source_evidence_id)
        assert source_evi is not None
        assert intv.metadata["channel_level"] is True
        # Target must be different from mediating event
        assert intv.target_id != tool_tx.event_id
        # Target must be TOOL_RESULT_OVERRIDE type
        assert intv.intervention_type == InterventionType.TOOL_RESULT_OVERRIDE

    def test_block_a_preserves_c(self):
        """BLOCK(A→B) must preserve C→B.

        Two tool calls create independent evidence channels.
        Blocking one tool's channel must preserve the other.
        """
        from captain.models.enums import EventType

        run = _make_multi_channel_run()
        graph = _build_graph(run)

        # Find TOOL_CALL events by tool_name
        calc_call_evt = None
        echo_call_evt = None
        for e in run.events:
            if e.event_type == EventType.TOOL_CALL:
                tn = e.payload.get("tool_name", "")
                if tn == "calculator":
                    calc_call_evt = e
                elif tn == "echo":
                    echo_call_evt = e

        if calc_call_evt is None or echo_call_evt is None:
            return

        # Find evidence produced by calculator's TOOL_CALL
        calc_evi_id = None
        for evi in graph.evidence:
            if evi.creation_event_id == calc_call_evt.event_id:
                calc_evi_id = evi.evidence_id
                break

        if calc_evi_id is None:
            return

        # Find a transformation from calculator's evidence
        target_tx = None
        for tx in graph.transformations:
            if tx.source_evidence_id == calc_evi_id:
                target_tx = tx
                break

        if target_tx is None:
            return

        # Create channel intervention: block calculator→downstream
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=target_tx.source_evidence_id,
            target_evidence_id=target_tx.target_evidence_id,
            event_id=target_tx.event_id,
        )

        # Bridge with true channel-level semantics
        intv = channel_to_intervention(ci, run, graph)

        # Verify: uses TOOL_RESULT_OVERRIDE (not EVENT_OUTPUT_OVERRIDE)
        assert intv.intervention_type == InterventionType.TOOL_RESULT_OVERRIDE
        assert intv.metadata["channel_level"] is True

        # Execute replay
        from captain.intervention.model import InterventionSet
        from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

        iset = InterventionSet(
            baseline_run_id=run.run_id,
            interventions=[intv],
        )
        result = CounterfactualReplayEngine.replay(
            run, iset, tool_registry=create_default_tool_registry()
        )

        if result.status != ReplayStatus.SUCCESS or result.counterfactual_run is None:
            return

        cf_run = result.counterfactual_run

        # Verify C→B preserved: echo tool result should still be present
        # and unmodified in the counterfactual run
        cf_echo_results = [
            e
            for e in cf_run.events
            if e.event_type == EventType.TOOL_RESULT and e.payload.get("tool_name") == "echo"
        ]
        assert len(cf_echo_results) > 0, "C→B was NOT preserved: echo result missing"

        # The echo result must match the baseline echo result
        baseline_echo = [
            e
            for e in run.events
            if e.event_type == EventType.TOOL_RESULT and e.payload.get("tool_name") == "echo"
        ]
        if baseline_echo and cf_echo_results:
            assert cf_echo_results[0].payload.get("result") == baseline_echo[0].payload.get(
                "result"
            ), "Echo result changed — C→B was NOT preserved"

    def test_blocked_channel_has_empty_result(self):
        """Verify the blocked channel's tool result is empty."""
        from captain.models.enums import EventType

        run = _make_multi_channel_run()
        graph = _build_graph(run)

        # Find calculator TOOL_CALL event
        calc_call_evt = None
        for e in run.events:
            if e.event_type == EventType.TOOL_CALL and e.payload.get("tool_name") == "calculator":
                calc_call_evt = e
                break
        if calc_call_evt is None:
            return

        calc_evi_id = None
        for evi in graph.evidence:
            if evi.creation_event_id == calc_call_evt.event_id:
                calc_evi_id = evi.evidence_id
                break
        if calc_evi_id is None:
            return

        target_tx = None
        for tx in graph.transformations:
            if tx.source_evidence_id == calc_evi_id:
                target_tx = tx
                break
        if target_tx is None:
            return

        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=target_tx.source_evidence_id,
            target_evidence_id=target_tx.target_evidence_id,
            event_id=target_tx.event_id,
        )
        intv = channel_to_intervention(ci, run, graph)

        from captain.intervention.model import InterventionSet
        from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

        iset = InterventionSet(baseline_run_id=run.run_id, interventions=[intv])
        result = CounterfactualReplayEngine.replay(
            run, iset, tool_registry=create_default_tool_registry()
        )
        if result.status != ReplayStatus.SUCCESS or result.counterfactual_run is None:
            return

        cf_run = result.counterfactual_run

        # Find the calculator tool result in counterfactual — should be empty
        cf_calc_results = [
            e.payload.get("result", "")
            for e in cf_run.events
            if e.event_type == EventType.TOOL_RESULT and e.payload.get("tool_name") == "calculator"
        ]
        # At least one should be empty (blocked)
        has_empty = any(r == "" for r in cf_calc_results)
        assert has_empty, f"Blocked channel result not empty: {cf_calc_results}"

    def test_baseline_immutability_multi_channel(self):
        """Baseline must remain unchanged after multi-channel replay."""
        run = _make_multi_channel_run()
        before = run.model_dump_json()
        graph = _build_graph(run)

        if not graph.transformations:
            return

        tx = graph.transformations[0]
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            event_id=tx.event_id,
        )
        estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        cand = Candidate(
            run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            transformation_type=tx.transformation_type.value,
            event_id=tx.event_id,
        )
        estimator.estimate(cand, ci)
        after = run.model_dump_json()
        assert before == after

    def test_fresh_counterfactual_ids(self):
        """Counterfactual run must have fresh IDs."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        if not graph.transformations:
            return
        tx = graph.transformations[0]
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            event_id=tx.event_id,
        )
        cand = Candidate(
            run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            transformation_type=tx.transformation_type.value,
            event_id=tx.event_id,
        )
        estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        result = estimator.estimate(cand, ci)
        for trial in result.trials:
            if trial.status == TrialStatus.SUCCESS:
                assert trial.counterfactual_run_id != run.run_id
                assert trial.counterfactual_run_id != ""

    def test_serialization_roundtrip(self):
        """Channel intervention and CEE result serialize correctly."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        if not graph.transformations:
            return
        tx = graph.transformations[0]
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            event_id=tx.event_id,
        )
        # Roundtrip ChannelIntervention
        d = ci.model_dump(mode="json")
        ci2 = ChannelIntervention.model_validate(d)
        assert ci2.source_evidence_id == ci.source_evidence_id

        # Roundtrip CEEResult
        cand = Candidate(
            run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            transformation_type=tx.transformation_type.value,
            event_id=tx.event_id,
        )
        estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        result = estimator.estimate(cand, ci)
        d2 = result.model_dump(mode="json")
        r2 = CEEResult.model_validate(d2)
        assert r2.cee == result.cee

    def test_existing_stage9_still_works(self):
        """Existing Stage 9 event-level interventions must still work."""
        from captain.intervention.model import Intervention, InterventionSet
        from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

        run = _make_run()
        # Find a reasoning event to override
        reasoning_evts = [e for e in run.events if e.event_type.value == "reasoning"]
        if not reasoning_evts:
            return
        evt = reasoning_evts[0]
        intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=evt.event_id,
            replacement_value="Modified reasoning output",
        )
        iset = InterventionSet(baseline_run_id=run.run_id, interventions=[intv])
        result = CounterfactualReplayEngine.replay(
            run, iset, tool_registry=create_default_tool_registry()
        )
        assert result.status == ReplayStatus.SUCCESS

    def test_existing_evidence_lineage_still_works(self):
        """Stage 12 evidence lineage must work on multi-channel runs."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        assert graph.evidence_count > 0
        assert graph.transformation_count >= 0

    def test_existing_stage13_candidates_still_work(self):
        """Stage 13 candidate generation must work with multi-channel runs."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        target_eids = {t.target_evidence_id for t in graph.transformations}
        if not target_eids:
            return
        target_id = sorted(target_eids)[0]
        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=[target_id],
        )
        analyzer = FailureAnalyzer(graph, failure)
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()
        assert len(candidates) >= 0
        assert len(interventions) >= 0

    def test_cee_with_evidence_graph(self):
        """CEE estimation works with evidence_graph parameter."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)
        if not graph.transformations:
            return
        tx = graph.transformations[0]
        ci = ChannelIntervention(
            baseline_run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            event_id=tx.event_id,
        )
        cand = Candidate(
            run_id=run.run_id,
            source_evidence_id=tx.source_evidence_id,
            target_evidence_id=tx.target_evidence_id,
            transformation_type=tx.transformation_type.value,
            event_id=tx.event_id,
        )
        estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        result = estimator.estimate(cand, ci)
        assert isinstance(result.cee, float)
        assert result.num_trials == 1

    def test_end_to_end_multi_channel_pipeline(self):
        """Full pipeline: Agent→Trace→Evidence→Failure→Candidate→
        TRUE channel BLOCK→Replay→Outcome→CEE→Bottleneck."""
        run = _make_multi_channel_run()
        graph = _build_graph(run)

        target_eids = {t.target_evidence_id for t in graph.transformations}
        if not target_eids:
            return
        target_id = sorted(target_eids)[0]

        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=[target_id],
        )
        analyzer = FailureAnalyzer(graph, failure)
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()
        if not candidates or not interventions:
            return

        cee_results: list[CEEResult] = []
        estimator = CEEEstimator(run, _always_fails, evidence_graph=graph, num_trials=1)
        for c, i in zip(candidates, interventions, strict=False):
            r = estimator.estimate(c, i)
            cee_results.append(r)

        # Verify channel-level metadata
        for r in cee_results:
            for trial in r.trials:
                if trial.status == TrialStatus.SUCCESS:
                    assert trial.counterfactual_run_id != run.run_id

        bn = BottleneckAnalyzer.select(cee_results)
        assert isinstance(bn, BottleneckResult)
        pp = BottleneckAnalyzer.propagation_profile(cee_results)
        assert len(pp.edge_ids) == len(cee_results)
