"""Traced agent wrapper for the CAPTAIN reference agent.

The :class:`TracedAgent` wraps a Stage 1 :class:`~captain.agent.agent.Agent`
and records canonical events/artifacts via a :class:`TraceCollector` at each
execution boundary.

The original ``Agent.run()`` is **not** modified.  Instead, ``TracedAgent``
re-implements the pipeline by calling the same sub-components (planner,
reasoner, response generator) while intercepting each boundary to record
trace events.

Usage::

    from captain.adapters.llm import MockLLMProvider
    from captain.agent.agent import Agent
    from captain.tracing import TracedAgent

    llm = MockLLMProvider(responses=[...])
    agent = Agent(llm=llm)
    traced = TracedAgent(agent)

    response, run = traced.run(TaskInput.from_text("What is 2+2?"))
    # response: normal AgentResponse
    # run: canonical ExecutionRun with events/artifacts
"""

from __future__ import annotations

from typing import Any

from captain.agent.agent import Agent
from captain.agent.memory import WorkingMemory
from captain.agent.types import AgentResponse, Content, Modality, TaskInput, ToolCall
from captain.models.enums import ArtifactType, EventType
from captain.tracing.collector import TraceCollector


class TracedAgent:
    """Wraps a Stage 1 :class:`Agent` with CAPTAIN trace collection.

    The traced agent produces the **same** :class:`AgentResponse` as an
    untraced agent while additionally recording a canonical
    :class:`~captain.models.execution.ExecutionRun`.

    Args:
        agent: The Stage 1 agent to observe.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def run(
        self,
        task_input: TaskInput,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[AgentResponse, TraceCollector]:
        """Execute the agent pipeline with trace collection.

        Args:
            task_input: The incoming task.
            metadata: Optional metadata attached to the run.

        Returns:
            A ``(response, collector)`` tuple.  The collector holds the
            completed :class:`~captain.models.execution.ExecutionRun`
            accessible via ``collector.get_run()``.

        Raises:
            Exception: Any exception raised by the agent is re-raised
                after the trace is marked FAILED.
        """
        collector = TraceCollector()
        collector.start_run(task_text=task_input.text, metadata=metadata)

        try:
            response = self._execute_traced(task_input, collector)
            collector.complete_run()
        except Exception:
            collector.fail_run()
            raise

        return response, collector

    # ------------------------------------------------------------------
    # Internal traced pipeline
    # ------------------------------------------------------------------

    def _execute_traced(
        self,
        task_input: TaskInput,
        collector: TraceCollector,
    ) -> AgentResponse:
        """Replicate Agent.run() pipeline with trace instrumentation."""
        agent = self._agent

        # --- INPUT event ---
        input_event = collector.record_event(
            EventType.INPUT,
            component="agent",
            payload={"text": task_input.text},
        )
        # Record input artifacts (text + image references)
        input_artifact_ids = self._record_input_artifacts(
            task_input.contents, collector, input_event.event_id
        )
        if input_artifact_ids:
            input_event.output_artifact_ids = input_artifact_ids

        # --- setup memory (same as Agent.run) ---
        memory = agent._memory if agent._memory is not None else WorkingMemory()
        memory.store("task", task_input.text)

        # --- MEMORY_WRITE for task storage ---
        collector.record_event(
            EventType.MEMORY_WRITE,
            component="agent",
            payload={"key": "task", "value": task_input.text},
        )

        # --- PLANNING ---
        plan_steps = agent._planner.plan(task_input, memory, agent._tool_registry)
        plan_descriptions = [s.description for s in plan_steps]

        planning_event = collector.record_event(
            EventType.PLANNING,
            component="planner",
            input_artifact_ids=input_artifact_ids,
            payload={"step_count": len(plan_steps), "steps": plan_descriptions},
        )

        # Record plan as artifact
        plan_artifact = collector.record_artifact(
            ArtifactType.STRUCTURED_DATA,
            value={"steps": plan_descriptions},
            producer_event_id=planning_event.event_id,
        )
        planning_event.output_artifact_ids = [plan_artifact.artifact_id]

        # --- EXECUTE STEPS ---
        tool_calls: list[ToolCall] = []
        step_descriptions: list[str] = []
        # Stage 14.1: Track tool result artifacts for multi-channel
        # evidence flow.  These are passed as input_artifact_ids to
        # downstream REASONING and OUTPUT events, creating the
        # provenance chain required for channel-level intervention.
        tool_result_artifact_ids: list[str] = []

        for idx, step in enumerate(plan_steps):
            if step.requires_tool and step.tool_name:
                # TOOL_CALL event
                tool_call_event = collector.record_event(
                    EventType.TOOL_CALL,
                    component=f"tool:{step.tool_name}",
                    payload={
                        "tool_name": step.tool_name,
                        "arguments": step.tool_args,
                        "step_index": idx,
                    },
                )

                # Execute the step
                result, tool_call = agent._reasoner.execute_step(
                    step, memory, agent._tool_registry, step_index=idx
                )

                # Record tool result artifact
                result_artifact = collector.record_artifact(
                    ArtifactType.TOOL_OUTPUT,
                    value=result,
                    producer_event_id=tool_call_event.event_id,
                )
                tool_result_artifact_ids.append(result_artifact.artifact_id)

                # TOOL_RESULT event (parent = TOOL_CALL)
                collector.record_event(
                    EventType.TOOL_RESULT,
                    component=f"tool:{step.tool_name}",
                    parent_event_id=tool_call_event.event_id,
                    input_artifact_ids=[result_artifact.artifact_id],
                    output_artifact_ids=[result_artifact.artifact_id],
                    payload={
                        "tool_name": step.tool_name,
                        "result": result,
                        "step_index": idx,
                    },
                )

                if tool_call is not None:
                    tool_calls.append(tool_call)
            else:
                # REASONING event (LLM-based step)
                result, tool_call = agent._reasoner.execute_step(
                    step, memory, agent._tool_registry, step_index=idx
                )

                reasoning_artifact = collector.record_artifact(
                    ArtifactType.MODEL_OUTPUT,
                    value=result,
                )

                collector.record_event(
                    EventType.REASONING,
                    component="reasoner",
                    # Stage 14.1: consume tool result artifacts to create
                    # evidence-flow edges from tool results to reasoning.
                    input_artifact_ids=list(tool_result_artifact_ids),
                    output_artifact_ids=[reasoning_artifact.artifact_id],
                    payload={
                        "step_description": step.description,
                        "result": result,
                        "step_index": idx,
                    },
                )

            # MEMORY_WRITE for step result storage
            collector.record_event(
                EventType.MEMORY_WRITE,
                component="memory",
                payload={
                    "key": f"step_{idx}_result",
                    "value": result,
                },
            )

            step_descriptions.append(f"Step {idx}: {step.description} → {result}")

        # --- OUTPUT ---
        response = agent._response_generator.generate(
            task_input, memory, tool_calls, step_descriptions
        )

        output_artifact = collector.record_artifact(
            ArtifactType.TEXT,
            value=response.content,
        )

        output_event = collector.record_event(
            EventType.OUTPUT,
            component="response_generator",
            # Stage 14.1: consume tool result artifacts for provenance
            input_artifact_ids=list(tool_result_artifact_ids),
            output_artifact_ids=[output_artifact.artifact_id],
            payload={"content": response.content},
        )
        output_artifact.producer_event_id = output_event.event_id

        return response

    @staticmethod
    def _record_input_artifacts(
        contents: list[Content],
        collector: TraceCollector,
        producer_event_id: str,
    ) -> list[str]:
        """Create artifacts for each input content item."""
        artifact_ids: list[str] = []
        for content in contents:
            if content.modality == Modality.TEXT:
                art = collector.record_artifact(
                    ArtifactType.TEXT,
                    value=content.data,
                    producer_event_id=producer_event_id,
                )
            elif content.modality == Modality.IMAGE:
                art = collector.record_artifact(
                    ArtifactType.IMAGE,
                    reference=content.data,
                    producer_event_id=producer_event_id,
                )
            else:
                art = collector.record_artifact(
                    ArtifactType.TEXT,
                    value=content.data,
                    producer_event_id=producer_event_id,
                )
            artifact_ids.append(art.artifact_id)
        return artifact_ids
