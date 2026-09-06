"""Canonical identifier generation for CAPTAIN models.

Provides a consistent strategy for generating globally unique, serializable
identifiers across all CAPTAIN canonical models.  IDs use UUID4 with
distinguishable prefixes (``run_``, ``evt_``, ``art_``) to aid debugging.

Identifiers are plain strings -- no database-generated sequences required.
Ordering determinism comes from sequence numbers and timestamps, not UUID order.

For research reproducibility, a :class:`DeterministicIdContext` context
manager replaces uuid4-based generation with hashlib-based deterministic
IDs seeded by a master seed + counter.  When no context is active,
the original uuid4 behavior is preserved.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from collections.abc import Generator
from contextlib import contextmanager

# Thread-local storage for deterministic ID generation
_local = threading.local()


def _is_deterministic() -> bool:
    """Check if a deterministic ID context is active."""
    return getattr(_local, "deterministic_seed", None) is not None


def _next_deterministic_id(prefix: str) -> str:
    """Generate the next deterministic ID using seed + counter."""
    seed = _local.deterministic_seed
    counter = _local.deterministic_counter
    _local.deterministic_counter = counter + 1

    # Use hashlib for deterministic, collision-resistant IDs
    data = f"{seed}:{prefix}:{counter}".encode()
    h = hashlib.sha256(data).hexdigest()[:32]
    return f"{prefix}{h}"


@contextmanager
def deterministic_ids(seed: int) -> Generator[None, None, None]:
    """Context manager for deterministic ID generation.

    When active, all ID generation functions (generate_run_id,
    generate_event_id, generate_artifact_id) produce deterministic
    IDs based on the given seed and an internal counter.

    This is essential for research reproducibility: the same seed
    always produces the same sequence of IDs.

    Usage::

        with deterministic_ids(seed=42):
            rid = generate_run_id()   # always the same for seed=42
            eid = generate_event_id() # always the same

    The context is thread-local and can be nested.

    Args:
        seed: Master seed for deterministic generation.
    """
    prev_seed = getattr(_local, "deterministic_seed", None)
    prev_counter = getattr(_local, "deterministic_counter", None)
    _local.deterministic_seed = seed
    _local.deterministic_counter = 0
    try:
        yield
    finally:
        _local.deterministic_seed = prev_seed
        _local.deterministic_counter = prev_counter


def generate_run_id() -> str:
    """Generate a unique run identifier with ``run_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("run_")
    return f"run_{uuid.uuid4().hex}"


def generate_event_id() -> str:
    """Generate a unique event identifier with ``evt_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("evt_")
    return f"evt_{uuid.uuid4().hex}"


def generate_artifact_id() -> str:
    """Generate a unique artifact identifier with ``art_`` prefix."""
    if _is_deterministic():
        return _next_deterministic_id("art_")
    return f"art_{uuid.uuid4().hex}"


def validate_id(value: str, prefix: str) -> str:
    """Validate that *value* is a non-empty string with the expected prefix.

    Args:
        value: The identifier to validate.
        prefix: Required prefix (e.g. ``"run_"``).

    Returns:
        The validated identifier.

    Raises:
        ValueError: If *value* is empty or does not start with *prefix*.
    """
    if not value:
        msg = "Identifier must not be empty"
        raise ValueError(msg)
    if not value.startswith(prefix):
        msg = f"Identifier must start with '{prefix}', got '{value[:10]}...'"
        raise ValueError(msg)
    return value
