"""Tests for captain.agent.tools — tool interface and demo tools."""

from __future__ import annotations

from datetime import UTC, datetime

from captain.agent.tools import (
    CalculatorTool,
    EchoTool,
    TimestampTool,
    ToolRegistry,
    create_default_tool_registry,
)


class TestCalculatorTool:
    """Tests for the CalculatorTool."""

    def test_addition(self) -> None:
        tool = CalculatorTool()
        assert tool.execute({"expression": "2 + 3"}) == "5"

    def test_multiplication(self) -> None:
        tool = CalculatorTool()
        assert tool.execute({"expression": "4 * 5"}) == "20"

    def test_complex_expression(self) -> None:
        tool = CalculatorTool()
        assert tool.execute({"expression": "2 + 3 * 4"}) == "14"

    def test_float_result(self) -> None:
        tool = CalculatorTool()
        assert tool.execute({"expression": "7 / 2"}) == "3.5"

    def test_power(self) -> None:
        tool = CalculatorTool()
        assert tool.execute({"expression": "2 ** 10"}) == "1024"

    def test_empty_expression_returns_error(self) -> None:
        tool = CalculatorTool()
        result = tool.execute({"expression": ""})
        assert result.startswith("Error")

    def test_no_expression_key_returns_error(self) -> None:
        tool = CalculatorTool()
        result = tool.execute({})
        assert result.startswith("Error")

    def test_division_by_zero_returns_error(self) -> None:
        tool = CalculatorTool()
        result = tool.execute({"expression": "1 / 0"})
        assert result.startswith("Error")

    def test_invalid_expression_returns_error(self) -> None:
        tool = CalculatorTool()
        result = tool.execute({"expression": "import os"})
        assert result.startswith("Error")

    def test_name_and_description(self) -> None:
        tool = CalculatorTool()
        assert tool.name == "calculator"
        assert len(tool.description) > 0


class TestTimestampTool:
    """Tests for the TimestampTool."""

    def test_frozen_time(self) -> None:
        frozen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        tool = TimestampTool(frozen_time=frozen)
        result = tool.execute({})
        assert "2026-01-01" in result

    def test_live_time_returns_string(self) -> None:
        tool = TimestampTool()
        result = tool.execute({})
        # Should be a valid ISO format timestamp
        assert "T" in result

    def test_name_and_description(self) -> None:
        tool = TimestampTool()
        assert tool.name == "timestamp"
        assert len(tool.description) > 0


class TestEchoTool:
    """Tests for the EchoTool."""

    def test_echoes_message(self) -> None:
        tool = EchoTool()
        assert tool.execute({"message": "hello world"}) == "hello world"

    def test_empty_message(self) -> None:
        tool = EchoTool()
        assert tool.execute({}) == ""

    def test_name_and_description(self) -> None:
        tool = EchoTool()
        assert tool.name == "echo"
        assert len(tool.description) > 0


class TestToolRegistry:
    """Tests for the ToolRegistry."""

    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        tool = EchoTool()
        registry.register(tool)
        assert registry.get("echo") is tool

    def test_get_missing_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(CalculatorTool())
        names = [t.name for t in registry.list_tools()]
        assert "echo" in names
        assert "calculator" in names

    def test_len(self) -> None:
        registry = ToolRegistry()
        assert len(registry) == 0
        registry.register(EchoTool())
        assert len(registry) == 1

    def test_contains(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert "echo" in registry
        assert "calculator" not in registry

    def test_tool_descriptions(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        desc = registry.tool_descriptions()
        assert "echo" in desc

    def test_create_default_registry(self) -> None:
        registry = create_default_tool_registry()
        assert "calculator" in registry
        assert "timestamp" in registry
        assert "echo" in registry
        assert len(registry) == 3
