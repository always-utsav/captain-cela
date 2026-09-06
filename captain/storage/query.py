"""Query layer for stored CAPTAIN execution traces.

The :class:`TraceQuery` provides composable filtering over runs stored in
a :class:`~captain.storage.store.TraceStore`.  Filters are combined with
AND semantics and applied lazily: runs are loaded and filtered on demand.

Usage::

    from captain.storage import FileTraceStore, TraceQuery

    store = FileTraceStore("./traces")
    query = TraceQuery(store)

    # Find all completed runs
    completed = query.by_status(RunStatus.COMPLETED).execute()

    # Find runs in a time range containing tool_call events
    results = (
        query
        .by_time_range(start=t0, end=t1)
        .by_event_type(EventType.TOOL_CALL)
        .execute()
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from captain.models.enums import EventType, RunStatus
from captain.models.execution import ExecutionRun

if TYPE_CHECKING:
    from captain.storage.store import TraceStore


class TraceQuery:
    """Composable query builder for stored execution traces.

    Each filter method returns ``self`` so calls can be chained.
    Call :meth:`execute` to materialise results.

    Args:
        store: The :class:`TraceStore` to query against.
    """

    def __init__(self, store: TraceStore) -> None:
        self._store = store
        self._run_id: str | None = None
        self._status: RunStatus | None = None
        self._start_after: datetime | None = None
        self._start_before: datetime | None = None
        self._event_type: EventType | None = None

    # --- filter methods (chainable) -----------------------------------------

    def by_run_id(self, run_id: str) -> TraceQuery:
        """Filter to a specific run ID."""
        self._run_id = run_id
        return self

    def by_status(self, status: RunStatus) -> TraceQuery:
        """Filter runs by lifecycle status."""
        self._status = status
        return self

    def by_time_range(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> TraceQuery:
        """Filter runs whose ``started_at`` falls within [start, end].

        Either or both bounds may be ``None`` for an open range.
        """
        self._start_after = start
        self._start_before = end
        return self

    def by_event_type(self, event_type: EventType) -> TraceQuery:
        """Filter runs that contain at least one event of *event_type*."""
        self._event_type = event_type
        return self

    # --- execution ----------------------------------------------------------

    def execute(self) -> list[ExecutionRun]:
        """Apply all filters and return matching runs.

        Runs are loaded from the store and filtered in memory.  Order
        is by ``started_at`` ascending.
        """
        # If a specific run_id is requested, short-circuit.
        if self._run_id is not None:
            run = self._store.load(self._run_id)
            if run is None:
                return []
            return [run] if self._matches(run) else []

        results: list[ExecutionRun] = []
        for run_id in self._store.list_runs():
            run = self._store.load(run_id)
            if run is not None and self._matches(run):
                results.append(run)

        results.sort(key=lambda r: r.started_at)
        return results

    def first(self) -> ExecutionRun | None:
        """Return the first matching run, or ``None``."""
        results = self.execute()
        return results[0] if results else None

    # --- internal -----------------------------------------------------------

    def _matches(self, run: ExecutionRun) -> bool:
        """Check whether *run* passes all configured filters."""
        if self._status is not None and run.status != self._status:
            return False

        if self._start_after is not None and run.started_at < self._start_after:
            return False

        if self._start_before is not None and run.started_at > self._start_before:
            return False

        if self._event_type is not None:
            event_types = {e.event_type for e in run.events}
            if self._event_type not in event_types:
                return False

        return True
