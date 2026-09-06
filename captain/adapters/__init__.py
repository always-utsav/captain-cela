"""Adapters for external systems.

Adapters translate between CAPTAIN's canonical internal representations and
the APIs of external services (LLMs, databases, agent frameworks, etc.).
CAPTAIN core logic must never depend directly on vendor-specific response
objects.

Currently implemented adapters:

- :mod:`captain.adapters.llm` — LLM provider abstraction with a
  deterministic :class:`~captain.adapters.llm.MockLLMProvider`.
"""
