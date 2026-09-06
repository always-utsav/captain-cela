"""CELA failure & intervention layer — canonical models.

Provides failure representation, failure-relevant evidence
region extraction, candidate evidence-flow channel selection,
and evidence-channel intervention specification.

**Critical research boundary:**

- Failure relevance ≠ causal effect.
- A candidate score is NOT a causal probability.
- Causal responsibility requires intervention + replay +
  outcome measurement (Stage 14).

This module answers:
    "Given a failed execution, which evidence-flow channels
    are relevant candidates for intervention?"

It does NOT answer:
    "Which channel is causally responsible?"
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from pydantic import BaseModel, Field

from captain.models.ids import _is_deterministic, _next_deterministic_id

# ===================================================================
# Failure ID generation
# ===================================================================


def generate_failure_id() -> str:
    """Generate a unique failure identifier with ``fail_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("fail_")
    return f"fail_{uuid.uuid4().hex}"


def generate_candidate_id() -> str:
    """Generate a unique candidate identifier with ``cand_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("cand_")
    return f"cand_{uuid.uuid4().hex}"


# ===================================================================
# Failure type
# ===================================================================


class FailureType(enum.StrEnum):
    """Classification of execution failures.

    Extensible — add types only when required by experiments.
    """

    TASK_FAILURE = "task_failure"
    WRONG_TOOL_USE = "wrong_tool_use"
    HALLUCINATED_CLAIM = "hallucinated_claim"
    UNSAFE_ACTION = "unsafe_action"


# ===================================================================
# Failure
# ===================================================================


class Failure(BaseModel):
    """Canonical failure representation.

    A failure is a label applied to an execution — either by a
    ground-truth oracle, a benchmark evaluator, or a human.

    It is NOT an automatic detection result unless explicitly
    marked as such in metadata.

    Attributes:
        failure_id: Unique ``fail_``-prefixed identifier.
        run_id: The ExecutionRun where failure was observed.
        failure_type: Classification from :class:`FailureType`.
        failure_event_id: Event where failure manifested (optional).
        failure_evidence_ids: Evidence associated with failure.
        sequence_number: Temporal position of failure manifestation.
        description: Human-readable explanation.
        metadata: Additional context (e.g. evaluator, ground truth).
    """

    failure_id: str = Field(default_factory=generate_failure_id)
    run_id: str
    failure_type: FailureType
    failure_event_id: str | None = None
    failure_evidence_ids: list[str] = Field(default_factory=list)
    sequence_number: int = 0
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Candidate evidence-flow channel
# ===================================================================


class Candidate(BaseModel):
    """A candidate evidence-flow channel for intervention.

    Represents a specific EvidenceTransformation edge that is
    structurally relevant to a failure and eligible for later
    counterfactual testing.

    **A candidate is NOT a causal claim.**

    The screening_score answers:
        "How useful is this edge as a candidate for later
        causal testing?"

    It does NOT answer:
        "How causally responsible is this edge?"

    Attributes:
        candidate_id: Unique ``cand_``-prefixed identifier.
        run_id: Baseline run identity.
        source_evidence_id: Upstream evidence in the channel.
        target_evidence_id: Downstream evidence in the channel.
        transformation_type: How information was transformed.
        event_id: Execution event that mediated the transfer.
        source_evidence_type: Modality of source evidence.
        target_evidence_type: Modality of target evidence.
        sequence_number: Temporal position.
        graph_distance: Hops from this edge to failure target.
        screening_score: Non-causal relevance score (higher = more relevant).
        provenance_method: How the edge was established.
        metadata: Additional context.
    """

    candidate_id: str = Field(default_factory=generate_candidate_id)
    run_id: str
    source_evidence_id: str
    target_evidence_id: str
    transformation_type: str
    event_id: str
    source_evidence_type: str = ""
    target_evidence_type: str = ""
    sequence_number: int = 0
    graph_distance: int = 0
    screening_score: float = 0.0
    provenance_method: str = "hard"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Evidence-channel intervention
# ===================================================================


class ChannelInterventionType(enum.StrEnum):
    """Types of evidence-channel interventions.

    BLOCK is the primary CELA intervention: do(C_e = ∅).
    """

    BLOCK = "block"


class ChannelIntervention(BaseModel):
    """Intervention targeting a specific evidence-flow channel.

    The target is the RELATIONSHIP (edge), not a single node:
        Evidence_A → Evidence_B

    Blocking A→B leaves C→B intact.

    **This is a specification only.** Execution happens in
    Stage 14 via CounterfactualReplayEngine.

    Attributes:
        intervention_id: Unique identifier.
        intervention_type: BLOCK (primary).
        baseline_run_id: The run being analyzed.
        source_evidence_id: Upstream evidence in channel.
        target_evidence_id: Downstream evidence in channel.
        event_id: Mediating execution event.
        candidate_id: The candidate this was generated from.
        description: Human-readable explanation.
        metadata: Additional context.
    """

    intervention_id: str = Field(
        default_factory=lambda: (
            _next_deterministic_id("cintv_")
            if _is_deterministic()
            else f"cintv_{uuid.uuid4().hex}"
        )
    )
    intervention_type: ChannelInterventionType = ChannelInterventionType.BLOCK
    baseline_run_id: str
    source_evidence_id: str
    target_evidence_id: str
    event_id: str
    candidate_id: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
