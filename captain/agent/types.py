"""Shared data types for the CAPTAIN reference agent.

Defines the canonical types used across all agent components: task inputs,
content items (text and image), plan steps, tool call records, and agent
responses.  All types are :mod:`pydantic` models for validation and
serialization.

These types are intentionally kept simple in Stage 1.  They will be extended
(not replaced) as CAPTAIN adds tracing and provenance in later stages.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class Modality(enum.StrEnum):
    """Supported content modalities."""

    TEXT = "text"
    IMAGE = "image"


class Content(BaseModel):
    """A single piece of content carried through the agent pipeline.

    Attributes:
        modality: Whether this content is text or an image.
        data: The payload.  For ``TEXT`` this is a plain string.  For
            ``IMAGE`` this is a placeholder description or reference
            (actual image bytes are out of scope for Stage 1).
    """

    modality: Modality = Modality.TEXT
    data: str = ""


class TaskInput(BaseModel):
    """Input provided to the agent for a single run.

    Attributes:
        contents: Ordered list of content items (text, images, …).
        metadata: Arbitrary key/value pairs for caller-supplied context.
    """

    contents: list[Content] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- convenience helpers ---------------------------------------------------

    @property
    def text(self) -> str:
        """Concatenated text of all ``TEXT`` content items."""
        return "\n".join(c.data for c in self.contents if c.modality == Modality.TEXT)

    @classmethod
    def from_text(cls, text: str) -> TaskInput:
        """Create a :class:`TaskInput` containing a single text item."""
        return cls(contents=[Content(modality=Modality.TEXT, data=text)])


class PlanStep(BaseModel):
    """A single step produced by the planner.

    Attributes:
        description: Human-readable description of what the step does.
        requires_tool: Whether the step needs a tool invocation.
        tool_name: Name of the tool to invoke (if *requires_tool* is True).
        tool_args: Arguments to pass to the tool.
    """

    description: str
    requires_tool: bool = False
    tool_name: str | None = None
    tool_args: dict[str, str] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Record of a single tool invocation.

    Attributes:
        tool_name: Name of the tool that was called.
        arguments: Arguments passed to the tool.
        result: String result returned by the tool.
    """

    tool_name: str
    arguments: dict[str, str] = Field(default_factory=dict)
    result: str = ""


class AgentResponse(BaseModel):
    """Final output produced by the agent after a run.

    Attributes:
        content: The synthesised response text.
        tool_calls: Ordered log of every tool invocation during the run.
        steps: Descriptions of the steps the agent executed.
    """

    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
