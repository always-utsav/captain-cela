"""Tests for captain.agent.types — shared agent data types."""

from __future__ import annotations

from captain.agent.types import (
    AgentResponse,
    Content,
    Modality,
    PlanStep,
    TaskInput,
    ToolCall,
)


class TestModality:
    """Tests for the Modality enum."""

    def test_text_value(self) -> None:
        assert Modality.TEXT.value == "text"

    def test_image_value(self) -> None:
        assert Modality.IMAGE.value == "image"


class TestContent:
    """Tests for the Content model."""

    def test_default_is_text(self) -> None:
        c = Content()
        assert c.modality == Modality.TEXT
        assert c.data == ""

    def test_image_content(self) -> None:
        c = Content(modality=Modality.IMAGE, data="photo.png")
        assert c.modality == Modality.IMAGE
        assert c.data == "photo.png"


class TestTaskInput:
    """Tests for the TaskInput model."""

    def test_from_text_convenience(self) -> None:
        task = TaskInput.from_text("Hello world")
        assert len(task.contents) == 1
        assert task.contents[0].modality == Modality.TEXT
        assert task.contents[0].data == "Hello world"

    def test_text_property_concatenates(self) -> None:
        task = TaskInput(
            contents=[
                Content(modality=Modality.TEXT, data="line 1"),
                Content(modality=Modality.IMAGE, data="img.png"),
                Content(modality=Modality.TEXT, data="line 2"),
            ]
        )
        assert task.text == "line 1\nline 2"

    def test_empty_task(self) -> None:
        task = TaskInput()
        assert task.text == ""
        assert task.contents == []
        assert task.metadata == {}

    def test_metadata(self) -> None:
        task = TaskInput.from_text("hi")
        task.metadata["source"] = "test"
        assert task.metadata["source"] == "test"


class TestPlanStep:
    """Tests for the PlanStep model."""

    def test_reasoning_step(self) -> None:
        step = PlanStep(description="Think about the problem")
        assert step.requires_tool is False
        assert step.tool_name is None

    def test_tool_step(self) -> None:
        step = PlanStep(
            description="Compute 2+3",
            requires_tool=True,
            tool_name="calculator",
            tool_args={"expression": "2+3"},
        )
        assert step.requires_tool is True
        assert step.tool_name == "calculator"


class TestToolCall:
    """Tests for the ToolCall model."""

    def test_construction(self) -> None:
        tc = ToolCall(tool_name="echo", arguments={"message": "hi"}, result="hi")
        assert tc.tool_name == "echo"
        assert tc.result == "hi"


class TestAgentResponse:
    """Tests for the AgentResponse model."""

    def test_defaults(self) -> None:
        resp = AgentResponse()
        assert resp.content == ""
        assert resp.tool_calls == []
        assert resp.steps == []

    def test_populated_response(self) -> None:
        resp = AgentResponse(
            content="answer",
            tool_calls=[ToolCall(tool_name="echo", result="x")],
            steps=["Step 0: did something"],
        )
        assert resp.content == "answer"
        assert len(resp.tool_calls) == 1
        assert len(resp.steps) == 1
