"""Tests for captain.agent.planner — task planning."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.planner import Planner
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput


class TestPlanner:
    """Tests for the Planner class."""

    def test_plan_produces_steps(self) -> None:
        """A numbered LLM response should produce multiple PlanSteps."""
        llm = MockLLMProvider(
            responses=["1. Understand the question\n2. Compute the answer\n3. Respond"]
        )
        planner = Planner(llm)
        steps = planner.plan(
            TaskInput.from_text("What is 2+2?"),
            WorkingMemory(),
        )
        assert len(steps) == 3
        assert steps[0].description == "Understand the question"
        assert steps[0].requires_tool is False

    def test_plan_detects_tool_markers(self) -> None:
        """[TOOL:name] markers in LLM output should set requires_tool."""
        llm = MockLLMProvider(
            responses=["1. [TOOL:calculator] Compute 2+3\n2. Summarise the result"]
        )
        planner = Planner(llm)
        registry = create_default_tool_registry()
        steps = planner.plan(
            TaskInput.from_text("Compute 2+3"),
            WorkingMemory(),
            registry,
        )
        assert len(steps) == 2
        assert steps[0].requires_tool is True
        assert steps[0].tool_name == "calculator"
        assert steps[1].requires_tool is False

    def test_plan_fallback_on_unparseable_response(self) -> None:
        """If the LLM returns no numbered lines, wrap in a single step."""
        llm = MockLLMProvider(responses=[""])
        planner = Planner(llm)
        steps = planner.plan(
            TaskInput.from_text("Do something"),
            WorkingMemory(),
        )
        assert len(steps) == 1

    def test_plan_ignores_unknown_tool(self) -> None:
        """[TOOL:nonexistent] should not set requires_tool when tool is missing."""
        llm = MockLLMProvider(responses=["1. [TOOL:nonexistent] Try this tool"])
        planner = Planner(llm)
        registry = create_default_tool_registry()
        steps = planner.plan(
            TaskInput.from_text("Try unknown tool"),
            WorkingMemory(),
            registry,
        )
        assert len(steps) == 1
        assert steps[0].requires_tool is False

    def test_plan_with_memory_context(self) -> None:
        """Memory contents should be included in the planning prompt."""
        llm = MockLLMProvider(responses=["1. Use prior knowledge"])
        planner = Planner(llm)
        memory = WorkingMemory()
        memory.store("fact", "the answer is 42")
        steps = planner.plan(
            TaskInput.from_text("Recall the fact"),
            memory,
        )
        assert len(steps) >= 1
