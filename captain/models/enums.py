"""Canonical enumerations for CAPTAIN execution models.

Provides stable enums for event types, run statuses, and artifact types.
All enums use :class:`~enum.StrEnum` for clean JSON serialization.

Designed for extensibility: new members can be added to any enum without
redesigning the model.
"""

from __future__ import annotations

import enum


class EventType(enum.StrEnum):
    """Type of an observable execution event.

    This enum covers the core event categories produced during agent
    execution.  Future stages may add members without breaking existing
    serialized data.
    """

    INPUT = "input"
    PLANNING = "planning"
    REASONING = "reasoning"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MODEL_CALL = "model_call"
    MODEL_RESULT = "model_result"
    OUTPUT = "output"
    ERROR = "error"


class RunStatus(enum.StrEnum):
    """Lifecycle status of an :class:`~captain.models.execution.ExecutionRun`.

    The valid transitions are::

        CREATED -> RUNNING -> COMPLETED
                           -> FAILED
                           -> CANCELLED

    ``CANCELLED`` is included because an agent run may be aborted by the
    user or by a timeout before it completes or fails.
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(enum.StrEnum):
    """Type/modality of a canonical :class:`~captain.models.artifacts.Artifact`.

    Represents the kind of data an artifact holds, independent of any
    specific agent framework.
    """

    TEXT = "text"
    IMAGE = "image"
    STRUCTURED_DATA = "structured_data"
    FILE = "file"
    TOOL_OUTPUT = "tool_output"
    MODEL_OUTPUT = "model_output"
