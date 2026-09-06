"""CAPTAIN canonical data models.

This sub-package defines CAPTAIN's framework-independent representation of
agent executions.  These models are consumed by tracing, provenance,
execution graph, counterfactual replay, and failure analysis layers.

The canonical models are **representations only** -- they do not implement
tracing, instrumentation, graph construction, or analysis.

Core types::

    from captain.models import (
        ExecutionRun,
        Event,
        Artifact,
        EventType,
        RunStatus,
        ArtifactType,
    )
"""

from captain.models.artifacts import Artifact
from captain.models.enums import ArtifactType, EventType, RunStatus
from captain.models.events import Event
from captain.models.execution import ExecutionRun

__all__ = [
    "Artifact",
    "ArtifactType",
    "Event",
    "EventType",
    "ExecutionRun",
    "RunStatus",
]
