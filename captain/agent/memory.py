"""Lightweight working memory for the CAPTAIN reference agent.

Provides an in-process, dictionary-backed memory store that agent components
use to share information within a single run.  There is no persistence,
no vector search, and no embedding — just deterministic key/value storage
with insertion-order preservation (guaranteed by Python ≥ 3.7 dicts).

This module exists as a stable interface so that future tracing and
provenance modules can observe every memory read/write without refactoring.
"""

from __future__ import annotations

from typing import Any


class WorkingMemory:
    """In-process working memory for a single agent run.

    Attributes are deliberately kept simple.  The class exposes only the
    operations that future CAPTAIN instrumentation needs to intercept.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    # --- mutators -------------------------------------------------------------

    def store(self, key: str, value: Any) -> None:
        """Store a value under *key*, overwriting any existing entry.

        Args:
            key: Identifier for the memory entry.
            value: Arbitrary data to store.
        """
        self._store[key] = value

    def clear(self) -> None:
        """Remove all entries from working memory."""
        self._store.clear()

    # --- accessors ------------------------------------------------------------

    def retrieve(self, key: str) -> Any | None:
        """Retrieve a value by *key*, returning ``None`` if absent.

        Args:
            key: The key to look up.

        Returns:
            The stored value, or ``None`` if the key does not exist.
        """
        return self._store.get(key)

    def list_keys(self) -> list[str]:
        """Return all keys currently in memory, in insertion order."""
        return list(self._store.keys())

    def to_context_string(self) -> str:
        """Serialise the entire memory as a human-readable string.

        This is used by downstream components (planner, reasoner, response
        generator) that need to feed memory contents into an LLM prompt.
        """
        if not self._store:
            return "(empty)"
        lines: list[str] = []
        for key, value in self._store.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store
