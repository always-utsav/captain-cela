"""Integration test: Stage 3 traced execution -> Stage 4 store -> load."""

from __future__ import annotations

from pathlib import Path

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.models.enums import EventType, RunStatus
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent


class TestTraceStoreIntegration:
    """End-to-end: trace an agent run, store it, reload it."""

    def test_traced_run_store_load_round_trip(self, tmp_path: Path) -> None:
        """Full pipeline: Agent -> TracedAgent -> FileTraceStore -> load."""
        # --- Setup ---
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:echo] Greet the user\n2. Summarise",
                "Summary done",
                "Final response",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)

        # --- Trace ---
        _response, collector = traced.run(TaskInput.from_text("Hello world"))
        run = collector.get_run()

        # --- Store ---
        store = FileTraceStore(tmp_path / "integration")
        store.save(run)
        assert store.exists(run.run_id)

        # --- Load ---
        loaded = store.load(run.run_id)
        assert loaded is not None

        # --- Verify equivalence ---
        assert loaded.run_id == run.run_id
        assert loaded.status == RunStatus.COMPLETED
        assert loaded.task_input == "Hello world"
        assert loaded.event_count == run.event_count
        assert loaded.artifact_count == run.artifact_count

        # Events preserved
        for orig, rest in zip(run.events, loaded.events, strict=True):
            assert orig.event_id == rest.event_id
            assert orig.event_type == rest.event_type
            assert orig.sequence_number == rest.sequence_number
            assert orig.component == rest.component

        # Artifacts preserved
        for orig, rest in zip(run.artifacts, loaded.artifacts, strict=True):
            assert orig.artifact_id == rest.artifact_id
            assert orig.artifact_type == rest.artifact_type

        # Event types present
        event_types = {e.event_type for e in loaded.events}
        assert EventType.INPUT in event_types
        assert EventType.TOOL_CALL in event_types
        assert EventType.OUTPUT in event_types

    def test_traced_run_queryable_after_store(self, tmp_path: Path) -> None:
        """Stored traced runs should be queryable."""
        from captain.storage.query import TraceQuery

        llm = MockLLMProvider(
            responses=[
                "1. Think about it",
                "Thought done",
                "Final answer",
            ]
        )
        agent = Agent(llm=llm)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("Query test"))
        run = collector.get_run()

        store = FileTraceStore(tmp_path / "query_integration")
        store.save(run)

        # Query by status
        results = TraceQuery(store).by_status(RunStatus.COMPLETED).execute()
        assert len(results) == 1
        assert results[0].run_id == run.run_id

        # Query by event type
        results = TraceQuery(store).by_event_type(EventType.INPUT).execute()
        assert len(results) == 1
