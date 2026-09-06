"""Tests for captain.models.events -- Event canonical model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from captain.models.enums import EventType
from captain.models.events import Event
from captain.models.ids import generate_artifact_id, generate_event_id, generate_run_id


class TestEvent:
    """Tests for the Event model."""

    def test_construction(self) -> None:
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.INPUT)
        assert evt.event_id.startswith("evt_")
        assert evt.run_id == rid
        assert evt.event_type == EventType.INPUT
        assert evt.sequence_number == 0

    def test_explicit_event_id(self) -> None:
        eid = generate_event_id()
        rid = generate_run_id()
        evt = Event(event_id=eid, run_id=rid, event_type=EventType.REASONING)
        assert evt.event_id == eid

    def test_timestamp_is_utc(self) -> None:
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.OUTPUT)
        assert evt.timestamp.tzinfo is not None

    def test_explicit_timestamp(self) -> None:
        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.PLANNING, timestamp=ts)
        assert evt.timestamp == ts

    def test_sequence_number_default(self) -> None:
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.INPUT)
        assert evt.sequence_number == 0

    def test_negative_sequence_number_raises(self) -> None:
        rid = generate_run_id()
        with pytest.raises(ValueError, match="non-negative"):
            Event(run_id=rid, event_type=EventType.INPUT, sequence_number=-1)

    def test_empty_event_id_raises(self) -> None:
        rid = generate_run_id()
        with pytest.raises(ValueError, match="empty"):
            Event(event_id="", run_id=rid, event_type=EventType.INPUT)

    def test_empty_run_id_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Event(run_id="", event_type=EventType.INPUT)

    def test_self_referencing_parent_raises(self) -> None:
        eid = generate_event_id()
        rid = generate_run_id()
        with pytest.raises(ValueError, match="self-reference"):
            Event(event_id=eid, run_id=rid, event_type=EventType.TOOL_CALL, parent_event_id=eid)

    def test_valid_parent_event_id(self) -> None:
        parent_id = generate_event_id()
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.TOOL_RESULT, parent_event_id=parent_id)
        assert evt.parent_event_id == parent_id

    def test_component_field(self) -> None:
        rid = generate_run_id()
        evt = Event(run_id=rid, event_type=EventType.TOOL_CALL, component="tool:calculator")
        assert evt.component == "tool:calculator"

    def test_input_output_artifact_ids(self) -> None:
        rid = generate_run_id()
        in_id = generate_artifact_id()
        out_id = generate_artifact_id()
        evt = Event(
            run_id=rid,
            event_type=EventType.REASONING,
            input_artifact_ids=[in_id],
            output_artifact_ids=[out_id],
        )
        assert in_id in evt.input_artifact_ids
        assert out_id in evt.output_artifact_ids

    def test_payload(self) -> None:
        rid = generate_run_id()
        evt = Event(
            run_id=rid,
            event_type=EventType.MODEL_CALL,
            payload={"model": "gpt-4", "prompt": "hello"},
        )
        assert evt.payload["model"] == "gpt-4"

    def test_metadata(self) -> None:
        rid = generate_run_id()
        evt = Event(
            run_id=rid,
            event_type=EventType.ERROR,
            metadata={"error_code": "TIMEOUT"},
        )
        assert evt.metadata["error_code"] == "TIMEOUT"

    def test_ordering_by_sequence_number(self) -> None:
        """Events can be sorted by sequence_number for deterministic ordering."""
        rid = generate_run_id()
        e0 = Event(run_id=rid, event_type=EventType.INPUT, sequence_number=0)
        e1 = Event(run_id=rid, event_type=EventType.PLANNING, sequence_number=1)
        e2 = Event(run_id=rid, event_type=EventType.OUTPUT, sequence_number=2)
        events = [e2, e0, e1]
        sorted_events = sorted(events, key=lambda e: e.sequence_number)
        assert [e.sequence_number for e in sorted_events] == [0, 1, 2]
