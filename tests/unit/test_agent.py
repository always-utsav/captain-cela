"""Tests for captain.agent.agent — full agent pipeline."""

from __future__ import annotations

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.memory import WorkingMemory
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import Content, Modality, TaskInput


class TestAgent:
    """Tests for the Agent orchestrator."""

    def test_simple_run(self) -> None:
        """Agent should complete a simple run and return a response."""
        # The mock returns:
        #   call 1 (planner): a single-step plan
        #   call 2 (reasoner): reasoning result
        #   call 3 (response generator): final answer
        llm = MockLLMProvider(
            responses=[
                "1. Analyse the question",
                "The analysis is complete",
                "Final answer: done",
            ]
        )
        agent = Agent(llm=llm)
        response = agent.run(TaskInput.from_text("What is AI?"))

        assert response.content == "Final answer: done"
        assert len(response.steps) >= 1

    def test_run_with_tool_invocation(self) -> None:
        """Agent should invoke tools when the plan includes [TOOL:…]."""
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:calculator] Compute 5 + 3",
                "The final answer is 8",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        response = agent.run(TaskInput.from_text("What is 5+3?"))

        # The calculator tool should have been invoked
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "calculator"
        # tool_args is empty because the planner doesn't extract arguments
        # from free text — this is expected Stage 1 behavior
        assert isinstance(response.tool_calls[0].result, str)

    def test_run_with_injected_memory(self) -> None:
        """Agent should use injected memory and persist results there."""
        memory = WorkingMemory()
        memory.store("prior_fact", "birds can fly")
        llm = MockLLMProvider(
            responses=[
                "1. Recall prior knowledge",
                "Birds can fly, confirmed",
                "Birds fly.",
            ]
        )
        agent = Agent(llm=llm, memory=memory)
        response = agent.run(TaskInput.from_text("Can birds fly?"))

        assert response.content == "Birds fly."
        # Memory should contain both the prior fact and the step result
        assert memory.retrieve("prior_fact") == "birds can fly"
        assert memory.retrieve("step_0_result") is not None

    def test_run_is_deterministic(self) -> None:
        """Two identical runs with the same MockLLM should produce identical results."""
        responses = [
            "1. Think\n2. Respond",
            "thought result",
            "respond result",
            "final answer",
        ]

        agent1 = Agent(llm=MockLLMProvider(responses=list(responses)))
        r1 = agent1.run(TaskInput.from_text("Determinism test"))

        agent2 = Agent(llm=MockLLMProvider(responses=list(responses)))
        r2 = agent2.run(TaskInput.from_text("Determinism test"))

        assert r1.content == r2.content
        assert r1.steps == r2.steps

    def test_multimodal_task_input(self) -> None:
        """Agent should accept multimodal input without errors."""
        llm = MockLLMProvider(
            responses=[
                "1. Process the inputs",
                "Processed",
                "Done",
            ]
        )
        task = TaskInput(
            contents=[
                Content(modality=Modality.TEXT, data="Describe this image"),
                Content(modality=Modality.IMAGE, data="placeholder_image.png"),
            ]
        )
        agent = Agent(llm=llm)
        response = agent.run(task)
        assert response.content == "Done"

    def test_empty_task(self) -> None:
        """Agent should handle an empty task gracefully."""
        llm = MockLLMProvider(
            responses=[
                "1. Nothing to do",
                "No action needed",
                "No result",
            ]
        )
        agent = Agent(llm=llm)
        response = agent.run(TaskInput())
        assert isinstance(response.content, str)


class TestMockLLMProvider:
    """Tests for the MockLLMProvider."""

    def test_scripted_responses(self) -> None:
        llm = MockLLMProvider(responses=["first", "second", "third"])
        assert llm.generate("a") == "first"
        assert llm.generate("b") == "second"
        assert llm.generate("c") == "third"

    def test_scripted_responses_cycle(self) -> None:
        llm = MockLLMProvider(responses=["a", "b"])
        assert llm.generate("1") == "a"
        assert llm.generate("2") == "b"
        assert llm.generate("3") == "a"  # cycles back

    def test_echo_mode(self) -> None:
        llm = MockLLMProvider()
        assert llm.generate("hello") == "hello"

    def test_system_prompt_accepted(self) -> None:
        """system_prompt kwarg should be accepted without error."""
        llm = MockLLMProvider(responses=["ok"])
        result = llm.generate("q", system_prompt="be helpful")
        assert result == "ok"
