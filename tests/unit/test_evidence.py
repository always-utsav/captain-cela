"""Tests for captain.evidence — CELA Evidence Layer (Stage 12)."""

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
    ProvenanceMethod,
    TransformationType,
    generate_evidence_id,
)
from captain.provenance.extractor import ProvenanceExtractor
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------
# Helper: deterministic baseline run
# ---------------------------------------------------------------


def _baseline():
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
    _resp, collector = traced.run(TaskInput.from_text("What is 6 times 7?"))
    return collector.get_run()


# ===============================================================
# 1. Evidence ID
# ===============================================================


class TestEvidenceId:
    def test_unique(self):
        ids = {generate_evidence_id() for _ in range(100)}
        assert len(ids) == 100

    def test_prefix(self):
        eid = generate_evidence_id()
        assert eid.startswith("evi_")

    def test_distinct_from_artifact(self):
        from captain.models.ids import generate_artifact_id

        eid = generate_evidence_id()
        aid = generate_artifact_id()
        assert eid[:4] != aid[:4]


# ===============================================================
# 2. Evidence construction
# ===============================================================


class TestEvidenceConstruction:
    def test_basic(self):
        e = Evidence(
            evidence_type=EvidenceType.TEXT,
            creation_event_id="evt_abc",
            sequence_number=0,
        )
        assert e.evidence_id.startswith("evi_")
        assert e.evidence_type == EvidenceType.TEXT
        assert e.creation_event_id == "evt_abc"
        assert e.artifact_id is None
        assert e.parent_evidence_ids == []

    def test_with_artifact(self):
        e = Evidence(
            evidence_type=EvidenceType.TOOL_OUTPUT,
            artifact_id="art_xyz",
            creation_event_id="evt_abc",
        )
        assert e.artifact_id == "art_xyz"

    def test_serialization(self):
        e = Evidence(
            evidence_type=EvidenceType.MEMORY,
            creation_event_id="evt_abc",
            metadata={"key": "task"},
        )
        d = e.model_dump(mode="json")
        e2 = Evidence.model_validate(d)
        assert e2.evidence_id == e.evidence_id
        assert e2.evidence_type == e.evidence_type
        assert e2.metadata == e.metadata


# ===============================================================
# 3. Evidence type / modality
# ===============================================================


class TestEvidenceType:
    def test_all_types(self):
        expected = {
            "text",
            "image",
            "structured",
            "memory",
            "tool_input",
            "tool_output",
            "model_output",
        }
        assert {t.value for t in EvidenceType} == expected

    def test_extensible(self):
        assert isinstance(EvidenceType.TEXT, str)


# ===============================================================
# 4. Transformation construction
# ===============================================================


class TestTransformation:
    def test_basic(self):
        t = EvidenceTransformation(
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_x",
        )
        assert t.provenance_method == ProvenanceMethod.HARD
        assert t.confidence == 1.0

    def test_serialization(self):
        t = EvidenceTransformation(
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            transformation_type=TransformationType.TOOL_DISPATCH,
            event_id="evt_x",
            sequence_number=5,
        )
        d = t.model_dump(mode="json")
        t2 = EvidenceTransformation.model_validate(d)
        assert t2.source_evidence_id == "evi_a"
        assert t2.transformation_type == TransformationType.TOOL_DISPATCH


# ===============================================================
# 5. Transformation type taxonomy
# ===============================================================


class TestTransformationType:
    def test_all_types(self):
        expected = {
            "observation",
            "interpretation",
            "memory_store",
            "planning_derivation",
            "tool_dispatch",
            "tool_return",
            "response_derivation",
        }
        assert {t.value for t in TransformationType} == expected


# ===============================================================
# 6. Provenance method
# ===============================================================


class TestProvenanceMethod:
    def test_hard_is_default(self):
        t = EvidenceTransformation(
            source_evidence_id="evi_a",
            target_evidence_id="evi_b",
            transformation_type=TransformationType.OBSERVATION,
            event_id="evt_x",
        )
        assert t.provenance_method == ProvenanceMethod.HARD

    def test_values(self):
        assert {m.value for m in ProvenanceMethod} == {"hard", "semantic", "hybrid"}


# ===============================================================
# 7. Lineage builder — basic extraction
# ===============================================================


