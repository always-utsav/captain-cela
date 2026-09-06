"""Counterfactual intervention model for CAPTAIN.

Defines the formal representation of a hypothetical modification to an
observed :class:`~captain.models.execution.ExecutionRun`.

Core types:

- :class:`InterventionType` -- taxonomy of supported interventions.
- :class:`Intervention` -- a single counterfactual modification.
- :class:`InterventionSet` -- a validated, deterministic collection of
  interventions for one baseline run.

**Architectural boundary**:

- OBSERVATION: what actually happened (ExecutionRun).
- INTERVENTION: what we hypothetically change (this module).
- REPLAY: what happens when the changed execution is rerun (Stage 10).
- CAUSAL EFFECT: the difference replay demonstrates (future).

This module implements ONLY interventions.  It never mutates the original
ExecutionRun.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from captain.models.ids import _is_deterministic, _next_deterministic_id


class InterventionType(enum.StrEnum):
    """Taxonomy of supported counterfactual interventions.

    - ``ARTIFACT_REPLACEMENT``: Replace an artifact's value/reference.
    - ``TOOL_RESULT_OVERRIDE``: Replace a tool-result event's output.
    - ``EVENT_DISABLE``: Prevent an event from participating in replay.
    - ``EVENT_OUTPUT_OVERRIDE``: Replace an event's output artifact/value.
    """

    ARTIFACT_REPLACEMENT = "artifact_replacement"
    TOOL_RESULT_OVERRIDE = "tool_result_override"
    EVENT_DISABLE = "event_disable"
    EVENT_OUTPUT_OVERRIDE = "event_output_override"


def generate_intervention_id() -> str:
    """Generate a globally unique intervention ID."""
    if _is_deterministic():
        return _next_deterministic_id("intv_")
    return f"intv_{uuid.uuid4().hex}"


class Intervention(BaseModel):
    """A single counterfactual intervention on an observed execution.

    Describes WHAT to change, not the effect of the change.

    Attributes:
        intervention_id: Unique identifier for this intervention.
        intervention_type: The kind of modification.
        baseline_run_id: The observed run this intervention targets.
        target_id: The canonical ID of the target (artifact_id or event_id).
        replacement_value: The replacement data (required for all types
            except EVENT_DISABLE).
        description: Optional human-readable explanation.
        created_at: When this intervention was created.
        metadata: Additional context.
    """

    intervention_id: str = Field(default_factory=generate_intervention_id)
    intervention_type: InterventionType
    baseline_run_id: str
    target_id: str
    replacement_value: str | dict[str, Any] | list[Any] | None = None
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class InterventionSet(BaseModel):
    """A deterministic collection of interventions for one baseline run.

    All interventions in the set must target the same baseline run.
    Interventions are ordered by their position in the list (insertion order).

    Attributes:
        baseline_run_id: The observed run all interventions target.
        interventions: Ordered list of interventions.
        description: Optional human-readable description of the set.
        metadata: Additional context.
    """

    baseline_run_id: str
    interventions: list[Intervention] = Field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add(self, intervention: Intervention) -> None:
        """Add an intervention to the set."""
        self.interventions.append(intervention)

    @property
    def count(self) -> int:
        """Number of interventions."""
        return len(self.interventions)

    def get_targets(self) -> list[str]:
        """Return sorted list of unique target IDs."""
        return sorted({i.target_id for i in self.interventions})
