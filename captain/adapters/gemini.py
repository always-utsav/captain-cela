"""Gemini LLM provider for real-agent validation.

Uses the Google Generative AI SDK to provide real LLM responses
within CAPTAIN's provider abstraction.

IMPORTANT: This provider does NOT modify CELA semantics.
It is an execution backend replacement for MockLLMProvider.
The actual LLM receives the actual modified evidence/environment
during counterfactual replay — no simulator-forced substitution.

Configuration:
    Set GEMINI_API_KEY as an environment variable or in .env file.
    NEVER commit the API key to source code or Git.
"""

from __future__ import annotations

import os
from typing import Any

from captain.adapters.llm import LLMProvider


def _load_env() -> None:
    """Load .env file if present (no external dependency)."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env",
    )
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


class GeminiProvider(LLMProvider):
    """Real LLM provider using Google Gemini API.

    Records model version, configuration, and call metadata
    for reproducibility documentation.

    The provider NEVER forces the LLM to react to an intervention.
    If the model ignores an intervention and CEE=0, that is a
    legitimate result.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        api_key: str | None = None,
    ) -> None:
        _load_env()
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. "
                "Set it as environment variable or in .env file."
            )

        self._model_name = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._call_count = 0
        self._total_tokens = 0

        # Lazy import to avoid hard dependency
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]

            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                },
            )
            self._available = True
        except ImportError:
            self._model = None
            self._available = False
        except Exception:
            self._model = None
            self._available = False

    @property
    def available(self) -> bool:
        """Whether the Gemini API is configured and accessible."""
        return self._available

    @property
    def model_info(self) -> dict[str, Any]:
        """Model metadata for reproducibility records."""
        return {
            "provider": "google_gemini",
            "model": self._model_name,
            "temperature": self._temperature,
            "max_output_tokens": self._max_output_tokens,
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
        }

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a response using Gemini.

        The model receives the ACTUAL prompt including any
        intervention-modified evidence. No simulator substitution
        is applied.
        """
        if not self._available or self._model is None:
            raise RuntimeError("Gemini API not available")

        full_prompt = ""
        if system_prompt:
            full_prompt += f"System: {system_prompt}\n\n"
        if context:
            ctx_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            full_prompt += f"Context:\n{ctx_str}\n\n"
        full_prompt += prompt

        try:
            response = self._model.generate_content(full_prompt)
            self._call_count += 1

            if hasattr(response, "usage_metadata"):
                meta = response.usage_metadata
                if hasattr(meta, "total_token_count"):
                    self._total_tokens += meta.total_token_count

            if response.text:
                return str(response.text)
            return ""
        except Exception as e:
            # Record but don't crash — allows graceful degradation
            return f"[GEMINI_ERROR: {type(e).__name__}]"