class TestLineageBuilder:
    def test_builds_evidence(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _txs = builder.build()
        assert len(evidence) > 0
        assert all(isinstance(e, Evidence) for e in evidence)

    def test_builds_transformations(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        _evidence, txs = builder.build()
        assert len(txs) > 0
        assert all(isinstance(t, EvidenceTransformation) for t in txs)

    def test_evidence_ids_unique(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _ = builder.build()
        ids = [e.evidence_id for e in evidence]
        assert len(ids) == len(set(ids))

    def test_evidence_ids_distinct_from_artifacts(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _ = builder.build()
        art_ids = {a.artifact_id for a in run.artifacts}
        evi_ids = {e.evidence_id for e in evidence}
        assert art_ids.isdisjoint(evi_ids)

    def test_artifact_references(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _ = builder.build()
        art_ids = {a.artifact_id for a in run.artifacts}
        for e in evidence:
            if e.artifact_id:
                assert e.artifact_id in art_ids

    def test_all_hard_provenance(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        _, txs = builder.build()
        for t in txs:
            assert t.provenance_method == ProvenanceMethod.HARD
            assert t.confidence == 1.0


# ===============================================================
# 8. Producer/consumer relationships
# ===============================================================


class TestProducerConsumer:
    def test_transformation_references_valid_evidence(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        evi_ids = {e.evidence_id for e in evidence}
        for t in txs:
            assert t.source_evidence_id in evi_ids
            assert t.target_evidence_id in evi_ids

    def test_no_self_loops(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        _, txs = builder.build()
        for t in txs:
            assert t.source_evidence_id != t.target_evidence_id

    def test_parent_evidence_populated(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        if txs:
            targets = {t.target_evidence_id for t in txs}
            for e in evidence:
                if e.evidence_id in targets:
                    assert len(e.parent_evidence_ids) > 0


# ===============================================================
# 9. Upstream traversal
# ===============================================================


class TestUpstream:
    def test_upstream(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)

        # Find an evidence with incoming edges
        for e in evidence:
            inc = graph.incoming(e.evidence_id)
            if inc:
                ups = graph.upstream(e.evidence_id)
                assert len(ups) > 0
                assert e.evidence_id not in ups
                break


# ===============================================================
# 10. Downstream traversal
# ===============================================================


class TestDownstream:
    def test_downstream(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)

        # Find an evidence with outgoing edges
        for e in evidence:
            out = graph.outgoing(e.evidence_id)
            if out:
                downs = graph.downstream(e.evidence_id)
                assert len(downs) > 0
                assert e.evidence_id not in downs
                break


# ===============================================================
# 11. Cycle-safe traversal
# ===============================================================


class TestCycleSafe:
    def test_cycle_safe_upstream(self):
        # Construct graph with cycle
        e1 = Evidence(
            evidence_type=EvidenceType.TEXT, creation_event_id="evt_a", evidence_id="evi_1"
        )
        e2 = Evidence(
            evidence_type=EvidenceType.TEXT, creation_event_id="evt_b", evidence_id="evi_2"
        )
        t1 = EvidenceTransformation(
            source_evidence_id="evi_1",
            target_evidence_id="evi_2",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_a",
        )
        t2 = EvidenceTransformation(
            source_evidence_id="evi_2",
            target_evidence_id="evi_1",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_b",
        )
        graph = EvidenceFlowGraph.from_lineage([e1, e2], [t1, t2])
        ups = graph.upstream("evi_1")
        assert "evi_2" in ups
        assert "evi_1" not in ups  # no infinite loop

    def test_cycle_safe_downstream(self):
        e1 = Evidence(
            evidence_type=EvidenceType.TEXT, creation_event_id="evt_a", evidence_id="evi_1"
        )
        e2 = Evidence(
            evidence_type=EvidenceType.TEXT, creation_event_id="evt_b", evidence_id="evi_2"
        )
        t1 = EvidenceTransformation(
            source_evidence_id="evi_1",
            target_evidence_id="evi_2",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_a",
        )
        t2 = EvidenceTransformation(
            source_evidence_id="evi_2",
            target_evidence_id="evi_1",
            transformation_type=TransformationType.INTERPRETATION,
            event_id="evt_b",
        )
        graph = EvidenceFlowGraph.from_lineage([e1, e2], [t1, t2])
        downs = graph.downstream("evi_1")
        assert "evi_2" in downs
        assert "evi_1" not in downs


# ===============================================================
# 12. Temporal identity
# ===============================================================


class TestTemporalIdentity:
    def test_distinct_sequence_numbers(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _ = builder.build()
        # Evidence at different sequence numbers are distinct
        seqs = [e.sequence_number for e in evidence]
        assert len(seqs) > 1  # multiple temporal positions

    def test_same_content_different_evidence(self):
        # Two evidence objects at different times are distinct
        e1 = Evidence(
            evidence_type=EvidenceType.TEXT,
            creation_event_id="evt_a",
            sequence_number=0,
        )
        e2 = Evidence(
            evidence_type=EvidenceType.TEXT,
            creation_event_id="evt_b",
            sequence_number=5,
        )
        assert e1.evidence_id != e2.evidence_id


# ===============================================================
# 13. Deterministic reconstruction
# ===============================================================


class TestDeterminism:
    def test_same_run_same_structure(self):
        run = _baseline()
        b1 = EvidenceLineageBuilder(run)
        e1, t1 = b1.build()
        b2 = EvidenceLineageBuilder(run)
        e2, t2 = b2.build()
        assert len(e1) == len(e2)
        assert len(t1) == len(t2)
        # Same evidence types in same order
        assert [e.evidence_type for e in e1] == [e.evidence_type for e in e2]
        # Same artifact references
        assert [e.artifact_id for e in e1] == [e.artifact_id for e in e2]


# ===============================================================
# 14. Missing/invalid provenance
# ===============================================================


class TestMissingProvenance:
    def test_empty_run(self):
        from captain.models.execution import ExecutionRun

        run = ExecutionRun(task_input="test")
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        assert evidence == []
        assert txs == []


# ===============================================================
# 15. Integration with ExecutionRun
# ===============================================================


class TestExecutionRunIntegration:
    def test_all_artifacts_covered(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, _ = builder.build()
        # Every artifact should have corresponding evidence
        art_ids = {a.artifact_id for a in run.artifacts}
        covered = {e.artifact_id for e in evidence if e.artifact_id}
        assert art_ids == covered

    def test_event_references_valid(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        evt_ids = {e.event_id for e in run.events}
        for e in evidence:
            if e.creation_event_id:
                assert e.creation_event_id in evt_ids
        for t in txs:
            assert t.event_id in evt_ids


# ===============================================================
# 16. Integration with ProvenanceExtractor
# ===============================================================


class TestProvenanceIntegration:
    def test_uses_provenance(self):
        run = _baseline()
        prov = ProvenanceExtractor(run)
        records = prov.extract()
        builder = EvidenceLineageBuilder(run)
        _, txs = builder.build()
        # Transformations should exist if provenance has
        # consumed relationships
        consumed = [r for r in records if r.relationship.value == "consumed"]
        if consumed:
            assert len(txs) > 0


# ===============================================================
# 17. Evidence graph serialization
# ===============================================================


class TestGraphSerialization:
    def test_to_dict(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)
        d = graph.to_dict()
        assert "evidence" in d
        assert "transformations" in d
        assert d["evidence_count"] == len(evidence)
        assert d["transformation_count"] == len(txs)

    def test_json_roundtrip(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)
        json_str = graph.model_dump_json()
        graph2 = EvidenceFlowGraph.model_validate_json(json_str)
        assert graph2.evidence_count == graph.evidence_count
        assert graph2.transformation_count == graph.transformation_count


# ===============================================================
# 18. Evidence graph lookups
# ===============================================================


class TestGraphLookups:
    def test_get_evidence(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)
        for e in evidence:
            found = graph.get_evidence(e.evidence_id)
            assert found is not None
            assert found.evidence_id == e.evidence_id

    def test_get_by_artifact(self):
        run = _baseline()
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)
        for e in evidence:
            if e.artifact_id:
                found = graph.get_by_artifact(e.artifact_id)
                assert found is not None
                assert found.artifact_id == e.artifact_id

    def test_missing_returns_none(self):
        graph = EvidenceFlowGraph()
        assert graph.get_evidence("evi_nonexistent") is None
        assert graph.get_by_artifact("art_nonexistent") is None


# ===============================================================
# 19. End-to-end pipeline
# ===============================================================


class TestEndToEnd:
    def test_full_pipeline(self):
        """Agent → Trace → ExecutionRun → Evidence → Graph."""
        run = _baseline()

        # Build evidence layer
        builder = EvidenceLineageBuilder(run)
        evidence, txs = builder.build()

        # Build graph
        graph = EvidenceFlowGraph.from_lineage(evidence, txs)

        # Verify structure
        assert graph.evidence_count > 0
        assert graph.transformation_count > 0

        # All evidence IDs are unique
        ids = {e.evidence_id for e in graph.evidence}
        assert len(ids) == graph.evidence_count

        # All transformations reference valid evidence
        for t in graph.transformations:
            assert graph.get_evidence(t.source_evidence_id) is not None
            assert graph.get_evidence(t.target_evidence_id) is not None

        # Upstream/downstream work
        for e in evidence:
            graph.upstream(e.evidence_id)
            graph.downstream(e.evidence_id)

        # Serialization works
        d = graph.to_dict()
        assert isinstance(d, dict)

        # JSON roundtrip works
        json_str = graph.model_dump_json()
        graph2 = EvidenceFlowGraph.model_validate_json(json_str)
        assert graph2.evidence_count == graph.evidence_count
