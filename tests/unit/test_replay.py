"""Tests for captain.replay -- Counterfactual Replay Engine (Stage 10)."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.graph.builder import ExecutionGraphBuilder
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.intervention.validation import InterventionValidator
from captain.models.enums import EventType
from captain.provenance.extractor import ProvenanceExtractor
from captain.replay.engine import (
    CounterfactualReplayEngine,
    ReplayStatus,
)
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------
# Helper: run a deterministic baseline
# ---------------------------------------------------------------


def _baseline() -> tuple[object, object]:
    """Run a deterministic baseline and return (run, registry)."""
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
    return collector.get_run(), reg


# ---------------------------------------------------------------
# 1. No-intervention sanity replay
# ---------------------------------------------------------------


class TestNoInterventionReplay:
    """Replay with empty InterventionSet."""

    def test_empty_set_replays(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None
        assert cf.run_id != run.run_id
        assert cf.parent_run_id == run.run_id
        assert cf.event_count == run.event_count

    def test_deterministic_content(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        # Same task input
        assert cf.task_input == run.task_input
        # Same output content
        out_b = _output_content(run)
        out_c = _output_content(cf)
        assert out_b == out_c


# ---------------------------------------------------------------
# 2. TOOL_RESULT_OVERRIDE -- core scientific test
# ---------------------------------------------------------------


class TestToolResultOverride:
    """Override a tool result and verify downstream change."""

    def test_override_changes_downstream(self) -> None:
        run, reg = _baseline()
        # Find TOOL_RESULT event
        tr = _find_event(run, EventType.TOOL_RESULT)
        assert tr is not None

        intv = Intervention(
            intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=tr.event_id,
            replacement_value="99",
            description="What if calculator returned 99?",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None

        # --- downstream observable differences ---
        # Tool output artifact differs
        b_tool = _tool_output_value(run)
        c_tool = _tool_output_value(cf)
        assert c_tool == "99"
        assert b_tool != c_tool

        # TOOL_RESULT event payload differs
        b_tr = _find_event(run, EventType.TOOL_RESULT)
        c_tr = _find_event(cf, EventType.TOOL_RESULT)
        assert b_tr is not None and c_tr is not None
        assert c_tr.payload["result"] == "99"
        assert b_tr.payload["result"] != "99"

        # Memory write for step_0 differs
        b_mem = _step_memory(run, 0)
        c_mem = _step_memory(cf, 0)
        assert c_mem == "99"
        assert b_mem != c_mem

    def test_baseline_unchanged(self) -> None:
        run, reg = _baseline()
        original = run.model_dump_json()
        tr = _find_event(run, EventType.TOOL_RESULT)
        assert tr is not None
        intv = Intervention(
            intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=tr.event_id,
            replacement_value="99",
        )
        CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert run.model_dump_json() == original


# ---------------------------------------------------------------
# 3. ARTIFACT_REPLACEMENT
# ---------------------------------------------------------------


class TestArtifactReplacement:
    """Replace an artifact value and verify it propagates."""

    def test_replace_tool_output(self) -> None:
        run, reg = _baseline()
        # Find TOOL_OUTPUT artifact
        from captain.models.enums import ArtifactType

        tool_art = next(
            (a for a in run.artifacts if a.artifact_type == ArtifactType.TOOL_OUTPUT),
            None,
        )
        assert tool_art is not None

        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=tool_art.artifact_id,
            replacement_value="77",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None
        assert _tool_output_value(cf) == "77"

    def test_replace_input_text(self) -> None:
        run, reg = _baseline()
        from captain.models.enums import ArtifactType

        inp_art = next(
            (
                a
                for a in run.artifacts
                if a.artifact_type == ArtifactType.TEXT and a.value == run.task_input
            ),
            None,
        )
        if inp_art is None:
            return
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=inp_art.artifact_id,
            replacement_value="What is 8 times 9?",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None
        assert cf.task_input == "What is 8 times 9?"


# ---------------------------------------------------------------
# 4. EVENT_OUTPUT_OVERRIDE
# ---------------------------------------------------------------


class TestEventOutputOverride:
    """Override an event's output."""

    def test_override_reasoning(self) -> None:
        run, reg = _baseline()
        re = _find_event(run, EventType.REASONING)
        if re is None:
            return
        intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=re.event_id,
            replacement_value="Overridden reasoning",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None
        c_re = _find_event(cf, EventType.REASONING)
        assert c_re is not None
        assert "Overridden" in c_re.payload.get("result", "")


