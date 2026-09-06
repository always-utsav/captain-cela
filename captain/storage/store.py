"""Trace store for persisting canonical ExecutionRun objects.

The :class:`FileTraceStore` saves each
:class:`~captain.models.execution.ExecutionRun` as an independently readable
JSON file on the local filesystem.  Files are named by ``run_id`` and stored
in a configurable directory.

Serialization uses the existing Stage 2 Pydantic ``model_dump_json()`` /
``model_validate_json()`` round-trip.  No database or external dependency
is required.

Usage::

    from captain.storage import FileTraceStore

    store = FileTraceStore("./traces")
    store.save(run)
    loaded = store.load(run.run_id)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from captain.models.execution import ExecutionRun


class TraceStore:
    """Abstract trace store interface.

    Subclasses implement persistence of canonical ``ExecutionRun`` objects.
    """

    def save(self, run: ExecutionRun) -> None:
        """Persist an execution run."""
        raise NotImplementedError

    def load(self, run_id: str) -> ExecutionRun | None:
        """Load a run by ID, or ``None`` if not found."""
        raise NotImplementedError

    def exists(self, run_id: str) -> bool:
        """Check whether a run with *run_id* exists."""
        raise NotImplementedError

    def delete(self, run_id: str) -> bool:
        """Delete a run.  Returns ``True`` if it existed."""
        raise NotImplementedError

    def list_runs(self) -> list[str]:
        """Return all stored run IDs."""
        raise NotImplementedError

    def count(self) -> int:
        """Return the number of stored runs."""
        raise NotImplementedError


class FileTraceStore(TraceStore):
    """Filesystem-backed trace store.

    Each :class:`~captain.models.execution.ExecutionRun` is stored as a
    single ``.json`` file named ``<run_id>.json`` in the configured
    *base_dir*.

    Writes use atomic temporary-file semantics: data is written to a
    temporary file in the same directory and then renamed, preventing
    partial/corrupt files on crash.

    Args:
        base_dir: Directory where trace files are stored.  Created
            automatically if it does not exist.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """The directory where trace files are stored."""
        return self._base_dir

    def save(self, run: ExecutionRun) -> None:
        """Persist *run* as a JSON file.

        Uses atomic write: data is written to a temp file first, then
        renamed to the final path.  This prevents corruption if the
        process is interrupted mid-write.

        Overwrites any existing file with the same ``run_id``.
        """
        target = self._path_for(run.run_id)
        json_bytes = run.model_dump_json(indent=2).encode("utf-8")

        # Atomic write via temp file + rename in the same directory.
        fd, tmp_path = tempfile.mkstemp(dir=str(self._base_dir), suffix=".tmp")
        try:
            os.write(fd, json_bytes)
            os.close(fd)
            # On Windows, replace() handles overwriting an existing file.
            os.replace(tmp_path, str(target))
        except BaseException:
            os.close(fd) if not _is_closed(fd) else None
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def load(self, run_id: str) -> ExecutionRun | None:
        """Load a run by ID.

        Returns:
            The deserialized :class:`ExecutionRun`, or ``None`` if the
            file does not exist or contains invalid JSON.
        """
        path = self._path_for(run_id)
        if not path.exists():
            return None
        try:
            json_text = path.read_text(encoding="utf-8")
            return ExecutionRun.model_validate_json(json_text)
        except (ValueError, OSError):
            return None

    def exists(self, run_id: str) -> bool:
        """Check whether a trace file for *run_id* exists."""
        return self._path_for(run_id).exists()

    def delete(self, run_id: str) -> bool:
        """Delete the trace file for *run_id*.

        Returns:
            ``True`` if the file existed and was deleted.
        """
        path = self._path_for(run_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_runs(self) -> list[str]:
        """Return the run IDs of all stored traces, sorted."""
        return sorted(p.stem for p in self._base_dir.glob("*.json") if p.is_file())

    def count(self) -> int:
        """Return the number of stored trace files."""
        return len(self.list_runs())

    # --- internal -----------------------------------------------------------

    def _path_for(self, run_id: str) -> Path:
        """Return the filesystem path for *run_id*."""
        return self._base_dir / f"{run_id}.json"


def _is_closed(fd: int) -> bool:
    """Check if a file descriptor is already closed."""
    try:
        os.fstat(fd)
    except OSError:
        return True
    return False
