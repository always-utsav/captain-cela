"""Canonical event model for CAPTAIN.

An :class:`Event` is the fundamental observable unit of an agent execution.
Events carry typed payloads, input/output artifact references (by ID), and
enough structural information for later stages to reconstruct execution
graphs and causal relationships.

Event ordering is determined by ``(sequence_number, timestamp)`` -- not by
UUID lexicographic order.  Sequence numbers are assigned by the collector
(future Stage 3) and must be non-negative.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from captain.models.enums import EventType
from captain.models.ids import generate_event_id


class Event(BaseModel):
    """Canonical representation of one observable execution event.

    Attributes:
        event_id: Globally unique identifier (``evt_`` prefix).
        run_id: ID of the :class:`~captain.models.execution.ExecutionRun`
            this event belongs to.
        event_type: Categorises the event.
        timestamp: Timezone-aware UTC time at which the event occurred.
        sequence_number: Zero-based ordinal within the run, ensuring
            deterministic ordering independent of timestamp granularity.
        parent_event_id: Optional ID of a parent event (e.g. a tool-call
            event is the parent of its tool-result event).
        component: Logical source component (e.g. ``"planner"``,
            ``"reasoner"``, ``"tool:calculator"``).
        input_artifact_ids: IDs of artifacts consumed by this event.
        output_artifact_ids: IDs of artifacts produced by this event.
        payload: Structured event-specific data.
        metadata: Additional key/value context.
    """

    event_id: str = Field(default_factory=generate_event_id)
    run_id: str
    event_type: EventType
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=__import__("datetime").UTC)
    )
    sequence_number: int = 0
    parent_event_id: str | None = None
    component: str = ""
    input_artifact_ids: list[str] = Field(default_factory=list)
    output_artifact_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- validators ---------------------------------------------------------

    @field_validator("event_id")
    @classmethod
    def _event_id_not_empty(cls, v: str) -> str:
        if not v:
            msg = "event_id must not be empty"
            raise ValueError(msg)
        return v

    @field_validator("run_id")
    @classmethod
    def _run_id_not_empty(cls, v: str) -> str:
        if not v:
            msg = "run_id must not be empty"
            raise ValueError(msg)
        return v

    @field_validator("sequence_number")
    @classmethod
    def _sequence_non_negative(cls, v: int) -> int:
        if v < 0:
            msg = "sequence_number must be non-negative"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _parent_not_self(self) -> Event:
        """An event cannot be its own parent."""
        if self.parent_event_id is not None and self.parent_event_id == self.event_id:
            msg = "parent_event_id must not equal event_id (self-reference)"
            raise ValueError(msg)
        return self

    @field_serializer("timestamp")
    @classmethod
    def _serialize_datetime(cls, v: datetime) -> str:
        return v.isoformat()
