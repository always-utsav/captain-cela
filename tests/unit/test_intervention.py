"""Tests for captain.intervention -- Counterfactual Intervention Model (Stage 9)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
    generate_intervention_id,
)
from captain.intervention.validation import InterventionValidator
from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.models.ids import generate_artifact_id, generate_event_id, generate_run_id
from captain.tracing.traced_agent import TracedAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run() -> ExecutionRun:
    """A run with events and artifacts suitable for intervention testing."""
    run_id = generate_run_id()
    now = datetime.now(tz=UTC)
    evt_input = generate_event_id()
    evt_tool_call = generate_event_id()
    evt_tool_result = generate_event_id()
    evt_output = generate_event_id()
    art_input = generate_artifact_id()
    art_tool_out = generate_artifact_id()
    art_output = generate_artifact_id()

    return ExecutionRun(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        task_input="test",
        events=[
            Event(
                event_id=evt_input,
                run_id=run_id,
                event_type=EventType.INPUT,
                timestamp=now,
                sequence_number=0,
                component="agent",
                output_artifact_ids=[art_input],
            ),
            Event(
                event_id=evt_tool_call,
                run_id=run_id,
                event_type=EventType.TOOL_CALL,
                timestamp=now,
                sequence_number=1,
                component="tool:calc",
                input_artifact_ids=[art_input],
            ),
            Event(
                event_id=evt_tool_result,
                run_id=run_id,
                event_type=EventType.TOOL_RESULT,
                timestamp=now,
                sequence_number=2,
                component="tool:calc",
                output_artifact_ids=[art_tool_out],
            ),
            Event(
                event_id=evt_output,
                run_id=run_id,
                event_type=EventType.OUTPUT,
                timestamp=now,
                sequence_number=3,
                component="response",
                input_artifact_ids=[art_tool_out],
                output_artifact_ids=[art_output],
            ),
        ],
        artifacts=[
            Artifact(
                artifact_id=art_input,
                artifact_type=ArtifactType.TEXT,
                value="What is 6*7?",
                producer_event_id=evt_input,
            ),
            Artifact(
                artifact_id=art_tool_out,
                artifact_type=ArtifactType.TOOL_OUTPUT,
                value="42",
                producer_event_id=evt_tool_result,
            ),
            Artifact(
                artifact_id=art_output,
                artifact_type=ArtifactType.TEXT,
                value="The answer is 42",
                producer_event_id=evt_output,
            ),
        ],
    )


# ===========================================================================
# Intervention model tests
# ===========================================================================


class TestInterventionModel:
    """Tests for the Intervention data model."""

    def test_create_artifact_replacement(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value="Modified input",
        )
        assert intv.intervention_id.startswith("intv_")
        assert intv.intervention_type == InterventionType.ARTIFACT_REPLACEMENT
        assert intv.baseline_run_id == run.run_id

    def test_create_tool_result_override(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[2].event_id,
            replacement_value="99",
        )
        assert intv.intervention_type == InterventionType.TOOL_RESULT_OVERRIDE

    def test_create_event_disable(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=run.events[1].event_id,
        )
        assert intv.replacement_value is None

    def test_create_event_output_override(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[3].event_id,
            replacement_value="Overridden output",
        )
        assert intv.intervention_type == InterventionType.EVENT_OUTPUT_OVERRIDE

    def test_unique_ids(self) -> None:
        id1 = generate_intervention_id()
        id2 = generate_intervention_id()
        assert id1 != id2
        assert id1.startswith("intv_")

    def test_description(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=run.events[0].event_id,
            description="Disable the input event for testing",
        )
        assert intv.description == "Disable the input event for testing"


# ===========================================================================
# InterventionSet tests
# ===========================================================================


class TestInterventionSet:
    """Tests for the InterventionSet collection."""

    def test_create_set(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        assert iset.count == 0

    def test_add_intervention(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id=run.run_id,
                target_id=run.events[0].event_id,
            )
        )
        assert iset.count == 1

    def test_get_targets(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id=run.run_id,
                target_id=run.events[1].event_id,
            )
        )
        iset.add(
            Intervention(
                intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                baseline_run_id=run.run_id,
                target_id=run.artifacts[0].artifact_id,
                replacement_value="new",
            )
        )
        targets = iset.get_targets()
        assert len(targets) == 2


# ===========================================================================
# Validation tests -- valid interventions
# ===========================================================================


class TestValidInterventions:
    """Tests for valid intervention validation."""

    def test_valid_artifact_replacement(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value="New value",
        )
        result = InterventionValidator.validate(intv, run)
        assert result.is_valid
        assert result.error_count == 0

    def test_valid_tool_result_override(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[2].event_id,
            replacement_value="99",
        )
        result = InterventionValidator.validate(intv, run)
        assert result.is_valid

    def test_valid_event_disable(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=run.events[1].event_id,
        )
        result = InterventionValidator.validate(intv, run)
        assert result.is_valid

    def test_valid_event_output_override(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[3].event_id,
            replacement_value="New output",
        )
        result = InterventionValidator.validate(intv, run)
        assert result.is_valid


# ===========================================================================
# Validation tests -- invalid interventions
# ===========================================================================


class TestInvalidInterventions:
    """Tests for invalid intervention detection."""

    def test_wrong_baseline_run(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id="run_wrong",
            target_id=run.events[0].event_id,
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "BASELINE_MISMATCH" in codes

    def test_invalid_artifact_target_format(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.events[0].event_id,  # evt_ not art_
            replacement_value="x",
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "INVALID_TARGET_FORMAT" in codes

    def test_invalid_event_target_format(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,  # art_ not evt_
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "INVALID_TARGET_FORMAT" in codes

    def test_nonexistent_artifact_target(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id="art_nonexistent",
            replacement_value="x",
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "TARGET_NOT_FOUND" in codes

    def test_nonexistent_event_target(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id="evt_nonexistent",
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "TARGET_NOT_FOUND" in codes

    def test_tool_result_override_wrong_event_type(self) -> None:
        run = _make_run()
        # Target the INPUT event (not TOOL_RESULT)
        intv = Intervention(
            intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[0].event_id,
            replacement_value="x",
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "WRONG_EVENT_TYPE" in codes

    def test_missing_replacement_value(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value=None,
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "MISSING_REPLACEMENT" in codes

    def test_event_output_override_missing_replacement(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=run.run_id,
            target_id=run.events[3].event_id,
            replacement_value=None,
        )
        result = InterventionValidator.validate(intv, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "MISSING_REPLACEMENT" in codes


# ===========================================================================
# InterventionSet validation tests
# ===========================================================================


class TestInterventionSetValidation:
    """Tests for intervention set validation."""

    def test_valid_set(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                baseline_run_id=run.run_id,
                target_id=run.artifacts[0].artifact_id,
                replacement_value="Modified",
            )
        )
        iset.add(
            Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id=run.run_id,
                target_id=run.events[1].event_id,
            )
        )
        result = InterventionValidator.validate_set(iset, run)
        assert result.is_valid

    def test_duplicate_targets_rejected(self) -> None:
        run = _make_run()
        target = run.artifacts[0].artifact_id
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                baseline_run_id=run.run_id,
                target_id=target,
                replacement_value="A",
            )
        )
        iset.add(
            Intervention(
                intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                baseline_run_id=run.run_id,
                target_id=target,
                replacement_value="B",
            )
        )
        result = InterventionValidator.validate_set(iset, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "DUPLICATE_TARGET" in codes

    def test_mixed_baseline_rejected(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(
            Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id="run_different",
                target_id=run.events[0].event_id,
            )
        )
        result = InterventionValidator.validate_set(iset, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "MIXED_BASELINE" in codes

    def test_set_baseline_mismatch(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id="run_wrong")
        result = InterventionValidator.validate_set(iset, run)
        assert not result.is_valid
        codes = [e.code for e in result.errors]
        assert "SET_BASELINE_MISMATCH" in codes

    def test_empty_set_valid(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        result = InterventionValidator.validate_set(iset, run)
        assert result.is_valid


# ===========================================================================
# Serialization tests
# ===========================================================================


class TestInterventionSerialization:
    """Tests for JSON round-trip serialization."""

    def test_intervention_round_trip(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value="New value",
            description="Test replacement",
        )
        json_str = intv.model_dump_json()
        restored = Intervention.model_validate_json(json_str)
        assert restored.intervention_id == intv.intervention_id
        assert restored.intervention_type == intv.intervention_type
        assert restored.baseline_run_id == intv.baseline_run_id
        assert restored.target_id == intv.target_id
        assert restored.replacement_value == intv.replacement_value
        assert restored.description == intv.description

    def test_intervention_set_round_trip(self) -> None:
        run = _make_run()
        iset = InterventionSet(
            baseline_run_id=run.run_id,
            description="Test set",
        )
        iset.add(
            Intervention(
                intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                baseline_run_id=run.run_id,
                target_id=run.artifacts[0].artifact_id,
                replacement_value="Replaced",
            )
        )
        iset.add(
            Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id=run.run_id,
                target_id=run.events[1].event_id,
            )
        )
        json_str = iset.model_dump_json()
        restored = InterventionSet.model_validate_json(json_str)
        assert restored.baseline_run_id == iset.baseline_run_id
        assert restored.count == iset.count
        assert restored.interventions[0].intervention_id == iset.interventions[0].intervention_id

    def test_json_is_valid_json(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.EVENT_DISABLE,
            baseline_run_id=run.run_id,
            target_id=run.events[0].event_id,
        )
        parsed = json.loads(intv.model_dump_json())
        assert parsed["intervention_type"] == "event_disable"
        assert parsed["baseline_run_id"] == run.run_id

    def test_dict_replacement_value(self) -> None:
        run = _make_run()
        intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value={"key": "value", "nested": [1, 2, 3]},
        )
        json_str = intv.model_dump_json()
        restored = Intervention.model_validate_json(json_str)
        assert restored.replacement_value == {"key": "value", "nested": [1, 2, 3]}


# ===========================================================================
# Immutability tests
# ===========================================================================


class TestInterventionImmutability:
    """Tests that interventions never mutate the original ExecutionRun."""

    def test_original_run_unchanged(self) -> None:
        run = _make_run()
        original_task = run.task_input
        original_event_count = run.event_count
        original_artifact_count = run.artifact_count
        original_art_value = run.artifacts[0].value

        # Create interventions targeting this run
        _intv = Intervention(
            intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
            baseline_run_id=run.run_id,
            target_id=run.artifacts[0].artifact_id,
            replacement_value="COMPLETELY DIFFERENT",
        )
        iset = InterventionSet(baseline_run_id=run.run_id)
        iset.add(_intv)
        InterventionValidator.validate_set(iset, run)

        # Original run must be unchanged
        assert run.task_input == original_task
        assert run.event_count == original_event_count
        assert run.artifact_count == original_artifact_count
        assert run.artifacts[0].value == original_art_value


# ===========================================================================
# Integration tests
# ===========================================================================


class TestInterventionIntegration:
    """Integration: real traced execution + intervention specification."""

    def test_intervention_on_traced_run(self) -> None:
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:calculator] Compute 2+2\n2. Respond",
                "Calculation done",
                "The answer is 4",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _, collector = traced.run(TaskInput.from_text("What is 2+2?"))
        run = collector.get_run()

        # Find a tool-result event
        tool_results = [e for e in run.events if e.event_type == EventType.TOOL_RESULT]

        if tool_results:
            intv = Intervention(
                intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
                baseline_run_id=run.run_id,
                target_id=tool_results[0].event_id,
                replacement_value="5",
                description="What if the tool returned 5 instead?",
            )
            result = InterventionValidator.validate(intv, run)
            assert result.is_valid

        # Create a full intervention set
        iset = InterventionSet(
            baseline_run_id=run.run_id,
            description="Counterfactual: different tool result",
        )
        if run.artifacts:
            iset.add(
                Intervention(
                    intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
                    baseline_run_id=run.run_id,
                    target_id=run.artifacts[0].artifact_id,
                    replacement_value="What is 3+3?",
                    description="Change the input question",
                )
            )
        result = InterventionValidator.validate_set(iset, run)
        assert result.is_valid

        # Verify serialization round-trip
        json_str = iset.model_dump_json()
        restored = InterventionSet.model_validate_json(json_str)
        assert restored.count == iset.count
        assert restored.baseline_run_id == run.run_id

    def test_deterministic_ordering(self) -> None:
        run = _make_run()
        iset = InterventionSet(baseline_run_id=run.run_id)
        ids = []
        for _i, evt in enumerate(run.events):
            intv = Intervention(
                intervention_type=InterventionType.EVENT_DISABLE,
                baseline_run_id=run.run_id,
                target_id=evt.event_id,
            )
            iset.add(intv)
            ids.append(intv.intervention_id)

        # Order should match insertion order
        for i, intv in enumerate(iset.interventions):
            assert intv.intervention_id == ids[i]