# ---------------------------------------------------------------
# 5. EVENT_DISABLE
# ---------------------------------------------------------------


class TestEventDisable:
    """Disable an event and verify behaviour."""

    def test_disable_tool_step(self) -> None:
        run, reg = _baseline()
        tc = _find_event(run, EventType.TOOL_CALL)
        assert tc is not None
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=tc.event_id,
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None
        # No TOOL_CALL events in counterfactual
        tc_cf = [e for e in cf.events if e.event_type == EventType.TOOL_CALL]
        assert len(tc_cf) == 0

    def test_disable_essential_rejected(self) -> None:
        run, reg = _baseline()
        ie = _find_event(run, EventType.INPUT)
        assert ie is not None
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=ie.event_id,
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.REJECTED
        assert "essential" in (r.rejection_reason or "")


# ---------------------------------------------------------------
# 6. Invalid / rejected interventions
# ---------------------------------------------------------------


class TestRejectedInterventions:
    """Interventions that should be rejected."""

    def test_invalid_target(self) -> None:
        run, reg = _baseline()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id="evt_nonexistent",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.REJECTED

    def test_baseline_mismatch(self) -> None:
        run, reg = _baseline()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id="run_wrong",
            target_id="evt_x",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.REJECTED

    def test_conflicting_set(self) -> None:
        run, reg = _baseline()
        tr = _find_event(run, EventType.TOOL_RESULT)
        assert tr is not None
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=(InterventionType.TOOL_RESULT_OVERRIDE),
                baseline_run_id=run.run_id,
                target_id=tr.event_id,
                replacement_value="A",
            )
        )
        iset.add(
            Intervention(
                intervention_type=(InterventionType.TOOL_RESULT_OVERRIDE),
                baseline_run_id=run.run_id,
                target_id=tr.event_id,
                replacement_value="B",
            )
        )
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        assert r.status == ReplayStatus.REJECTED


# ---------------------------------------------------------------
# 7. Fresh IDs and parent linkage
# ---------------------------------------------------------------


