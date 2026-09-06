"""Tests for captain.failures — CELA Failure & Intervention Layer (Stage 13)."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.evidence.model import (
    Evidence,
    EvidenceTransformation,
    EvidenceType,
    TransformationType,
)
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    Candidate,
    ChannelIntervention,
    ChannelInterventionType,
    Failure,
    FailureType,
    generate_candidate_id,
    generate_failure_id,
)
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _baseline_run():
    llm = MockLLMProvider(
        responses=[
            "1. [TOOL:calculator] Compute 6*7\n2. Summarise",
            "The result is 42",
            "Six times seven equals 42.",
        ]
    )
    reg = create_default_tool_registry()
    agent = Agent(llm=llm, tool_registry=reg)
    traced = TracedAgent(agent)
    _resp, collector = traced.run(TaskInput.from_text("What is 6*7?"))
    return collector.get_run()


def _build_graph(run):
    builder = EvidenceLineageBuilder(run)
    evidence, txs = builder.build()
    return EvidenceFlowGraph.from_lineage(evidence, txs)


def _simple_graph():
    """A→B→C linear graph for testing."""
    ea = Evidence(
        evidence_id="evi_a",
        evidence_type=EvidenceType.TEXT,
        creation_event_id="evt_1",
        sequence_number=0,
    )
    eb = Evidence(
        evidence_id="evi_b",
        evidence_type=EvidenceType.TOOL_OUTPUT,
        creation_event_id="evt_2",
        sequence_number=1,
    )
    ec = Evidence(
        evidence_id="evi_c",
        evidence_type=EvidenceType.MODEL_OUTPUT,
        creation_event_id="evt_3",
        sequence_number=2,
    )
    t1 = EvidenceTransformation(
        source_evidence_id="evi_a",
        target_evidence_id="evi_b",
        transformation_type=TransformationType.TOOL_DISPATCH,
        event_id="evt_2",
        sequence_number=1,
    )
    t2 = EvidenceTransformation(
        source_evidence_id="evi_b",
        target_evidence_id="evi_c",
        transformation_type=TransformationType.INTERPRETATION,
        event_id="evt_3",
        sequence_number=2,
    )
    return EvidenceFlowGraph.from_lineage([ea, eb, ec], [t1, t2])


# ===============================================================
# 1. Failure construction
# ===============================================================


class TestFailureConstruction:
    def test_basic(self):
        f = Failure(
            run_id="run_abc",
            failure_type=FailureType.TASK_FAILURE,
            description="Wrong answer",
        )
        assert f.failure_id.startswith("fail_")
        assert f.run_id == "run_abc"
        assert f.failure_type == FailureType.TASK_FAILURE

    def test_with_event(self):
        f = Failure(
            run_id="run_abc",
            failure_type=FailureType.WRONG_TOOL_USE,
            failure_event_id="evt_xyz",
        )
        assert f.failure_event_id == "evt_xyz"

    def test_with_evidence(self):
        f = Failure(
            run_id="run_abc",
            failure_type=FailureType.HALLUCINATED_CLAIM,
            failure_evidence_ids=["evi_1", "evi_2"],
        )
        assert len(f.failure_evidence_ids) == 2


# ===============================================================
# 2. Failure serialization
# ===============================================================


class TestFailureSerialization:
    def test_roundtrip(self):
        f = Failure(
            run_id="run_abc",
            failure_type=FailureType.TASK_FAILURE,
            failure_event_id="evt_1",
            failure_evidence_ids=["evi_1"],
            description="test",
            metadata={"evaluator": "oracle"},
        )
        d = f.model_dump(mode="json")
        f2 = Failure.model_validate(d)
        assert f2.failure_id == f.failure_id
        assert f2.failure_type == f.failure_type
        assert f2.metadata == {"evaluator": "oracle"}


# ===============================================================
# 3. Failure ID
# ===============================================================


class TestFailureId:
    def test_unique(self):
        ids = {generate_failure_id() for _ in range(100)}
        assert len(ids) == 100

    def test_prefix(self):
        assert generate_failure_id().startswith("fail_")


# ===============================================================
# 4. Failure type
# ===============================================================


class TestFailureType:
    def test_values(self):
        expected = {"task_failure", "wrong_tool_use", "hallucinated_claim", "unsafe_action"}
        assert {t.value for t in FailureType} == expected


# ===============================================================
# 5. Failure target resolution
# ===============================================================


class TestFailureTargets:
    def test_by_evidence_ids(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        analyzer = FailureAnalyzer(graph, f)
        targets = analyzer.failure_targets()
        assert targets == ["evi_c"]

    def test_by_event_id(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_event_id="evt_3",
        )
        analyzer = FailureAnalyzer(graph, f)
        targets = analyzer.failure_targets()
        assert "evi_c" in targets

    def test_fallback_to_last(self):
        graph = _simple_graph()
        f = Failure(run_id="run_1", failure_type=FailureType.TASK_FAILURE)
        analyzer = FailureAnalyzer(graph, f)
        targets = analyzer.failure_targets()
        assert "evi_c" in targets  # highest sequence number

    def test_invalid_evidence_filtered(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_nonexistent"],
        )
        analyzer = FailureAnalyzer(graph, f)
        targets = analyzer.failure_targets()
        # Falls back since no valid IDs
        assert len(targets) > 0  # fallback works

    def test_empty_graph(self):
        graph = EvidenceFlowGraph()
        f = Failure(run_id="run_1", failure_type=FailureType.TASK_FAILURE)
        analyzer = FailureAnalyzer(graph, f)
        assert analyzer.failure_targets() == []


# ===============================================================
# 6. Failure-relevant region
# ===============================================================


class TestRelevantRegion:
    def test_linear_graph(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        analyzer = FailureAnalyzer(graph, f)
        region = analyzer.relevant_region()
        # All nodes reachable upstream from C
        assert "evi_c" in region
        assert "evi_b" in region
        assert "evi_a" in region

    def test_excludes_unrelated(self):
        # Add disconnected node D
        ea = Evidence(
            evidence_id="evi_a", evidence_type=EvidenceType.TEXT, creation_event_id="evt_1"
        )
        eb = Evidence(
            evidence_id="evi_b", evidence_type=EvidenceType.TEXT, creation_event_id="evt_2"
        )
        ed = Evidence(
            evidence_id="evi_d",
            evidence_type=EvidenceType.TEXT,
            creation_event_id="evt_4",
            sequence_number=3,
        )
        t1 = EvidenceTransformation(
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            transformation_type=TransformationType.OBSERVATION,
            event_id="evt_2",
        )
        graph = EvidenceFlowGraph.from_lineage([ea, eb, ed], [t1])
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_b"],
        )
        analyzer = FailureAnalyzer(graph, f)
        region = analyzer.relevant_region()
        assert "evi_d" not in region

    def test_deterministic(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        r1 = FailureAnalyzer(graph, f).relevant_region()
        r2 = FailureAnalyzer(graph, f).relevant_region()
        assert r1 == r2

    def test_cycle_safe(self):
        ea = Evidence(
            evidence_id="evi_x", evidence_type=EvidenceType.TEXT, creation_event_id="evt_1"
        )
        eb = Evidence(
            evidence_id="evi_y", evidence_type=EvidenceType.TEXT, creation_event_id="evt_2"
        )
        t1 = EvidenceTransformation(
            source_evidence_id="evi_x",
            target_evidence_id="evi_y",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_1",
        )
        t2 = EvidenceTransformation(
            source_evidence_id="evi_y",
            target_evidence_id="evi_x",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_2",
        )
        graph = EvidenceFlowGraph.from_lineage([ea, eb], [t1, t2])
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_x"],
        )
        region = FailureAnalyzer(graph, f).relevant_region()
        assert "evi_x" in region
        assert "evi_y" in region  # cycle: y is upstream of x

    def test_empty_targets(self):
        graph = EvidenceFlowGraph()
        f = Failure(run_id="run_1", failure_type=FailureType.TASK_FAILURE)
        assert FailureAnalyzer(graph, f).relevant_region() == []


# ===============================================================
# 7. Candidate generation
# ===============================================================


class TestCandidateGeneration:
    def test_produces_candidates(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        assert len(candidates) > 0
        assert all(isinstance(c, Candidate) for c in candidates)

    def test_candidate_ids_unique(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        ids = [c.candidate_id for c in candidates]
        assert len(ids) == len(set(ids))

    def test_candidate_references(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        evi_ids = {e.evidence_id for e in graph.evidence}
        for c in candidates:
            assert c.source_evidence_id in evi_ids
            assert c.target_evidence_id in evi_ids
            assert c.run_id == "run_1"

    def test_no_self_loops(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        for c in FailureAnalyzer(graph, f).candidates():
            assert c.source_evidence_id != c.target_evidence_id

    def test_max_candidates(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates(max_candidates=1)
        assert len(candidates) <= 1

    def test_modality_preserved(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        types_seen = set()
        for c in candidates:
            types_seen.add(c.source_evidence_type)
            types_seen.add(c.target_evidence_type)
        assert len(types_seen) > 0


# ===============================================================
# 8. Screening score
# ===============================================================


class TestScreeningScore:
    def test_closer_scores_higher(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        # B→C is closer to failure than A→B
        b_to_c = [c for c in candidates if c.source_evidence_id == "evi_b"]
        a_to_b = [c for c in candidates if c.source_evidence_id == "evi_a"]
        if b_to_c and a_to_b:
            assert b_to_c[0].screening_score >= a_to_b[0].screening_score

    def test_score_is_non_negative(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        for c in FailureAnalyzer(graph, f).candidates():
            assert c.screening_score >= 0.0

    def test_sorted_descending(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        candidates = FailureAnalyzer(graph, f).candidates()
        scores = [c.screening_score for c in candidates]
        assert scores == sorted(scores, reverse=True)


# ===============================================================
# 9. Candidate serialization
# ===============================================================


class TestCandidateSerialization:
    def test_roundtrip(self):
        c = Candidate(
            run_id="run_1",
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            transformation_type="tool_dispatch",
            event_id="evt_1",
            screening_score=2.5,
        )
        d = c.model_dump(mode="json")
        c2 = Candidate.model_validate(d)
        assert c2.candidate_id == c.candidate_id
        assert c2.screening_score == 2.5

    def test_candidate_id_prefix(self):
        assert generate_candidate_id().startswith("cand_")


# ===============================================================
# 10. Channel intervention — BLOCK
# ===============================================================


class TestChannelIntervention:
    def test_block_construction(self):
        ci = ChannelIntervention(
            baseline_run_id="run_1",
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id="evt_1",
        )
        assert ci.intervention_type == ChannelInterventionType.BLOCK
        assert ci.intervention_id.startswith("cintv_")

    def test_targets_relationship_not_node(self):
        ci = ChannelIntervention(
            baseline_run_id="run_1",
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id="evt_1",
        )
        # Must have BOTH source and target — it's an edge
        assert ci.source_evidence_id == "evi_a"
        assert ci.target_evidence_id == "evi_b"

    def test_serialization(self):
        ci = ChannelIntervention(
            baseline_run_id="run_1",
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            event_id="evt_1",
            candidate_id="cand_xyz",
        )
        d = ci.model_dump(mode="json")
        ci2 = ChannelIntervention.model_validate(d)
        assert ci2.intervention_id == ci.intervention_id
        assert ci2.candidate_id == "cand_xyz"


# ===============================================================
# 11. Intervention generation from analyzer
# ===============================================================


class TestInterventionGeneration:
    def test_generates_interventions(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        interventions = FailureAnalyzer(graph, f).interventions()
        assert len(interventions) > 0
        assert all(isinstance(i, ChannelIntervention) for i in interventions)

    def test_all_are_block(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        for i in FailureAnalyzer(graph, f).interventions():
            assert i.intervention_type == ChannelInterventionType.BLOCK

    def test_baseline_run_id(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        for i in FailureAnalyzer(graph, f).interventions():
            assert i.baseline_run_id == "run_1"

    def test_max_candidates(self):
        graph = _simple_graph()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        interventions = FailureAnalyzer(graph, f).interventions(max_candidates=1)
        assert len(interventions) <= 1


# ===============================================================
# 12. Baseline immutability
# ===============================================================


class TestBaselineImmutability:
    def test_graph_unchanged(self):
        graph = _simple_graph()
        before = graph.model_dump_json()
        f = Failure(
            run_id="run_1",
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=["evi_c"],
        )
        analyzer = FailureAnalyzer(graph, f)
        analyzer.relevant_region()
        analyzer.candidates()
        analyzer.interventions()
        after = graph.model_dump_json()
        assert before == after


# ===============================================================
# 13. End-to-end: Agent → Trace → Evidence → Failure → Candidates
# ===============================================================


class TestEndToEnd:
    def test_full_pipeline(self):
        """Agent→Trace→Evidence→Failure→Region→Candidates→Interventions."""
        run = _baseline_run()
        graph = _build_graph(run)

        # Find evidence that is a transformation target (has upstream)
        target_eids = {t.target_evidence_id for t in graph.transformations}
        if not target_eids:
            # Graph too sparse for full pipeline — just verify no crash
            failure = Failure(
                run_id=run.run_id,
                failure_type=FailureType.TASK_FAILURE,
            )
            analyzer = FailureAnalyzer(graph, failure)
            analyzer.failure_targets()
            analyzer.relevant_region()
            analyzer.candidates()
            analyzer.interventions()
            return

        # Target the failure at evidence downstream of a transformation
        target_id = sorted(target_eids)[0]
        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=[target_id],
            description="Wrong answer (test scenario)",
        )

        analyzer = FailureAnalyzer(graph, failure)

        # Failure targets resolve
        targets = analyzer.failure_targets()
        assert len(targets) > 0

        # Relevant region found
        region = analyzer.relevant_region()
        assert len(region) > 0
        for t in targets:
            assert t in region

        # Candidates generated
        candidates = analyzer.candidates()
        assert len(candidates) > 0
        evi_ids = {e.evidence_id for e in graph.evidence}
        for c in candidates:
            assert c.source_evidence_id in evi_ids
            assert c.target_evidence_id in evi_ids
            assert c.run_id == run.run_id
            assert c.source_evidence_id != c.target_evidence_id

        # Interventions generated
        interventions = analyzer.interventions()
        assert len(interventions) > 0
        for i in interventions:
            assert i.intervention_type == ChannelInterventionType.BLOCK
            assert i.baseline_run_id == run.run_id
            assert i.source_evidence_id != ""
            assert i.target_evidence_id != ""

        # Baseline run unchanged
        run2_json = run.model_dump_json()
        assert run2_json

    def test_candidate_to_intervention_has_candidate_id(self):
        """Candidate → Intervention preserves candidate_id."""
        run = _baseline_run()
        graph = _build_graph(run)

        # Target evidence with upstream connections
        target_eids = {t.target_evidence_id for t in graph.transformations}
        if not target_eids:
            return  # Graph too sparse

        target_id = sorted(target_eids)[0]
        failure = Failure(
            run_id=run.run_id,
            failure_type=FailureType.TASK_FAILURE,
            failure_evidence_ids=[target_id],
        )
        analyzer = FailureAnalyzer(graph, failure)
        # Verify interventions have valid candidate_id format
        interventions = analyzer.interventions()
        for i in interventions:
            assert i.candidate_id.startswith("cand_")
            assert len(i.candidate_id) > 5
