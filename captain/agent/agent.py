"""Agent orchestrator for the CAPTAIN reference agent.

The :class:`Agent` ties together the planner, reasoner, response generator,
working memory, and tool registry into a single ``run()`` method that
executes the full agent pipeline:

    Receive Task → Plan → Reason / Execute Steps → Generate Response

The orchestrator is deliberately thin.  Each sub-component is independently
testable, and every method call is a clear instrumentation point for future
CAPTAIN tracing and provenance modules.
"""

from __future__ import annotations

from captain.adapters.llm import LLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.planner import Planner
from captain.agent.reasoner import Reasoner
from captain.agent.response import ResponseGenerator
from captain.agent.tools import ToolRegistry
from captain.agent.types import AgentResponse, TaskInput, ToolCall
from captain.core.logging import get_logger

_log = get_logger("agent")


class Agent:
    """Reference multimodal agent for CAPTAIN.

    This agent is **not** the research contribution.  It is the execution
    target that CAPTAIN will observe, trace, and analyse in later stages.

    Args:
        llm: The language-model provider.
        tool_registry: Pre-configured tool registry.  If ``None``, an
            empty registry is used.
        memory: Working memory instance.  If ``None``, a fresh
            :class:`WorkingMemory` is created per run.
    """

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry | None = None,
        memory: WorkingMemory | None = None,
    ) -> None:
        self._llm = llm
        self._tool_registry = tool_registry or ToolRegistry()
        self._memory = memory
        self._planner = Planner(llm)
        self._reasoner = Reasoner(llm)
        self._response_generator = ResponseGenerator(llm)

    def run(self, task_input: TaskInput) -> AgentResponse:
        """Execute the full agent pipeline for *task_input*.

        The pipeline:

        1. **Plan** — decompose the task into steps.
        2. **Execute** — run each step (tool call or reasoning).
        3. **Respond** — synthesise a final answer.

        Args:
            task_input: The incoming task.

        Returns:
            An :class:`AgentResponse` containing the final answer,
            tool-call log, and step descriptions.
        """
        # Use the injected memory or create a fresh one for this run.
        memory = self._memory if self._memory is not None else WorkingMemory()

        # Store the original task in memory so downstream steps can refer to it.
        memory.store("task", task_input.text)

        _log.info("Agent run started — task: %s", task_input.text[:80])

        # 1. Plan
        plan_steps = self._planner.plan(task_input, memory, self._tool_registry)
        _log.info("Plan created with %d step(s)", len(plan_steps))

        # 2. Execute each step
        tool_calls: list[ToolCall] = []
        step_descriptions: list[str] = []

        for idx, step in enumerate(plan_steps):
            _log.debug("Executing step %d: %s", idx, step.description)
            result, tool_call = self._reasoner.execute_step(
                step,
                memory,
                self._tool_registry,
                step_index=idx,
            )
            step_descriptions.append(f"Step {idx}: {step.description} → {result}")
            if tool_call is not None:
                tool_calls.append(tool_call)

        # 3. Generate response
        response = self._response_generator.generate(
            task_input, memory, tool_calls, step_descriptions
        )
        _log.info("Agent run completed")

        return response