class TestIdentity:
    """Counterfactual must have fresh IDs."""

    def test_fresh_run_id(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        assert cf.run_id != run.run_id
        assert cf.run_id.startswith("run_")

    def test_parent_linkage(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        assert cf.parent_run_id == run.run_id

    def test_fresh_event_ids(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        b_ids = {e.event_id for e in run.events}
        c_ids = {e.event_id for e in cf.events}
        assert b_ids.isdisjoint(c_ids)

    def test_fresh_artifact_ids(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        b_ids = {a.artifact_id for a in run.artifacts}
        c_ids = {a.artifact_id for a in cf.artifacts}
        assert b_ids.isdisjoint(c_ids)


# ---------------------------------------------------------------
# 8. Metadata
# ---------------------------------------------------------------


class TestReplayMetadata:
    """Counterfactual run carries replay metadata."""

    def test_metadata_present(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        assert cf.metadata["is_counterfactual"] is True
        assert cf.metadata["baseline_run_id"] == run.run_id


# ---------------------------------------------------------------
# 9. Storage compatibility
# ---------------------------------------------------------------


class TestStorageCompat:
    """Counterfactual run works with FileTraceStore."""

    def test_store_and_load(self, tmp_path: object) -> None:
        from pathlib import Path

        run, reg = _baseline()
        tr = _find_event(run, EventType.TOOL_RESULT)
        assert tr is not None
        intv = Intervention(
            intervention_type=(InterventionType.TOOL_RESULT_OVERRIDE),
            baseline_run_id=run.run_id,
            target_id=tr.event_id,
            replacement_value="99",
        )
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None

        store = FileTraceStore(base_dir=Path(str(tmp_path)))
        store.save(cf)
        loaded = store.load(cf.run_id)
        assert loaded is not None
        assert loaded.run_id == cf.run_id
        assert loaded.parent_run_id == run.run_id


# ---------------------------------------------------------------
# 10. Provenance compatibility
# ---------------------------------------------------------------


class TestProvenanceCompat:
    """ProvenanceExtractor works on counterfactual runs."""

    def test_provenance(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        pe = ProvenanceExtractor(cf)
        pe.extract()  # Should not raise


# ---------------------------------------------------------------
# 11. Graph compatibility
# ---------------------------------------------------------------


class TestGraphCompat:
    """ExecutionGraphBuilder works on counterfactual runs."""

    def test_graph(self) -> None:
        run, reg = _baseline()
        iset = InterventionSet(baseline_run_id=run.run_id)
        r = CounterfactualReplayEngine.replay(run, iset, tool_registry=reg)
        cf = r.counterfactual_run
        assert cf is not None
        graph = ExecutionGraphBuilder.build(cf)
        assert graph.node_count > 0
        assert graph.edge_count > 0


# ---------------------------------------------------------------
# 12. End-to-end pipeline
# ---------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: trace -> store -> intervene -> replay ->
    store -> provenance -> graph."""

    def test_full_pipeline(self, tmp_path: object) -> None:
        from pathlib import Path

        store = FileTraceStore(base_dir=Path(str(tmp_path)))

        # 1. Baseline execution
        run, reg = _baseline()
        store.save(run)

        # 2. Validate intervention
        tr = _find_event(run, EventType.TOOL_RESULT)
        assert tr is not None
        intv = Intervention(
            intervention_type=(InterventionType.TOOL_RESULT_OVERRIDE),
            baseline_run_id=run.run_id,
            target_id=tr.event_id,
            replacement_value="99",
        )
        val = InterventionValidator.validate(intv, run)
        assert val.is_valid

        # 3. Replay
        r = CounterfactualReplayEngine.replay(run, intv, tool_registry=reg)
        assert r.status == ReplayStatus.SUCCESS
        cf = r.counterfactual_run
        assert cf is not None

        # 4. Store counterfactual
        store.save(cf)
        loaded = store.load(cf.run_id)
        assert loaded is not None

        # 5. Provenance
        pe = ProvenanceExtractor(cf)
        pe.extract()

        # 6. Graph
        graph = ExecutionGraphBuilder.build(cf)
        assert graph.node_count > 0

        # 7. Verify downstream change
        assert _tool_output_value(cf) == "99"
        assert _tool_output_value(run) != "99"

        # 8. Both runs independently loadable
        b_loaded = store.load(run.run_id)
        c_loaded = store.load(cf.run_id)
        assert b_loaded is not None
        assert c_loaded is not None
        assert b_loaded.run_id != c_loaded.run_id


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _find_event(run: object, et: EventType) -> object | None:
    """Find first event of given type in run."""
    for e in run.events:  # type: ignore[attr-defined]
        if e.event_type == et:
            return e
    return None


def _output_content(run: object) -> str:
    """Extract OUTPUT event content."""
    evt = _find_event(run, EventType.OUTPUT)
    if evt:
        return evt.payload.get("content", "")  # type: ignore[union-attr]
    return ""


def _tool_output_value(run: object) -> str:
    """Extract first TOOL_OUTPUT artifact value."""
    from captain.models.enums import ArtifactType

    for a in run.artifacts:  # type: ignore[attr-defined]
        if a.artifact_type == ArtifactType.TOOL_OUTPUT:
            return str(a.value) if a.value else ""
    return ""


def _step_memory(run: object, idx: int) -> str:
    """Get memory write value for step idx."""
    for e in run.events:  # type: ignore[attr-defined]
        if e.event_type == EventType.MEMORY_WRITE and e.payload.get("key") == f"step_{idx}_result":
            return str(e.payload.get("value", ""))
    return ""
