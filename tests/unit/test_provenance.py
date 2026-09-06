"""Tests for captain.provenance -- extraction, queries, traversal."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import Content, Modality, TaskInput
from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_artifact_id, generate_event_id, generate_run_id
from captain.provenance.extractor import ProvenanceExtractor
from captain.provenance.model import RelationshipType
from captain.provenance.query import ProvenanceQuery
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_id() -> str:
    return generate_run_id()


def _make_linear_run() -> ExecutionRun:
    """Build a linear 3-event, 3-artifact run for testing.

    Event A (INPUT) -> produces Artifact X (TEXT)
    Event B (REASONING) -> consumes Artifact X, produces Artifact Y (MODEL_OUTPUT)
    Event C (OUTPUT) -> consumes Artifact Y, produces Artifact Z (TEXT)
    """
    run_id = _make_run_id()
    now = datetime.now(tz=UTC)

    evt_a_id = generate_event_id()
    evt_b_id = generate_event_id()
    evt_c_id = generate_event_id()
    art_x_id = generate_artifact_id()
    art_y_id = generate_artifact_id()
    art_z_id = generate_artifact_id()

    art_x = Artifact(
        artifact_id=art_x_id,
        artifact_type=ArtifactType.TEXT,
        value="user input",
        producer_event_id=evt_a_id,
    )
    art_y = Artifact(
        artifact_id=art_y_id,
        artifact_type=ArtifactType.MODEL_OUTPUT,
        value="model result",
        producer_event_id=evt_b_id,
    )
    art_z = Artifact(
        artifact_id=art_z_id,
        artifact_type=ArtifactType.TEXT,
        value="final output",
        producer_event_id=evt_c_id,
    )

    evt_a = Event(
        event_id=evt_a_id,
        run_id=run_id,
        event_type=EventType.INPUT,
        timestamp=now,
        sequence_number=0,
        component="agent",
        output_artifact_ids=[art_x_id],
    )
    evt_b = Event(
        event_id=evt_b_id,
        run_id=run_id,
        event_type=EventType.REASONING,
        timestamp=now,
        sequence_number=1,
        component="reasoner",
        input_artifact_ids=[art_x_id],
        output_artifact_ids=[art_y_id],
    )
    evt_c = Event(
        event_id=evt_c_id,
        run_id=run_id,
        event_type=EventType.OUTPUT,
        timestamp=now,
        sequence_number=2,
        component="response_generator",
        input_artifact_ids=[art_y_id],
        output_artifact_ids=[art_z_id],
    )

    return ExecutionRun(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        task_input="test",
        events=[evt_a, evt_b, evt_c],
        artifacts=[art_x, art_y, art_z],
    )


def _make_multimodal_run() -> ExecutionRun:
    """Build a run with IMAGE input -> REASONING -> TOOL -> OUTPUT.

    Event A (INPUT) -> produces Artifact IMG (IMAGE, by reference)
    Event B (REASONING) -> consumes IMG, produces Artifact TXT (TEXT)
    Event C (TOOL_CALL) -> consumes TXT, produces Artifact TOOL (TOOL_OUTPUT)
    Event D (OUTPUT) -> consumes TOOL, produces Artifact OUT (TEXT)
    """
    run_id = _make_run_id()
    now = datetime.now(tz=UTC)

    evt_a = generate_event_id()
    evt_b = generate_event_id()
    evt_c = generate_event_id()
    evt_d = generate_event_id()
    art_img = generate_artifact_id()
    art_txt = generate_artifact_id()
    art_tool = generate_artifact_id()
    art_out = generate_artifact_id()

    return ExecutionRun(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        task_input="describe image",
        events=[
            Event(
                event_id=evt_a,
                run_id=run_id,
                event_type=EventType.INPUT,
                timestamp=now,
                sequence_number=0,
                component="agent",
                output_artifact_ids=[art_img],
            ),
            Event(
                event_id=evt_b,
                run_id=run_id,
                event_type=EventType.REASONING,
                timestamp=now,
                sequence_number=1,
                component="reasoner",
                input_artifact_ids=[art_img],
                output_artifact_ids=[art_txt],
            ),
            Event(
                event_id=evt_c,
                run_id=run_id,
                event_type=EventType.TOOL_CALL,
                timestamp=now,
                sequence_number=2,
                component="tool:calc",
                input_artifact_ids=[art_txt],
                output_artifact_ids=[art_tool],
            ),
            Event(
                event_id=evt_d,
                run_id=run_id,
                event_type=EventType.OUTPUT,
                timestamp=now,
                sequence_number=3,
                component="response",
                input_artifact_ids=[art_tool],
                output_artifact_ids=[art_out],
            ),
        ],
        artifacts=[
            Artifact(
                artifact_id=art_img,
                artifact_type=ArtifactType.IMAGE,
                reference="s3://bucket/photo.jpg",
                producer_event_id=evt_a,
            ),
            Artifact(
                artifact_id=art_txt,
                artifact_type=ArtifactType.TEXT,
                value="derived text",
                producer_event_id=evt_b,
            ),
            Artifact(
                artifact_id=art_tool,
                artifact_type=ArtifactType.TOOL_OUTPUT,
                value="tool result",
                producer_event_id=evt_c,
            ),
            Artifact(
                artifact_id=art_out,
                artifact_type=ArtifactType.TEXT,
                value="final answer",
                producer_event_id=evt_d,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


class TestProvenanceExtractor:
    """Tests for ProvenanceExtractor."""

    def test_extract_produced_relationships(self) -> None:
        run = _make_linear_run()
        records = ProvenanceExtractor(run).extract()
        produced = [r for r in records if r.relationship == RelationshipType.PRODUCED]
        assert len(produced) == 3  # 3 artifacts, each produced by 1 event

    def test_extract_consumed_relationships(self) -> None:
        run = _make_linear_run()
        records = ProvenanceExtractor(run).extract()
        consumed = [r for r in records if r.relationship == RelationshipType.CONSUMED]
        assert len(consumed) == 2  # X consumed by B, Y consumed by C

    def test_producer_event_matches(self) -> None:
        run = _make_linear_run()
        records = ProvenanceExtractor(run).extract()
        art_x = run.artifacts[0]
        produced_x = [
            r
            for r in records
            if r.artifact_id == art_x.artifact_id and r.relationship == RelationshipType.PRODUCED
        ]
        assert len(produced_x) == 1
        assert produced_x[0].event_id == run.events[0].event_id

    def test_consumer_event_matches(self) -> None:
        run = _make_linear_run()
        records = ProvenanceExtractor(run).extract()
        art_x = run.artifacts[0]
        consumed_x = [
            r
            for r in records
            if r.artifact_id == art_x.artifact_id and r.relationship == RelationshipType.CONSUMED
        ]
        assert len(consumed_x) == 1
        assert consumed_x[0].event_id == run.events[1].event_id

    def test_multimodal_extraction(self) -> None:
        run = _make_multimodal_run()
        records = ProvenanceExtractor(run).extract()
        produced = [r for r in records if r.relationship == RelationshipType.PRODUCED]
        consumed = [r for r in records if r.relationship == RelationshipType.CONSUMED]
        assert len(produced) == 4  # IMG, TXT, TOOL, OUT
        assert len(consumed) == 3  # IMG->B, TXT->C, TOOL->D

    def test_deterministic_ordering(self) -> None:
        run = _make_linear_run()
        r1 = ProvenanceExtractor(run).extract()
        r2 = ProvenanceExtractor(run).extract()
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2, strict=True):
            assert a.artifact_id == b.artifact_id
            assert a.event_id == b.event_id
            assert a.relationship == b.relationship

    def test_empty_run(self) -> None:
        run = ExecutionRun(
            run_id=_make_run_id(),
            status=RunStatus.COMPLETED,
            task_input="empty",
        )
        records = ProvenanceExtractor(run).extract()
        assert records == []

    def test_no_duplicate_records(self) -> None:
        """Producer from output_artifact_ids and artifact.producer_event_id
        should not create duplicates."""
        run = _make_linear_run()
        records = ProvenanceExtractor(run).extract()
        keys = [(r.artifact_id, r.event_id, r.relationship) for r in records]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# Query tests: direct lookups
# ---------------------------------------------------------------------------


class TestProvenanceQueryDirect:
    """Tests for direct provenance queries."""

    def test_get_producer(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        assert pq.get_producer(art_x.artifact_id) == run.events[0].event_id

    def test_get_producer_missing(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        assert pq.get_producer("art_nonexistent") is None

    def test_get_consumers(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        consumers = pq.get_consumers(art_x.artifact_id)
        assert len(consumers) == 1
        assert consumers[0] == run.events[1].event_id

    def test_get_consumers_empty(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_z = run.artifacts[2]  # final output, no consumers
        assert pq.get_consumers(art_z.artifact_id) == []

    def test_get_upstream_artifacts(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        evt_b = run.events[1]
        upstream = pq.get_upstream_artifacts(evt_b.event_id)
        assert run.artifacts[0].artifact_id in upstream

    def test_get_downstream_artifacts(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        evt_b = run.events[1]
        downstream = pq.get_downstream_artifacts(evt_b.event_id)
        assert run.artifacts[1].artifact_id in downstream

    def test_multiple_consumers(self) -> None:
        """An artifact consumed by multiple events."""
        run_id = _make_run_id()
        now = datetime.now(tz=UTC)
        art_id = generate_artifact_id()
        evt_a = generate_event_id()
        evt_b = generate_event_id()
        evt_c = generate_event_id()

        run = ExecutionRun(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            task_input="multi",
            events=[
                Event(
                    event_id=evt_a,
                    run_id=run_id,
                    event_type=EventType.INPUT,
                    timestamp=now,
                    sequence_number=0,
                    output_artifact_ids=[art_id],
                ),
                Event(
                    event_id=evt_b,
                    run_id=run_id,
                    event_type=EventType.REASONING,
                    timestamp=now,
                    sequence_number=1,
                    input_artifact_ids=[art_id],
                ),
                Event(
                    event_id=evt_c,
                    run_id=run_id,
                    event_type=EventType.REASONING,
                    timestamp=now,
                    sequence_number=2,
                    input_artifact_ids=[art_id],
                ),
            ],
            artifacts=[
                Artifact(
                    artifact_id=art_id,
                    artifact_type=ArtifactType.TEXT,
                    value="shared",
                    producer_event_id=evt_a,
                ),
            ],
        )
        pq = ProvenanceQuery(run)
        consumers = pq.get_consumers(art_id)
        assert len(consumers) == 2
        assert evt_b in consumers
        assert evt_c in consumers


# ---------------------------------------------------------------------------
# Query tests: multi-hop traversal
# ---------------------------------------------------------------------------


class TestProvenanceQueryTraversal:
    """Tests for multi-hop upstream/downstream traversal."""

    def test_trace_upstream_linear(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_z = run.artifacts[2]
        upstream = pq.trace_upstream(art_z.artifact_id)
        # Z was produced by C, which consumed Y.
        # Y was produced by B, which consumed X.
        # X was produced by A, which had no inputs.
        assert run.artifacts[1].artifact_id in upstream  # Y
        assert run.artifacts[0].artifact_id in upstream  # X

    def test_trace_downstream_linear(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        downstream = pq.trace_downstream(art_x.artifact_id)
        assert run.artifacts[1].artifact_id in downstream  # Y
        assert run.artifacts[2].artifact_id in downstream  # Z

    def test_trace_upstream_empty_for_origin(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        upstream = pq.trace_upstream(art_x.artifact_id)
        assert upstream == []

    def test_trace_downstream_empty_for_terminal(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_z = run.artifacts[2]
        downstream = pq.trace_downstream(art_z.artifact_id)
        assert downstream == []

    def test_multimodal_upstream_traversal(self) -> None:
        """Image -> text -> tool -> output: trace output back to image."""
        run = _make_multimodal_run()
        pq = ProvenanceQuery(run)
        art_out = run.artifacts[3]  # final output
        upstream = pq.trace_upstream(art_out.artifact_id)
        # Should reach tool_output, text, and image
        art_ids = {a.artifact_id for a in run.artifacts}
        for art_id in upstream:
            assert art_id in art_ids
        assert run.artifacts[0].artifact_id in upstream  # IMAGE origin

    def test_multimodal_downstream_traversal(self) -> None:
        """Image -> text -> tool -> output: trace image to output."""
        run = _make_multimodal_run()
        pq = ProvenanceQuery(run)
        art_img = run.artifacts[0]
        downstream = pq.trace_downstream(art_img.artifact_id)
        assert run.artifacts[3].artifact_id in downstream  # final output

    def test_missing_artifact_reference(self) -> None:
        """Missing referenced artifact should not cause errors."""
        run_id = _make_run_id()
        now = datetime.now(tz=UTC)
        run = ExecutionRun(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            task_input="missing",
            events=[
                Event(
                    event_id=generate_event_id(),
                    run_id=run_id,
                    event_type=EventType.INPUT,
                    timestamp=now,
                    sequence_number=0,
                    input_artifact_ids=["art_does_not_exist"],
                ),
            ],
            artifacts=[],
        )
        pq = ProvenanceQuery(run)
        # Should not crash
        assert pq.get_producer("art_does_not_exist") is None
        # The event references it as input, so it is a recorded consumer
        consumers = pq.get_consumers("art_does_not_exist")
        assert len(consumers) == 1
        # Traversal on a missing (non-stored) artifact should not crash
        assert pq.trace_upstream("art_does_not_exist") == []
        assert pq.trace_downstream("art_does_not_exist") == []


class TestProvenanceQueryCycleProtection:
    """Tests for cycle safety in traversal."""

    def test_cycle_does_not_infinite_loop(self) -> None:
        """Construct a cycle: A -> B -> A. Traversal must terminate."""
        run_id = _make_run_id()
        now = datetime.now(tz=UTC)
        evt_a = generate_event_id()
        evt_b = generate_event_id()
        art_a = generate_artifact_id()
        art_b = generate_artifact_id()

        run = ExecutionRun(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            task_input="cycle",
            events=[
                Event(
                    event_id=evt_a,
                    run_id=run_id,
                    event_type=EventType.REASONING,
                    timestamp=now,
                    sequence_number=0,
                    input_artifact_ids=[art_b],
                    output_artifact_ids=[art_a],
                ),
                Event(
                    event_id=evt_b,
                    run_id=run_id,
                    event_type=EventType.REASONING,
                    timestamp=now,
                    sequence_number=1,
                    input_artifact_ids=[art_a],
                    output_artifact_ids=[art_b],
                ),
            ],
            artifacts=[
                Artifact(
                    artifact_id=art_a,
                    artifact_type=ArtifactType.TEXT,
                    value="a",
                    producer_event_id=evt_a,
                ),
                Artifact(
                    artifact_id=art_b,
                    artifact_type=ArtifactType.TEXT,
                    value="b",
                    producer_event_id=evt_b,
                ),
            ],
        )
        pq = ProvenanceQuery(run)
        # Should terminate without error
        upstream = pq.trace_upstream(art_a)
        assert isinstance(upstream, list)
        downstream = pq.trace_downstream(art_a)
        assert isinstance(downstream, list)


# ---------------------------------------------------------------------------
# Ancestor/descendant queries
# ---------------------------------------------------------------------------


class TestProvenanceQueryAncestry:
    """Tests for ancestor/descendant checks."""

    def test_is_ancestor_true(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        art_z = run.artifacts[2]
        assert pq.is_ancestor(art_x.artifact_id, art_z.artifact_id)

    def test_is_ancestor_false(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        art_z = run.artifacts[2]
        assert not pq.is_ancestor(art_z.artifact_id, art_x.artifact_id)

    def test_is_ancestor_self_is_false(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        assert not pq.is_ancestor(art_x.artifact_id, art_x.artifact_id)

    def test_is_descendant(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        art_z = run.artifacts[2]
        assert pq.is_descendant(art_z.artifact_id, art_x.artifact_id)

    def test_is_descendant_false(self) -> None:
        run = _make_linear_run()
        pq = ProvenanceQuery(run)
        art_x = run.artifacts[0]
        art_z = run.artifacts[2]
        assert not pq.is_descendant(art_x.artifact_id, art_z.artifact_id)


# ---------------------------------------------------------------------------
# Integration with Stage 3 tracing
# ---------------------------------------------------------------------------


class TestProvenanceFromTracedRun:
    """Test provenance extraction from a real Stage 3 traced run."""

    def test_provenance_from_traced_execution(self) -> None:
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:echo] Greet\n2. Summarise",
                "Summary done",
                "Final answer",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("Hello"))
        run = collector.get_run()

        pq = ProvenanceQuery(run)
        records = pq.records
        assert len(records) > 0

        # Should have PRODUCED and CONSUMED records
        rel_types = {r.relationship for r in records}
        assert RelationshipType.PRODUCED in rel_types
        assert RelationshipType.CONSUMED in rel_types

        # Every artifact should have a producer
        for art in run.artifacts:
            if art.producer_event_id:
                assert pq.get_producer(art.artifact_id) is not None

    def test_provenance_from_multimodal_traced_run(self) -> None:
        llm = MockLLMProvider(responses=["1. Process image", "Processed", "Done"])
        agent = Agent(llm=llm)
        traced = TracedAgent(agent)
        task = TaskInput(
            contents=[
                Content(modality=Modality.TEXT, data="Describe this"),
                Content(modality=Modality.IMAGE, data="s3://bucket/img.jpg"),
            ]
        )
        _, collector = traced.run(task)
        run = collector.get_run()

        pq = ProvenanceQuery(run)
        # Find the image artifact
        image_arts = [a for a in run.artifacts if a.artifact_type == ArtifactType.IMAGE]
        assert len(image_arts) == 1
        img = image_arts[0]
        assert img.reference == "s3://bucket/img.jpg"
        # Image should have a producer
        assert pq.get_producer(img.artifact_id) is not None


# ---------------------------------------------------------------------------
# Integration with Stage 4 storage
# ---------------------------------------------------------------------------


class TestProvenanceFromStoredRun:
    """Test provenance from a run loaded through Stage 4 storage."""

    def test_provenance_from_stored_run(self, tmp_path: Path) -> None:
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:echo] Say hi",
                "Echo done",
                "Final",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("test storage"))
        run = collector.get_run()

        # Store and reload
        store = FileTraceStore(tmp_path / "prov_test")
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None

        # Provenance from loaded run should match original
        pq_orig = ProvenanceQuery(run)
        pq_loaded = ProvenanceQuery(loaded)

        assert len(pq_orig.records) == len(pq_loaded.records)
        for r1, r2 in zip(pq_orig.records, pq_loaded.records, strict=True):
            assert r1.artifact_id == r2.artifact_id
            assert r1.event_id == r2.event_id
            assert r1.relationship == r2.relationship
