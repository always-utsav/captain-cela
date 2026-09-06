"""Tests for captain.models.ids -- identifier generation and validation."""

from __future__ import annotations

import pytest

from captain.models.ids import (
    generate_artifact_id,
    generate_event_id,
    generate_run_id,
    validate_id,
)


class TestIdGeneration:
    """Tests for the ID factory functions."""

    def test_run_id_has_prefix(self) -> None:
        rid = generate_run_id()
        assert rid.startswith("run_")

    def test_event_id_has_prefix(self) -> None:
        eid = generate_event_id()
        assert eid.startswith("evt_")

    def test_artifact_id_has_prefix(self) -> None:
        aid = generate_artifact_id()
        assert aid.startswith("art_")

    def test_ids_are_unique(self) -> None:
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100

    def test_ids_are_strings(self) -> None:
        assert isinstance(generate_run_id(), str)
        assert isinstance(generate_event_id(), str)
        assert isinstance(generate_artifact_id(), str)

    def test_id_length_is_reasonable(self) -> None:
        # "run_" + 32 hex chars = 36
        rid = generate_run_id()
        assert len(rid) == 36


class TestIdValidation:
    """Tests for validate_id."""

    def test_valid_run_id(self) -> None:
        rid = generate_run_id()
        assert validate_id(rid, "run_") == rid

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_id("", "run_")

    def test_wrong_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="must start with"):
            validate_id("evt_abc", "run_")
