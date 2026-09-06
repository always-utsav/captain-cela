"""CAPTAIN trace storage and query infrastructure.

This sub-package provides the persistence and query layer for canonical
:class:`~captain.models.execution.ExecutionRun` objects produced by the
Stage 3 tracing system.

Core types::

    from captain.storage import FileTraceStore, TraceQuery
"""

from captain.storage.query import TraceQuery
from captain.storage.store import FileTraceStore, TraceStore

__all__ = [
    "FileTraceStore",
    "TraceQuery",
    "TraceStore",
]
