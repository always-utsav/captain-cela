"""Response generator for the CAPTAIN reference agent.

The :class:`ResponseGenerator` synthesises a final answer from the
accumulated working memory after all plan steps have been executed.
"""

from __future__ import annotations

from captain.adapters.llm import LLMProvider
from captain.agent.memory import WorkingMemory
from captain.agent.types import AgentResponse, TaskInput, ToolCall


class ResponseGenerator:
    """Produces the final :class:`AgentResponse` from memory contents.

    Attributes:
        llm: The language-model provider used for response synthesis.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def generate(
        self,
        task_input: TaskInput,
        memory: WorkingMemory,
        tool_calls: list[ToolCall],
        steps: list[str],
    ) -> AgentResponse:
        """Synthesise a final response.

        Args:
            task_input: The original task.
            memory: Working memory containing all intermediate results.
            tool_calls: Ordered log of tool invocations.
            steps: Descriptions of executed steps.

        Returns:
            A fully populated :class:`AgentResponse`.
        """
        prompt = (
            f"Original task: {task_input.text}\n\n"
            f"Execution results:\n{memory.to_context_string()}\n\n"
            "Synthesise a concise final answer."
        )
        content = self._llm.generate(
            prompt,
            system_prompt=(
                "You are a response synthesiser. Combine the execution "
                "results into a clear, concise answer to the original task."
            ),
        )
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            steps=steps,
        )
