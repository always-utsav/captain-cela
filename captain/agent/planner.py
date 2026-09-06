"""Lightweight task planner for the CAPTAIN reference agent.

The :class:`Planner` decomposes a :class:`~captain.agent.types.TaskInput`
into an ordered list of :class:`~captain.agent.types.PlanStep` objects by
delegating to an :class:`~captain.adapters.llm.LLMProvider`.

In Stage 1, planning is deliberately simple: the LLM is asked (via prompt)
to produce steps.  The planner then parses the response into
:class:`PlanStep` objects.  With the :class:`MockLLMProvider`, the planner
uses a deterministic heuristic fallback when the LLM response cannot be
parsed into structured steps.
"""

from __future__ import annotations

from captain.adapters.llm import LLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.tools import ToolRegistry
from captain.agent.types import PlanStep, TaskInput


class Planner:
    """Decomposes a task into executable plan steps.

    The planner uses the LLM provider to generate a plan, then parses the
    result.  If parsing fails, it falls back to a single reasoning step.

    Attributes:
        llm: The language-model provider used for plan generation.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def plan(
        self,
        task_input: TaskInput,
        memory: WorkingMemory,
        tool_registry: ToolRegistry | None = None,
    ) -> list[PlanStep]:
        """Produce an ordered list of plan steps for *task_input*.

        Args:
            task_input: The agent's incoming task.
            memory: Current working memory (may influence planning).
            tool_registry: Available tools (descriptions are included in
                the planning prompt so the LLM can suggest tool usage).

        Returns:
            A list of :class:`PlanStep` objects.
        """
        prompt = self._build_prompt(task_input, memory, tool_registry)
        raw_plan = self._llm.generate(
            prompt,
            system_prompt=(
                "You are a task planner. Break the task into numbered steps. "
                "If a step requires a tool, prefix it with [TOOL:tool_name]. "
                "Example: 1. [TOOL:calculator] Compute 2+3"
            ),
        )
        return self._parse_plan(raw_plan, tool_registry)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        task_input: TaskInput,
        memory: WorkingMemory,
        tool_registry: ToolRegistry | None,
    ) -> str:
        parts: list[str] = [f"Task: {task_input.text}"]
        if tool_registry and len(tool_registry) > 0:
            parts.append(f"Available tools:\n{tool_registry.tool_descriptions()}")
        mem_ctx = memory.to_context_string()
        if mem_ctx != "(empty)":
            parts.append(f"Working memory:\n{mem_ctx}")
        return "\n\n".join(parts)

    @staticmethod
    def _parse_plan(
        raw: str,
        tool_registry: ToolRegistry | None,
    ) -> list[PlanStep]:
        """Parse the LLM's textual plan into :class:`PlanStep` objects.

        Lines that start with a digit and a period (e.g. ``1. …``) are
        treated as individual steps.  If a ``[TOOL:name]`` marker is
        present, the step is flagged as requiring a tool.

        If no numbered lines are found, the entire response is wrapped
        in a single reasoning step.
        """
        steps: list[PlanStep] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Detect numbered lines like "1. …" or "2) …"
            if stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in ".)":
                description = stripped[2:].strip()
            else:
                description = stripped

            # Detect [TOOL:name] markers
            tool_name: str | None = None
            requires_tool = False
            if "[TOOL:" in description.upper():
                start = description.upper().index("[TOOL:")
                end = description.index("]", start)
                tool_name = description[start + 6 : end].strip()
                description = (description[:start] + description[end + 1 :]).strip()
                # Only mark as tool step if the tool actually exists
                if tool_registry is None or tool_name in tool_registry:
                    requires_tool = True

            steps.append(
                PlanStep(
                    description=description,
                    requires_tool=requires_tool,
                    tool_name=tool_name if requires_tool else None,
                )
            )

        # Fallback: if nothing was parsed, create a single reasoning step.
        if not steps:
            steps.append(PlanStep(description=raw.strip() or "Process the task."))

        return steps
