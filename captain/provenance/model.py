"""Provenance relationship types for CAPTAIN.

Defines the taxonomy of information-lineage relationships between
events and artifacts.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class RelationshipType(enum.StrEnum):
    """Type of provenance relationship between events and artifacts.

    This is a small, stable taxonomy for information lineage:

    - ``PRODUCED``: an event created/produced an artifact.
    - ``CONSUMED``: an event consumed/read an artifact as input.
    - ``DERIVED``: an artifact was derived from another artifact
      through an intermediary event (multi-hop convenience).
    """

    PRODUCED = "produced"
    CONSUMED = "consumed"
    DERIVED = "derived"


class ProvenanceRecord(BaseModel):
    """A single provenance relationship.

    Captures one directional lineage link between an artifact and an
    event, or between two artifacts through an event.

    Attributes:
        artifact_id: The artifact involved in this relationship.
        event_id: The event involved (producer or consumer).
        relationship: The type of lineage link.
        source_artifact_id: For DERIVED relationships, the upstream
            artifact from which ``artifact_id`` was derived.
        metadata: Optional additional context.
    """

    artifact_id: str
    event_id: str
    relationship: RelationshipType
    source_artifact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
