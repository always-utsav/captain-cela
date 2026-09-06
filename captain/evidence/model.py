"""CELA evidence layer — canonical evidence models.

The evidence layer provides the primary CELA research
abstraction on top of existing CAPTAIN infrastructure.

An :class:`Evidence` object represents an identifiable unit
of information that participates in agent execution.  It
wraps/references an existing :class:`Artifact` rather than
duplicating its value.

An :class:`EvidenceTransformation` represents an information-
bearing link between two evidence objects — the core CELA
intervention unit (evidence-flow channel).

**Evidence ≠ Artifact.**

- Artifact: "What stored execution data exists?"
- Evidence: "What information unit is being reasoned about
  or transmitted?"

**An evidence-flow edge is NOT a causal claim.**

It means: "Evidence B was derived from / received information
from Evidence A according to hard provenance."

Causal meaning is only investigated through intervention and
counterfactual replay (Stage 14+).
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from pydantic import BaseModel, Field

from captain.models.ids import _is_deterministic, _next_deterministic_id

# ===================================================================
# Evidence ID generation
# ===================================================================


def generate_evidence_id() -> str:
    """Generate a unique evidence identifier with ``evi_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("evi_")
    return f"evi_{uuid.uuid4().hex}"


# ===================================================================
# Evidence modality
# ===================================================================


class EvidenceType(enum.StrEnum):
    """Classification of evidence by role in agent execution.

    Extensible — new types added only when required by
    experiments, not for theoretical completeness.
    """

    TEXT = "text"
    IMAGE = "image"
    STRUCTURED = "structured"
    MEMORY = "memory"
    TOOL_INPUT = "tool_input"
    TOOL_OUTPUT = "tool_output"
    MODEL_OUTPUT = "model_output"


# ===================================================================
# Transformation type
# ===================================================================


class TransformationType(enum.StrEnum):
    """Classification of evidence transformations.

    Each value represents how information moved between
    two evidence objects during agent execution.
    """

    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    MEMORY_STORE = "memory_store"
    PLANNING_DERIVATION = "planning_derivation"
    TOOL_DISPATCH = "tool_dispatch"
    TOOL_RETURN = "tool_return"
    RESPONSE_DERIVATION = "response_derivation"


# ===================================================================
# Provenance method
# ===================================================================


class ProvenanceMethod(enum.StrEnum):
    """How an evidence relationship was established.

    Stage 12 supports HARD only.  SEMANTIC is reserved for
    a future optional extension (ablation A8 vs A9).
    """

    HARD = "hard"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


# ===================================================================
# Evidence
# ===================================================================


class Evidence(BaseModel):
    """An identifiable unit of information in agent execution.

    Evidence wraps/references an existing CAPTAIN
    :class:`~captain.models.artifacts.Artifact` without
    duplicating its value.

    Attributes:
        evidence_id: Unique ``evi_``-prefixed identifier.
        evidence_type: Classification from :class:`EvidenceType`.
        artifact_id: Reference to the underlying CAPTAIN artifact
            (``None`` for event-payload-only evidence).
        creation_event_id: The event that produced this evidence.
        parent_evidence_ids: Evidence objects this was derived from.
        sequence_number: Temporal position in execution trace.
        metadata: Additional context.
    """

    evidence_id: str = Field(default_factory=generate_evidence_id)
    evidence_type: EvidenceType
    artifact_id: str | None = None
    creation_event_id: str
    parent_evidence_ids: list[str] = Field(default_factory=list)
    sequence_number: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Evidence transformation (evidence-flow edge)
# ===================================================================


class EvidenceTransformation(BaseModel):
    """An information-bearing link between two evidence objects.

    This is the primary CELA intervention unit — the
    evidence-flow channel.

    **This is NOT a causal claim.** It records that evidence
    B was derived from / received information from evidence A
    according to hard provenance.

    Attributes:
        source_evidence_id: Upstream evidence.
        target_evidence_id: Downstream evidence.
        transformation_type: How information was transformed.
        event_id: Execution event that mediated the transfer.
        provenance_method: How this edge was established.
        confidence: Certainty of the relationship (1.0 = hard).
        sequence_number: Temporal position of the mediating event.
        metadata: Additional context.
    """

    source_evidence_id: str
    target_evidence_id: str
    transformation_type: TransformationType
    event_id: str
    provenance_method: ProvenanceMethod = ProvenanceMethod.HARD
    confidence: float = 1.0
    sequence_number: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
