"""LLM provider abstraction for CAPTAIN.

Defines the :class:`LLMProvider` interface and a deterministic
:class:`MockLLMProvider` that does not require paid API keys.

Future real providers (OpenAI, Anthropic, local models, …) should implement
:class:`LLMProvider` without changing agent code.  Provider-specific modules
should live under ``captain/adapters/`` and be registered via configuration.
"""

from __future__ import annotations

import abc
from typing import Any


class LLMProvider(abc.ABC):
    """Abstract interface for large-language-model backends.

    Every provider must implement :meth:`generate`.  The interface is
    intentionally minimal so that future tracing hooks can intercept
    calls transparently.
    """

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a text completion.

        Args:
            prompt: The user/task prompt.
            system_prompt: Optional system-level instruction.
            context: Optional key/value context passed to the provider.

        Returns:
            The generated text.
        """


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM that returns pre-configured responses.

    The mock operates in two modes:

    1. **Scripted** - if *responses* is provided, successive calls to
       :meth:`generate` return the next response in order (cycling if
       the list is exhausted).
    2. **Echo** - when no scripted responses remain (or none were
       provided), the prompt is echoed back verbatim.

    This provider requires no network access and no API keys.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = list(responses) if responses else []
        self._index: int = 0

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Return the next scripted response, or echo the prompt."""
        if self._responses:
            result = self._responses[self._index % len(self._responses)]
            self._index += 1
            return result
        return prompt
