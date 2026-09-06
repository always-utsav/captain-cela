"""Canonical artifact model for CAPTAIN.

An :class:`Artifact` represents a piece of data produced, consumed, or
transformed during an agent execution.  Artifacts are the nodes that carry
information between events; the future graph builder will use artifact IDs
and producer/consumer event IDs to reconstruct data-flow edges.

Large binary content (images, files) is represented **by reference** --
the ``reference`` field holds a URI or path, not the actual bytes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from captain.models.enums import ArtifactType
from captain.models.ids import generate_artifact_id


class Artifact(BaseModel):
    """Canonical representation of data produced or consumed during execution.

    Attributes:
        artifact_id: Globally unique identifier (``art_`` prefix).
        artifact_type: The kind/modality of this artifact.
        value: Inline textual or structured value (for small payloads).
        reference: URI/path for external or large content.
        producer_event_id: ID of the event that produced this artifact.
        metadata: Additional key/value context.
        created_at: Timezone-aware UTC creation timestamp.
    """

    artifact_id: str = Field(default_factory=generate_artifact_id)
    artifact_type: ArtifactType
    value: str | dict[str, Any] | list[Any] | None = None
    reference: str | None = None
    producer_event_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=__import__("datetime").UTC)
    )

    # --- validators ---------------------------------------------------------

    @field_validator("artifact_id")
    @classmethod
    def _id_not_empty(cls, v: str) -> str:
        if not v:
            msg = "artifact_id must not be empty"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _require_value_or_reference(self) -> Artifact:
        """At least one of value or reference should typically be present.

        We do not raise here -- an artifact may be a pure placeholder at
        creation time -- but we ensure the ID prefix is correct.
        """
        if not self.artifact_id.startswith("art_"):
            msg = f"artifact_id must start with 'art_', got '{self.artifact_id}'"
            raise ValueError(msg)
        return self

    @field_serializer("created_at")
    @classmethod
    def _serialize_datetime(cls, v: datetime) -> str:
        return v.isoformat()
