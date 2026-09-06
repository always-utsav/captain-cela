"""Tests for captain.explorer -- Trace Explorer (Stage 8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.explorer.app import create_app
from captain.graph.builder import ExecutionGraphBuilder
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent


@pytest.fixture()
def app(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Create a test Flask app with a temporary store."""
    application = create_app(store_dir=tmp_path / "test_traces")
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):  # type: ignore[no-untyped-def]
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Application tests
# ---------------------------------------------------------------------------


class TestExplorerApp:
    """Tests that the application starts and serves pages."""

    def test_app_creates(self, app) -> None:  # type: ignore[no-untyped-def]
        assert app is not None

    def test_index_page_serves(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/")
        assert response.status_code == 200
        assert b"CAPTAIN" in response.data

    def test_runs_list_empty(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/api/runs")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Demo execution tests
# ---------------------------------------------------------------------------


class TestExplorerDemo:
    """Tests that the demo execution produces a valid run."""

    def test_demo_creates_run(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post("/api/demo")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "run_id" in data
        assert data["status"] == "completed"
        assert data["event_count"] > 0
        assert data["artifact_count"] > 0

    def test_demo_run_appears_in_list(self, client) -> None:  # type: ignore[no-untyped-def]
        client.post("/api/demo")
        response = client.get("/api/runs")
        data = json.loads(response.data)
        assert len(data) >= 1

    def test_demo_run_is_loadable(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        response = client.get(f"/api/run/{demo['run_id']}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["run_id"] == demo["run_id"]
        assert "events" in data
        assert "artifacts" in data


# ---------------------------------------------------------------------------
# Graph data tests
# ---------------------------------------------------------------------------


class TestExplorerGraph:
    """Tests that graph data comes from ExecutionGraph."""

    def test_graph_endpoint(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        response = client.get(f"/api/graph/{demo['run_id']}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "graph" in data
        assert "validation" in data
        assert "analysis" in data
        assert data["validation"]["is_valid"] is True
        assert len(data["graph"]["nodes"]) > 0
        assert len(data["graph"]["edges"]) >= 0

    def test_graph_has_event_and_artifact_nodes(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        data = json.loads(client.get(f"/api/graph/{demo['run_id']}").data)
        groups = {n["group"] for n in data["graph"]["nodes"]}
        assert "event" in groups

    def test_graph_not_found(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/api/graph/run_nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Event detail tests
# ---------------------------------------------------------------------------


class TestExplorerEventDetail:
    """Tests that event details are correctly exposed."""

    def test_event_detail(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        run = json.loads(client.get(f"/api/run/{demo['run_id']}").data)
        evt = run["events"][0]
        response = client.get(f"/api/event/{demo['run_id']}/{evt['event_id']}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["event_id"] == evt["event_id"]
        assert "event_type" in data
        assert "sequence_number" in data
        assert "timestamp" in data
        assert "component" in data
        assert "payload" in data
        assert "input_artifact_ids" in data
        assert "output_artifact_ids" in data

    def test_event_not_found(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        response = client.get(f"/api/event/{demo['run_id']}/evt_nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Artifact detail tests
# ---------------------------------------------------------------------------


class TestExplorerArtifactDetail:
    """Tests that artifact details and provenance are correctly exposed."""

    def test_artifact_detail(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        run = json.loads(client.get(f"/api/run/{demo['run_id']}").data)
        if run["artifacts"]:
            art = run["artifacts"][0]
            response = client.get(f"/api/artifact/{demo['run_id']}/{art['artifact_id']}")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["artifact_id"] == art["artifact_id"]
            assert "artifact_type" in data
            assert "producer" in data
            assert "consumers" in data
            assert "upstream" in data
            assert "downstream" in data

    def test_artifact_not_found(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        response = client.get(f"/api/artifact/{demo['run_id']}/art_nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Provenance endpoint tests
# ---------------------------------------------------------------------------


class TestExplorerProvenance:
    """Tests that provenance information is correctly exposed."""

    def test_provenance_endpoint(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        run = json.loads(client.get(f"/api/run/{demo['run_id']}").data)
        if run["artifacts"]:
            art = run["artifacts"][0]
            response = client.get(f"/api/provenance/{demo['run_id']}/{art['artifact_id']}")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "artifact_id" in data
            assert "producer" in data
            assert "consumers" in data
            assert "upstream" in data
            assert "downstream" in data


# ---------------------------------------------------------------------------
# Real ExecutionRun integration test
# ---------------------------------------------------------------------------


class TestExplorerRealExecution:
    """Integration: real traced execution reaches the UI layer."""

    def test_real_execution_through_explorer(self, tmp_path: Path) -> None:
        """Verify a real traced run is accessible via explorer APIs."""
        # Create a traced run
        llm = MockLLMProvider(responses=["1. [TOOL:echo] Test\n2. Respond", "Echo done", "Answer"])
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("Integration test"))
        run = collector.get_run()

        # Store it
        store_dir = tmp_path / "integration"
        store = FileTraceStore(store_dir)
        store.save(run)

        # Create app pointing to same store
        app = create_app(store_dir=store_dir)
        client = app.test_client()

        # Verify run is listed
        runs = json.loads(client.get("/api/runs").data)
        assert any(r["run_id"] == run.run_id for r in runs)

        # Verify graph comes from ExecutionGraph
        graph_data = json.loads(client.get(f"/api/graph/{run.run_id}").data)
        expected_graph = ExecutionGraphBuilder.build(run)
        assert graph_data["analysis"]["node_count"] == expected_graph.node_count
        assert graph_data["analysis"]["edge_count"] == expected_graph.edge_count
