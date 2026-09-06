"""Reasoner that executes individual plan steps for the CAPTAIN agent.

The :class:`Reasoner` takes a single :class:`~captain.agent.types.PlanStep`
and either invokes a tool (via :class:`~captain.agent.tools.ToolRegistry`) or
delegates to the :class:`~captain.adapters.llm.LLMProvider` for a reasoning
response.  Every result is recorded in
:class:`~captain.agent.memory.WorkingMemory`.

Each method is a clear instrumentation point for future CAPTAIN tracing.
"""

from __future__ import annotations

from captain.adapters.llm import LLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.tools import ToolRegistry
from captain.agent.types import PlanStep, ToolCall
from captain.core.logging import get_logger

_log = get_logger("agent.reasoner")


class Reasoner:
    """Executes plan steps, recording results in working memory.

    Attributes:
        llm: The language-model provider for reasoning steps.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def execute_step(
        self,
        step: PlanStep,
        memory: WorkingMemory,
        tool_registry: ToolRegistry,
        *,
        step_index: int = 0,
    ) -> tuple[str, ToolCall | None]:
        """Execute a single plan step.

        Args:
            step: The plan step to execute.
            memory: Working memory (results are stored here).
            tool_registry: Available tools for tool-steps.
            step_index: Ordinal index of this step in the plan (used as
                the memory key prefix).

        Returns:
            A ``(result_text, tool_call_or_none)`` tuple.  *tool_call* is
            ``None`` for pure-reasoning steps.
        """
        if step.requires_tool and step.tool_name:
            result, tool_call = self._execute_tool_step(step, tool_registry)
        else:
            result = self._execute_reasoning_step(step, memory)
            tool_call = None

        # Persist the result in working memory.
        memory_key = f"step_{step_index}_result"
        memory.store(memory_key, result)
        _log.debug("Step %d completed: %s", step_index, result[:80])

        return result, tool_call

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_tool_step(
        self,
        step: PlanStep,
        tool_registry: ToolRegistry,
    ) -> tuple[str, ToolCall]:
        """Invoke the tool specified by *step*."""
        tool = tool_registry.get(step.tool_name or "")
        if tool is None:
            error_msg = f"Tool '{step.tool_name}' not found in registry."
            _log.warning(error_msg)
            return error_msg, ToolCall(
                tool_name=step.tool_name or "unknown",
                arguments=step.tool_args,
                result=error_msg,
            )

        result = tool.execute(step.tool_args)
        _log.debug("Tool '%s' returned: %s", tool.name, result[:80])
        return result, ToolCall(
            tool_name=tool.name,
            arguments=step.tool_args,
            result=result,
        )

    def _execute_reasoning_step(
        self,
        step: PlanStep,
        memory: WorkingMemory,
    ) -> str:
        """Delegate a reasoning step to the LLM."""
        prompt = f"Step: {step.description}\n\nWorking memory:\n{memory.to_context_string()}"
        return self._llm.generate(
            prompt,
            system_prompt="You are a reasoning agent. Execute the given step.",
        )
