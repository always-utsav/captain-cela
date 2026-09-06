"""Tests for captain.agent.memory — working memory."""

from __future__ import annotations

from captain.agent.memory import WorkingMemory


class TestWorkingMemory:
    """Tests for the WorkingMemory class."""

    def test_store_and_retrieve(self) -> None:
        mem = WorkingMemory()
        mem.store("key1", "value1")
        assert mem.retrieve("key1") == "value1"

    def test_retrieve_missing_key_returns_none(self) -> None:
        mem = WorkingMemory()
        assert mem.retrieve("nonexistent") is None

    def test_overwrite_existing_key(self) -> None:
        mem = WorkingMemory()
        mem.store("k", "v1")
        mem.store("k", "v2")
        assert mem.retrieve("k") == "v2"

    def test_list_keys_preserves_insertion_order(self) -> None:
        mem = WorkingMemory()
        mem.store("b", 1)
        mem.store("a", 2)
        mem.store("c", 3)
        assert mem.list_keys() == ["b", "a", "c"]

    def test_clear(self) -> None:
        mem = WorkingMemory()
        mem.store("x", 1)
        mem.store("y", 2)
        mem.clear()
        assert mem.list_keys() == []
        assert len(mem) == 0

    def test_len(self) -> None:
        mem = WorkingMemory()
        assert len(mem) == 0
        mem.store("a", 1)
        assert len(mem) == 1

    def test_contains(self) -> None:
        mem = WorkingMemory()
        mem.store("present", True)
        assert "present" in mem
        assert "absent" not in mem

    def test_to_context_string_empty(self) -> None:
        mem = WorkingMemory()
        assert mem.to_context_string() == "(empty)"

    def test_to_context_string_populated(self) -> None:
        mem = WorkingMemory()
        mem.store("fact", "the sky is blue")
        mem.store("count", 42)
        ctx = mem.to_context_string()
        assert "fact: the sky is blue" in ctx
        assert "count: 42" in ctx
