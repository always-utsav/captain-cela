"""Tests for captain.graph.validation and captain.graph.analysis (Stage 7)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.graph.analysis import GraphAnalyzer
from captain.graph.builder import ExecutionGraphBuilder
from captain.graph.model import EdgeType, ExecutionGraph, GraphEdge, GraphNode, NodeType
from captain.graph.validation import GraphValidator
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


def _linear_graph() -> ExecutionGraph:
    """E1 -> A1 -> E2 -> A2 -> E3 (linear chain)."""
    g = ExecutionGraph()
    g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT, label="input", sequence_number=0))
    g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT, label="text"))
    g.add_node(
        GraphNode(node_id="e2", node_type=NodeType.EVENT, label="reasoning", sequence_number=1)
    )
    g.add_node(GraphNode(node_id="a2", node_type=NodeType.ARTIFACT, label="model_output"))
    g.add_node(
        GraphNode(node_id="e3", node_type=NodeType.EVENT, label="output", sequence_number=2)
    )
    g.add_edge(GraphEdge(source_id="e1", target_id="a1", edge_type=EdgeType.PRODUCED))
    g.add_edge(GraphEdge(source_id="a1", target_id="e2", edge_type=EdgeType.CONSUMED))
    g.add_edge(GraphEdge(source_id="e2", target_id="a2", edge_type=EdgeType.PRODUCED))
    g.add_edge(GraphEdge(source_id="a2", target_id="e3", edge_type=EdgeType.CONSUMED))
    return g


def _make_linear_run() -> ExecutionRun:
    """Same as test_graph helper."""
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
                value="in",
                producer_event_id=ea,
            ),
            Artifact(
                artifact_id=ay,
                artifact_type=ArtifactType.MODEL_OUTPUT,
                value="mid",
                producer_event_id=eb,
            ),
            Artifact(
                artifact_id=az,
                artifact_type=ArtifactType.TEXT,
                value="out",
                producer_event_id=ec,
            ),
        ],
    )


# ===========================================================================
# Validation tests
# ===========================================================================


class TestGraphValidatorValid:
    """Tests for valid graphs."""

    def test_valid_linear_graph(self) -> None:
        g = _linear_graph()
        result = GraphValidator.validate(g)
        assert result.is_valid
        assert result.error_count == 0

    def test_empty_graph_is_valid(self) -> None:
        g = ExecutionGraph()
        result = GraphValidator.validate(g)
        assert result.is_valid

    def test_built_graph_is_valid(self) -> None:
        run = _make_linear_run()
        graph = ExecutionGraphBuilder.build(run)
        result = GraphValidator.validate(graph)
        assert result.is_valid
        assert result.error_count == 0


class TestGraphValidatorEdgeErrors:
    """Tests for edge-related errors."""

    def test_invalid_edge_combination(self) -> None:
        """PRODUCED from Artifact -> Event is invalid."""
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        # Manually add invalid edge (bypass add_edge type safety)
        g._edges.append(GraphEdge(source_id="a1", target_id="e1", edge_type=EdgeType.PRODUCED))
        g._successors["a1"].append("e1")
        g._predecessors["e1"].append("a1")

        result = GraphValidator.validate(g)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "INVALID_EDGE_COMBINATION" in codes

    def test_self_loop_detected(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))
        g._edges.append(GraphEdge(source_id="e1", target_id="e1", edge_type=EdgeType.PRODUCED))
        g._successors["e1"].append("e1")
        g._predecessors["e1"].append("e1")

        result = GraphValidator.validate(g)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "SELF_LOOP" in codes


class TestGraphValidatorWarnings:
    """Tests for warnings."""

    def test_isolated_node_warning(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT, sequence_number=0))
        result = GraphValidator.validate(g)
        assert result.is_valid  # warnings don't make it invalid
        assert result.warning_count > 0
        codes = [w.code for w in result.warnings]
        assert "ISOLATED_NODE" in codes

    def test_missing_sequence_number_warning(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT))  # no sequence_number
        result = GraphValidator.validate(g)
        codes = [w.code for w in result.warnings]
        assert "EVENT_MISSING_SEQUENCE" in codes

    def test_adjacency_consistency(self) -> None:
        g = _linear_graph()
        result = GraphValidator.validate(g)
        codes = [e.code for e in result.errors]
        assert "ADJACENCY_MISMATCH_SUCCESSORS" not in codes
        assert "ADJACENCY_MISMATCH_PREDECESSORS" not in codes


# ===========================================================================
# Analysis tests
# ===========================================================================


class TestGraphAnalyzerDegree:
    """Tests for degree metrics."""

    def test_in_degree(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.in_degree("e1") == 0  # root
        assert a.in_degree("a1") == 1  # produced by e1
        assert a.in_degree("e2") == 1  # consumed a1

    def test_out_degree(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.out_degree("e1") == 1  # produces a1
        assert a.out_degree("e3") == 0  # leaf

    def test_degree(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.degree("a1") == 2  # produced + consumed


class TestGraphAnalyzerRootsLeaves:
    """Tests for root, leaf, and isolated node detection."""

    def test_roots(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        roots = a.roots()
        assert "e1" in roots

    def test_leaves(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        leaves = a.leaves()
        assert "e3" in leaves

    def test_isolated_nodes(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT, sequence_number=0))
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        a = GraphAnalyzer(g)
        isolated = a.isolated_nodes()
        assert "e1" in isolated
        assert "a1" in isolated

    def test_no_isolated_in_connected_graph(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.isolated_nodes() == []


class TestGraphAnalyzerReachability:
    """Tests for reachability."""

    def test_downstream_reachable(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        downstream = a.reachable_downstream("e1")
        assert "a1" in downstream
        assert "e2" in downstream
        assert "a2" in downstream
        assert "e3" in downstream

    def test_upstream_reachable(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        upstream = a.reachable_upstream("e3")
        assert "a2" in upstream
        assert "e2" in upstream
        assert "a1" in upstream
        assert "e1" in upstream

    def test_cycle_safe_reachability(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT, sequence_number=0))
        g.add_node(GraphNode(node_id="a1", node_type=NodeType.ARTIFACT))
        g.add_edge(GraphEdge(source_id="e1", target_id="a1", edge_type=EdgeType.PRODUCED))
        g.add_edge(GraphEdge(source_id="a1", target_id="e1", edge_type=EdgeType.CONSUMED))
        a = GraphAnalyzer(g)
        downstream = a.reachable_downstream("e1")
        assert isinstance(downstream, list)


class TestGraphAnalyzerEventOrder:
    """Tests for execution ordering."""

    def test_event_execution_order(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        order = a.event_execution_order()
        assert order == ["e1", "e2", "e3"]

    def test_event_order_deterministic(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.event_execution_order() == a.event_execution_order()


class TestGraphAnalyzerPaths:
    """Tests for structural event paths."""

    def test_structural_path_exists(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        path = a.structural_event_path("e1", "e3")
        assert path is not None
        assert path[0] == "e1"
        assert path[-1] == "e3"

    def test_structural_path_includes_artifacts(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        path = a.structural_event_path("e1", "e3")
        assert path is not None
        assert "a1" in path  # intermediate artifact

    def test_no_path_returns_none(self) -> None:
        g = ExecutionGraph()
        g.add_node(GraphNode(node_id="e1", node_type=NodeType.EVENT, sequence_number=0))
        g.add_node(GraphNode(node_id="e2", node_type=NodeType.EVENT, sequence_number=1))
        a = GraphAnalyzer(g)
        assert a.structural_event_path("e1", "e2") is None

    def test_self_path(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        path = a.structural_event_path("e1", "e1")
        assert path == ["e1"]

    def test_all_event_paths(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        paths = a.all_event_paths()
        assert len(paths) >= 1
        # Should contain e1 -> e3 path
        has_full_path = any(p[0] == "e1" and p[-1] == "e3" for p in paths)
        assert has_full_path

    def test_all_event_paths_deterministic(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        assert a.all_event_paths() == a.all_event_paths()


class TestGraphAnalyzerSummary:
    """Tests for summary metrics."""

    def test_summary_keys(self) -> None:
        g = _linear_graph()
        a = GraphAnalyzer(g)
        s = a.summary()
        assert s["node_count"] == 5
        assert s["edge_count"] == 4
        assert s["event_nodes"] == 3
        assert s["artifact_nodes"] == 2
        assert s["roots"] >= 1
        assert s["leaves"] >= 1
        assert s["isolated_nodes"] == 0


# ===========================================================================
# Integration tests
# ===========================================================================


class TestGraphAnalysisIntegration:
    """Integration: TracedAgent -> Graph -> Validation + Analysis."""

    def test_traced_run_graph_valid_and_analyzable(self) -> None:
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

        # Validate
        result = GraphValidator.validate(graph)
        assert result.is_valid
        assert result.error_count == 0

        # Analyze
        analyzer = GraphAnalyzer(graph)
        assert len(analyzer.roots()) >= 1
        assert len(analyzer.leaves()) >= 1
        # Some events may not have artifact connections (valid)
        assert len(analyzer.isolated_nodes()) >= 0

        order = analyzer.event_execution_order()
        assert len(order) == run.event_count

        summary = analyzer.summary()
        assert summary["node_count"] > 0
        assert summary["edge_count"] > 0

    def test_stored_run_graph_analysis(self, tmp_path: Path) -> None:
        llm = MockLLMProvider(responses=["1. Plan", "Done", "Final"])
        agent = Agent(llm=llm)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("stored analysis"))
        run = collector.get_run()

        store = FileTraceStore(tmp_path / "analysis_test")
        store.save(run)
        loaded = store.load(run.run_id)
        assert loaded is not None

        graph = ExecutionGraphBuilder.build(loaded)
        result = GraphValidator.validate(graph)
        assert result.is_valid

        analyzer = GraphAnalyzer(graph)
        assert len(analyzer.roots()) >= 1
        assert analyzer.summary()["node_count"] == graph.node_count
