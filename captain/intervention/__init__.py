"""CAPTAIN counterfactual intervention system.

This sub-package provides the formal representation and validation
of hypothetical modifications to observed agent executions.

Core types::

    from captain.intervention import (
        Intervention,
        InterventionType,
        InterventionSet,
        InterventionValidator,
        InterventionValidationResult,
    )
"""

from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
    generate_intervention_id,
)
from captain.intervention.validation import (
    InterventionFinding,
    InterventionSeverity,
    InterventionValidationResult,
    InterventionValidator,
)

__all__ = [
    "Intervention",
    "InterventionFinding",
    "InterventionSet",
    "InterventionSeverity",
    "InterventionType",
    "InterventionValidationResult",
    "InterventionValidator",
    "generate_intervention_id",
]
