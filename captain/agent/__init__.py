"""CAPTAIN reference multimodal agent.

This sub-package implements Layer A of the CAPTAIN architecture: a modular,
deterministic reference agent whose execution can be observed by future
CAPTAIN tracing and provenance modules.

Quick start::

    from captain.agent import Agent
    from captain.adapters.llm import MockLLMProvider
    from captain.agent.tools import create_default_tool_registry
    from captain.agent.types import TaskInput

    agent = Agent(
        llm=MockLLMProvider(responses=["1. Analyse the task"]),
        tool_registry=create_default_tool_registry(),
    )
    response = agent.run(TaskInput.from_text("Hello"))
"""

from captain.agent.agent import Agent

__all__ = ["Agent"]
