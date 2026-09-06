"""Tests for captain.agent.reasoner — step execution."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.reasoner import Reasoner
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import PlanStep


class TestReasoner:
    """Tests for the Reasoner class."""

    def test_reasoning_step_delegates_to_llm(self) -> None:
        """A reasoning step (no tool) should call the LLM."""
        llm = MockLLMProvider(responses=["The answer is 42"])
        reasoner = Reasoner(llm)
        step = PlanStep(description="Think deeply")
        memory = WorkingMemory()
        registry = create_default_tool_registry()

        result, tool_call = reasoner.execute_step(step, memory, registry, step_index=0)
        assert result == "The answer is 42"
        assert tool_call is None
        assert memory.retrieve("step_0_result") == "The answer is 42"

    def test_tool_step_invokes_calculator(self) -> None:
        """A tool step with calculator should invoke CalculatorTool."""
        llm = MockLLMProvider()
        reasoner = Reasoner(llm)
        step = PlanStep(
            description="Compute 10 + 5",
            requires_tool=True,
            tool_name="calculator",
            tool_args={"expression": "10 + 5"},
        )
        memory = WorkingMemory()
        registry = create_default_tool_registry()

        result, tool_call = reasoner.execute_step(step, memory, registry, step_index=0)
        assert result == "15"
        assert tool_call is not None
        assert tool_call.tool_name == "calculator"
        assert tool_call.result == "15"

    def test_tool_step_invokes_echo(self) -> None:
        """A tool step with echo should invoke EchoTool."""
        llm = MockLLMProvider()
        reasoner = Reasoner(llm)
        step = PlanStep(
            description="Echo hello",
            requires_tool=True,
            tool_name="echo",
            tool_args={"message": "hello"},
        )
        memory = WorkingMemory()
        registry = create_default_tool_registry()

        result, tool_call = reasoner.execute_step(step, memory, registry, step_index=1)
        assert result == "hello"
        assert tool_call is not None
        assert tool_call.tool_name == "echo"

    def test_missing_tool_returns_error(self) -> None:
        """A tool step referencing a missing tool should return an error."""
        llm = MockLLMProvider()
        reasoner = Reasoner(llm)
        step = PlanStep(
            description="Use nonexistent",
            requires_tool=True,
            tool_name="nonexistent",
        )
        memory = WorkingMemory()
        registry = create_default_tool_registry()

        result, tool_call = reasoner.execute_step(step, memory, registry, step_index=0)
        assert "not found" in result
        assert tool_call is not None
        assert tool_call.tool_name == "nonexistent"

    def test_step_result_stored_in_memory(self) -> None:
        """Every step result should be persisted under step_N_result."""
        llm = MockLLMProvider(responses=["result_a", "result_b"])
        reasoner = Reasoner(llm)
        memory = WorkingMemory()
        registry = create_default_tool_registry()

        reasoner.execute_step(PlanStep(description="Step A"), memory, registry, step_index=0)
        reasoner.execute_step(PlanStep(description="Step B"), memory, registry, step_index=1)
        assert memory.retrieve("step_0_result") == "result_a"
        assert memory.retrieve("step_1_result") == "result_b"
