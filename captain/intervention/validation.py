"""Intervention validation for CAPTAIN.

The :class:`InterventionValidator` checks interventions and intervention sets
against a baseline :class:`~captain.models.execution.ExecutionRun` and returns
structured :class:`InterventionValidationResult`.

Validation rules:

- Target IDs must be correctly formatted (prefix check).
- Artifact interventions must target existing artifacts.
- Event interventions must target existing events.
- Tool-result overrides must target TOOL_RESULT events.
- Replacement values are required for all types except EVENT_DISABLE.
- All interventions in a set must target the same baseline run.
- Duplicate targets within a set are rejected as conflicts.
- Conflicting intervention types on the same target are rejected.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field

from captain.intervention.model import Intervention, InterventionSet, InterventionType
from captain.models.enums import EventType
from captain.models.execution import ExecutionRun


class InterventionSeverity(enum.StrEnum):
    """Severity of a validation finding."""

    ERROR = "error"
    WARNING = "warning"


class InterventionFinding(BaseModel):
    """A single validation finding.

    Attributes:
        severity: ERROR or WARNING.
        code: Machine-readable finding code.
        message: Human-readable description.
        intervention_id: Related intervention ID, if applicable.
        metadata: Additional context.
    """

    severity: InterventionSeverity
    code: str
    message: str
    intervention_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InterventionValidationResult(BaseModel):
    """Structured result of intervention validation.

    Attributes:
        is_valid: True if zero errors were found.
        errors: Findings with ERROR severity.
        warnings: Findings with WARNING severity.
    """

    is_valid: bool = True
    errors: list[InterventionFinding] = Field(default_factory=list)
    warnings: list[InterventionFinding] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


# Target ID prefix expectations by intervention type
_ARTIFACT_TYPES = {InterventionType.ARTIFACT_REPLACEMENT}
_EVENT_TYPES = {
    InterventionType.EVENT_DISABLE,
    InterventionType.EVENT_OUTPUT_OVERRIDE,
    InterventionType.TOOL_RESULT_OVERRIDE,
}
_NEEDS_REPLACEMENT = {
    InterventionType.ARTIFACT_REPLACEMENT,
    InterventionType.TOOL_RESULT_OVERRIDE,
    InterventionType.EVENT_OUTPUT_OVERRIDE,
}


class InterventionValidator:
    """Validates interventions against a baseline ExecutionRun.

    Usage::

        result = InterventionValidator.validate(intervention, run)
        result = InterventionValidator.validate_set(iset, run)
    """

    @staticmethod
    def validate(
        intervention: Intervention,
        run: ExecutionRun,
    ) -> InterventionValidationResult:
        """Validate a single intervention against a baseline run."""
        findings: list[InterventionFinding] = []
        iid = intervention.intervention_id

        # Check baseline run ID match
        if intervention.baseline_run_id != run.run_id:
            findings.append(
                InterventionFinding(
                    severity=InterventionSeverity.ERROR,
                    code="BASELINE_MISMATCH",
                    message=(
                        f"Intervention targets run '{intervention.baseline_run_id}' "
                        f"but validated against '{run.run_id}'"
                    ),
                    intervention_id=iid,
                )
            )

        # Check target ID format
        itype = intervention.intervention_type
        if itype in _ARTIFACT_TYPES and not intervention.target_id.startswith("art_"):
            findings.append(
                InterventionFinding(
                    severity=InterventionSeverity.ERROR,
                    code="INVALID_TARGET_FORMAT",
                    message=(
                        f"Artifact intervention target '{intervention.target_id}' "
                        f"does not have 'art_' prefix"
                    ),
                    intervention_id=iid,
                )
            )
        if itype in _EVENT_TYPES and not intervention.target_id.startswith("evt_"):
            findings.append(
                InterventionFinding(
                    severity=InterventionSeverity.ERROR,
                    code="INVALID_TARGET_FORMAT",
                    message=(
                        f"Event intervention target '{intervention.target_id}' "
                        f"does not have 'evt_' prefix"
                    ),
                    intervention_id=iid,
                )
            )

        # Check target exists in run
        if itype in _ARTIFACT_TYPES:
            art_ids = {a.artifact_id for a in run.artifacts}
            if intervention.target_id not in art_ids:
                findings.append(
                    InterventionFinding(
                        severity=InterventionSeverity.ERROR,
                        code="TARGET_NOT_FOUND",
                        message=f"Artifact '{intervention.target_id}' not found in run",
                        intervention_id=iid,
                    )
                )

        if itype in _EVENT_TYPES:
            evt_ids = {e.event_id for e in run.events}
            if intervention.target_id not in evt_ids:
                findings.append(
                    InterventionFinding(
                        severity=InterventionSeverity.ERROR,
                        code="TARGET_NOT_FOUND",
                        message=f"Event '{intervention.target_id}' not found in run",
                        intervention_id=iid,
                    )
                )

        # Check tool-result targets a TOOL_RESULT event
        if itype == InterventionType.TOOL_RESULT_OVERRIDE:
            for evt in run.events:
                if evt.event_id == intervention.target_id:
                    if evt.event_type != EventType.TOOL_RESULT:
                        findings.append(
                            InterventionFinding(
                                severity=InterventionSeverity.ERROR,
                                code="WRONG_EVENT_TYPE",
                                message=(
                                    f"TOOL_RESULT_OVERRIDE targets event "
                                    f"'{intervention.target_id}' which is "
                                    f"'{evt.event_type.value}', not 'tool_result'"
                                ),
                                intervention_id=iid,
                            )
                        )
                    break

        # Check replacement value is present where required
        if itype in _NEEDS_REPLACEMENT and intervention.replacement_value is None:
            findings.append(
                InterventionFinding(
                    severity=InterventionSeverity.ERROR,
                    code="MISSING_REPLACEMENT",
                    message=(f"{itype.value} requires a replacement_value"),
                    intervention_id=iid,
                )
            )

        errors = [f for f in findings if f.severity == InterventionSeverity.ERROR]
        warnings = [f for f in findings if f.severity == InterventionSeverity.WARNING]

        return InterventionValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def validate_set(
        iset: InterventionSet,
        run: ExecutionRun,
    ) -> InterventionValidationResult:
        """Validate an intervention set against a baseline run."""
        findings: list[InterventionFinding] = []

        # Check baseline run ID
        if iset.baseline_run_id != run.run_id:
            findings.append(
                InterventionFinding(
                    severity=InterventionSeverity.ERROR,
                    code="SET_BASELINE_MISMATCH",
                    message=(
                        f"InterventionSet targets run '{iset.baseline_run_id}' "
                        f"but validated against '{run.run_id}'"
                    ),
                )
            )

        # Check each intervention's baseline matches the set
        for intv in iset.interventions:
            if intv.baseline_run_id != iset.baseline_run_id:
                findings.append(
                    InterventionFinding(
                        severity=InterventionSeverity.ERROR,
                        code="MIXED_BASELINE",
                        message=(
                            f"Intervention '{intv.intervention_id}' targets "
                            f"run '{intv.baseline_run_id}' but set targets "
                            f"'{iset.baseline_run_id}'"
                        ),
                        intervention_id=intv.intervention_id,
                    )
                )

        # Check for duplicate targets
        target_map: dict[str, list[Intervention]] = {}
        for intv in iset.interventions:
            target_map.setdefault(intv.target_id, []).append(intv)

        for target_id, intvs in target_map.items():
            if len(intvs) > 1:
                ids = [i.intervention_id for i in intvs]
                findings.append(
                    InterventionFinding(
                        severity=InterventionSeverity.ERROR,
                        code="DUPLICATE_TARGET",
                        message=(f"Target '{target_id}' has {len(intvs)} interventions: {ids}"),
                        metadata={"intervention_ids": ids},
                    )
                )

        # Validate each intervention individually
        for intv in iset.interventions:
            result = InterventionValidator.validate(intv, run)
            findings.extend(result.errors)
            findings.extend(result.warnings)

        errors = [f for f in findings if f.severity == InterventionSeverity.ERROR]
        warnings = [f for f in findings if f.severity == InterventionSeverity.WARNING]

        return InterventionValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
