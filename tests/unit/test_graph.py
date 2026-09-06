"""Tests for captain.graph -- ExecutionGraph, ExecutionGraphBuilder."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.graph.builder import ExecutionGraphBuilder
from captain.graph.model import EdgeType, ExecutionGraph, GraphEdge, GraphNode, NodeType
from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_artifact_id, generate_event_id, generate_run_id
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_linear_run() -> ExecutionRun:
    """A -> X -> B -> Y -> C -> Z  (3 events, 3 artifacts, linear chain)."""
    run_id = generate_run_id()
    now = datetime.now(tz=UTC)
    ea, eb, ec = generate_event_id(), generate_event_id(), generate_event_id()
    ax, ay, az = generate_artifact_id(), generate_artifact_id(), generate_artifact_id()

    return ExecutionRun(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        task_input="test",
        events=[
            Event(
                event_id=ea,
                run_id=run_id,
                event_type=EventType.INPUT,
                timestamp=now,
                sequence_number=0,
                component="agent",
                output_artifact_ids=[ax],
            ),
            Event(
                event_id=eb,
                run_id=run_id,
                event_type=EventType.REASONING,
                timestamp=now,
                sequence_number=1,
                component="reasoner",
                input_artifact_ids=[ax],
                output_artifact_ids=[ay],
            ),
            Event(
                event_id=ec,
                run_id=run_id,
                event_type=EventType.OUTPUT,
                timestamp=now,
                sequence_number=2,
                component="response",
                input_artifact_ids=[ay],
                output_artifact_ids=[az],
            ),
        ],
        artifacts=[
            Artifact(
                artifact_id=ax,
                artifact_type=ArtifactType.TEXT,
                value="input",
                producer_event_id=ea,
            ),
            Artifact(
                artifact_id=ay,
                artifact_type=ArtifactType.MODEL_OUTPUT,
                value="model",
                producer_event_id=eb,
            ),
            Artifact(
                artifact_id=az,
                artifact_type=ArtifactType.TEXT,
                value="output",
                producer_event_id=ec,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Graph model unit tests
# ---------------------------------------------------------------------------


class TestExecutionGraphModel:
    """Tests for the ExecutionGraph data structure itself."""

    def test_add_event_node(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT, label="input"))
        assert g.node_count == 1
        assert g.event_node_count == 1
        assert g.artifact_node_count == 0

    def test_add_artifact_node(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT, label="text"))
        assert g.node_count == 1
        assert g.artifact_node_count == 1

    def test_add_node_idempotent(self) -> None:
        g = ExecutionGraph()
        node = GraphNode(node_id="evt_1", node_type=NodeType.EVENT)
        g.add_node(node)
        g.add_node(node)
        assert g.node_count == 1

    def test_add_edge(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        assert g.edge_count == 1

    def test_edge_to_unknown_node_ignored(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_edge(
            GraphEdge(source_id="evt_1", target_id="art_missing", edge_type=EdgeType.PRODUCED)
        )
        assert g.edge_count == 0

    def test_get_event_node(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT, label="input"))
        assert g.get_event_node("evt_1") is not None
        assert g.get_event_node("art_1") is None

    def test_get_artifact_node(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT, label="text"))
        assert g.get_artifact_node("art_1") is not None
        assert g.get_artifact_node("evt_1") is None

    def test_successors_predecessors(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        assert g.get_successors("evt_1") == ["art_1"]
        assert g.get_predecessors("art_1") == ["evt_1"]
        assert g.get_successors("art_1") == []
        assert g.get_predecessors("evt_1") == []

    def test_get_event_artifacts(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT))
        g.add_node(GraphNode(node_id="art_2", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="art_2", target_id="evt_1", edge_type=EdgeType.CONSUMED))
        arts = g.get_event_artifacts("evt_1")
        assert "art_1" in arts
        assert "art_2" in arts

    def test_get_artifact_events(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="evt_2", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="art_1", target_id="evt_2", edge_type=EdgeType.CONSUMED))
        evts = g.get_artifact_events("art_1")
        assert "evt_1" in evts
        assert "evt_2" in evts

    def test_get_event_events(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="evt_2", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="art_1", target_id="evt_2", edge_type=EdgeType.CONSUMED))
        assert g.get_event_events("evt_1") == ["evt_2"]
        assert g.get_event_events("evt_2") == ["evt_1"]


# ---------------------------------------------------------------------------
# Graph traversal tests
# ---------------------------------------------------------------------------


class TestExecutionGraphTraversal:
    """Tests for BFS upstream/downstream traversal."""

    def test_downstream_linear(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        g.add_node(GraphNode(node_id="e2", node_type=NodeType.EVENT))
        g.add_edge(GraphEdge(source_id="e1", target_id="a1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="a1", target_id="e2", edge_type=EdgeType.CONSUMED))
        downstream = g.traverse_downstream("e1")
        assert "a1" in downstream
        assert "e2" in downstream

    def test_upstream_linear(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        g.add_node(GraphNode(node_id="e2", node_type=NodeType.EVENT))
        g.add_edge(GraphEdge(source_id="e1", target_id="a1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="a1", target_id="e2", edge_type=EdgeType.CONSUMED))
        upstream = g.traverse_upstream("e2")
        assert "a1" in upstream
        assert "e1" in upstream

    def test_cycle_safe_traversal(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="e1", target_id="a1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="a1", target_id="e1", edge_type=EdgeType.CONSUMED))
        # Should terminate
        downstream = g.traverse_downstream("e1")
        assert isinstance(downstream, list)
        upstream = g.traverse_upstream("e1")
        assert isinstance(upstream, list)

    def test_traversal_empty_for_isolated_node(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        assert g.traverse_downstream("e1") == []
        assert g.traverse_upstream("e1") == []


# ---------------------------------------------------------------------------
# Graph export tests
# ---------------------------------------------------------------------------


class TestExecutionGraphExport:
    """Tests for JSON-compatible export."""

    def test_to_dict_structure(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT, label="input"))
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT, label="text"))
        g.add_edge(GraphEdge(source_id="evt_1", target_id="art_1", edge_type=EdgeType.PRODUCED))
        d = g.to_dict()
        assert d["node_count"] == 2
        assert d["edge_count"] == 1
        assert len(d["nodes"]) == 2
        assert len(d["edges"]) == 1

    def test_to_dict_is_json_serializable(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="evt_1", node_type=NodeType.EVENT))
        d = g.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["node_count"] == 1

    def test_nodes_sorted_events_first(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="art_1", node_type=NodeType.ARTIFACT, label="text"))
        g.add_node(
            GraphNode(node_id="evt_1", node_type=NodeType.EVENT, label="input", sequence_number=0)
        )
        d = g.to_dict()
        assert d["nodes"][0]["node_id"] == "evt_1"
        assert d["nodes"][1]["node_id"] == "art_1"


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------


class TestExecutionGraphBuilder:
    """Tests for ExecutionGraphBuilder.build()."""

    def test_build_linear_run(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        assert graph.event_node_count == 3
        assert graph.artifact_node_count == 3
        assert graph.edge_count > 0

    def test_event_nodes_have_sequence_numbers(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        for event in run.events:
            node = graph.get_event_node(event.event_id)
            assert node is not None
            assert node.sequence_number == event.sequence_number

    def test_artifact_nodes_have_correct_labels(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        for art in run.artifacts:
            node = graph.get_artifact_node(art.artifact_id)
            assert node is not None
            assert node.label == art.artifact_type.value

    def test_produced_edges_direction(self) -> None:
        """PRODUCED: Event -> Artifact."""
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        evt_a = run.events[0]
        art_x = run.artifacts[0]
        edges = graph.get_edges_from(evt_a.event_id)
        produced = [e for e in edges if e.edge_type == EdgeType.PRODUCED]
        assert len(produced) == 1
        assert produced[0].target_id == art_x.artifact_id

    def test_consumed_edges_direction(self) -> None:
        """CONSUMED: Artifact -> Event."""
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        art_x = run.artifacts[0]
        evt_b = run.events[1]
        edges = graph.get_edges_from(art_x.artifact_id)
        consumed = [e for e in edges if e.edge_type == EdgeType.CONSUMED]
        assert len(consumed) == 1
        assert consumed[0].target_id == evt_b.event_id

    def test_deterministic_construction(self) -> None:
        run = _make_linear_run()
        g1 = ExecutionGraphBuilder.build(run)
        g2 = ExecutionGraphBuilder.build(run)
        assert g1.node_count == g2.node_count
        assert g1.edge_count == g2.edge_count
        assert g1.to_dict()["edges"] == g2.to_dict()["edges"]

    def test_downstream_traversal_through_graph(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        evt_a = run.events[0]
        downstream = graph.traverse_downstream(evt_a.event_id)
        # Should reach all downstream artifacts and events
        assert run.artifacts[0].artifact_id in downstream
        assert run.events[1].event_id in downstream
        assert run.artifacts[2].artifact_id in downstream

    def test_upstream_traversal_through_graph(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        evt_c = run.events[2]
        upstream = graph.traverse_upstream(evt_c.event_id)
        assert run.artifacts[1].artifact_id in upstream
        assert run.events[0].event_id in upstream

    def test_empty_run(self) -> None:
        run = ExecutionRun(
            run_id=generate_run_id(),
            status=RunStatus.COMPLETED,
            task_input="empty",
        )
        graph = ExecutionGraphBuilder.build(run)
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_missing_artifact_reference_safe(self) -> None:
        """Events referencing non-existent artifacts should not create ghost nodes."""
        run_id = generate_run_id()
        now = datetime.now(tz=UTC)
        run = ExecutionRun(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            task_input="missing ref",
            events=[
                Event(
                    event_id=generate_event_id(),
                    run_id=run_id,
                    event_type=EventType.INPUT,
                    timestamp=now,
                    sequence_number=0,
                    output_artifact_ids=["art_ghost"],
                ),
            ],
            artifacts=[],
        )
        graph = ExecutionGraphBuilder.build(run)
        assert graph.event_node_count == 1
        assert graph.artifact_node_count == 0
        # Edge to ghost artifact should be dropped
        assert graph.edge_count == 0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestGraphIntegration:
    """Integration: TracedAgent -> ExecutionGraph."""

    def test_traced_run_to_graph(self) -> None:
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:echo] Greet\n2. Summarise",
                "Summary",
                "Final answer",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("Hello"))
        run = collector.get_run()

        graph = ExecutionGraphBuilder.build(run)

        # Should have event nodes for each traced event
        assert graph.event_node_count == run.event_count
        assert graph.artifact_node_count == run.artifact_count
        assert graph.edge_count > 0

        # Every event node should be findable
        for event in run.events:
            node = graph.get_event_node(event.event_id)
            assert node is not None
            assert node.label == event.event_type.value

        # Every artifact node should be findable
        for art in run.artifacts:
            node = graph.get_artifact_node(art.artifact_id)
            assert node is not None

        # Graph should be JSON-exportable
        d = graph.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["node_count"] == graph.node_count

    def test_stored_run_to_graph(self, tmp_path: Path) -> None:
        """Graph from a run loaded through Stage 4 storage."""
        llm = MockLLMProvider(responses=["1. Think", "Done", "Final"])
        agent = Agent(llm=llm)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("stored graph"))
        run = collector.get_run()

        store = FileTraceStore(tmp_path / "graph_test")
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None

        g_orig = ExecutionGraphBuilder.build(run)
        g_loaded = ExecutionGraphBuilder.build(loaded)

        assert g_orig.node_count == g_loaded.node_count
        assert g_orig.edge_count == g_loaded.edge_count
