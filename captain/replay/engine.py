"""Counterfactual replay engine for CAPTAIN.

Produces a genuinely re-executed counterfactual
:class:`~captain.models.execution.ExecutionRun` by replaying the
CAPTAIN Stage 1 reference agent under a validated intervention.

Replay strategy -- full re-execution with intervention injection:

1. Extract baseline execution data (LLM responses, tool results,
   plan structure) from the baseline ``ExecutionRun``.
2. Apply interventions to modify extracted data (LLM responses,
   tool behaviours, task text).
3. Build a fresh ``Agent`` + ``TracedAgent`` with modified
   ``MockLLMProvider`` and wrapped tools.
4. Run ``TracedAgent.run()`` to produce a genuine new execution.
5. Link the new run to the baseline via ``parent_run_id``.

Architectural boundary::

    OBSERVATION  -- what actually happened  (Stages 2-5)
    INTERVENTION -- what we hypothetically change  (Stage 9)
    REPLAY       -- re-execution under intervention (THIS MODULE)
    CAUSAL EFFECT-- difference the replay shows     (future)

Scoped to the CAPTAIN-owned Stage 1 reference agent.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import (
    Tool,
    ToolRegistry,
    create_default_tool_registry,
)
from captain.agent.types import TaskInput
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.intervention.validation import InterventionValidator
from captain.models.enums import EventType
from captain.models.execution import ExecutionRun
from captain.tracing.traced_agent import TracedAgent

# ===================================================================
# Public types
# ===================================================================


class ReplayStatus(enum.StrEnum):
    """Outcome of a counterfactual replay attempt."""

    SUCCESS = "success"
    REJECTED = "rejected"
    FAILED = "failed"


class CounterfactualResult(BaseModel):
    """Result of a counterfactual replay.

    Attributes:
        status: Replay outcome.
        counterfactual_run: The new execution (None on reject/fail).
        baseline_run_id: ID of the baseline run.
        intervention_ids: IDs of applied interventions.
        rejection_reason: Why replay was rejected/failed.
        metadata: Additional replay context.
    """

    status: ReplayStatus
    counterfactual_run: ExecutionRun | None = None
    baseline_run_id: str
    intervention_ids: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Internal: tool wrapper
# ===================================================================


class _OverrideTool(Tool):
    """Wraps a tool to return overrides at specific calls."""

    def __init__(
        self,
        wrapped: Tool,
        overrides: dict[int, str],
    ) -> None:
        self._wrapped = wrapped
        self._overrides = overrides
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._wrapped.name

    @property
    def description(self) -> str:
        return self._wrapped.description

    def execute(self, args: dict[str, str]) -> str:
        idx = self._call_count
        self._call_count += 1
        if idx in self._overrides:
            return self._overrides[idx]
        return self._wrapped.execute(args)


class _UnsupportedError(Exception):
    """Raised when an intervention cannot be replayed."""


# ===================================================================
# Internal: baseline extraction
# ===================================================================

_ESSENTIAL = frozenset(
    {
        EventType.INPUT,
        EventType.PLANNING,
        EventType.OUTPUT,
        EventType.MEMORY_WRITE,
    }
)


def _extract_baseline(run: ExecutionRun) -> dict[str, Any]:
    """Extract structured execution data from baseline."""
    events = sorted(run.events, key=lambda e: e.sequence_number)
    ebi = {e.event_id: e for e in events}
    abi = {a.artifact_id: a for a in run.artifacts}

    task_text = run.task_input

    # Plan
    pe = [e for e in events if e.event_type == EventType.PLANNING]
    if not pe:
        msg = "Baseline has no PLANNING event"
        raise ValueError(msg)
    descs: list[str] = pe[0].payload.get("steps", [])

    # Categorise steps
    ts: dict[int, dict[str, Any]] = {}
    rs: dict[int, dict[str, Any]] = {}
    for evt in events:
        si = evt.payload.get("step_index")
        if si is None:
            continue
        if evt.event_type == EventType.TOOL_CALL:
            ts.setdefault(si, {})["call"] = evt
        elif evt.event_type == EventType.TOOL_RESULT:
            ts.setdefault(si, {})["result"] = evt
        elif evt.event_type == EventType.REASONING:
            rs[si] = {"event": evt}

    idxs = sorted(set(ts.keys()) | set(rs.keys()))
    steps: list[dict[str, Any]] = []
    for idx in idxs:
        if idx in ts:
            tc = ts[idx].get("call")
            tr = ts[idx].get("result")
            steps.append(
                {
                    "step_index": idx,
                    "is_tool": True,
                    "tool_name": (tc.payload.get("tool_name") if tc else None),
                    "result": (tr.payload.get("result", "") if tr else ""),
                    "event_id": tc.event_id if tc else "",
                    "result_event_id": (tr.event_id if tr else None),
                }
            )
        else:
            r = rs[idx]["event"]
            steps.append(
                {
                    "step_index": idx,
                    "is_tool": False,
                    "result": r.payload.get("result", ""),
                    "event_id": r.event_id,
                }
            )

    # LLM responses
    r_results = [s["result"] for s in steps if not s["is_tool"]]
    oe = [e for e in events if e.event_type == EventType.OUTPUT]
    final = oe[0].payload.get("content", "") if oe else ""

    tm: dict[int, str] = {s["step_index"]: s["tool_name"] for s in steps if s["is_tool"]}
    lines: list[str] = []
    for i, d in enumerate(descs):
        if i in tm:
            lines.append(f"{i + 1}. [TOOL:{tm[i]}] {d}")
        else:
            lines.append(f"{i + 1}. {d}")
    plan_text = "\n".join(lines)

    llm = [plan_text, *r_results, final]

    # Tool call map: step_idx -> (tool_name, per-tool call_idx)
    tcm: dict[int, tuple[str, int]] = {}
    tc_counts: dict[str, int] = {}
    for s in steps:
        if s["is_tool"] and s["tool_name"]:
            nm = s["tool_name"]
            ci = tc_counts.get(nm, 0)
            tc_counts[nm] = ci + 1
            tcm[s["step_index"]] = (nm, ci)

    return {
        "task_text": task_text,
        "plan_descs": descs,
        "plan_text": plan_text,
        "steps": steps,
        "llm": llm,
        "r_results": r_results,
        "final": final,
        "tcm": tcm,
        "ebi": ebi,
        "abi": abi,
    }


# ===================================================================
# Internal: artifact boundary resolution
# ===================================================================


def _art_boundary(
    aid: str,
    run: ExecutionRun,
    ebi: dict[str, Any],
    abi: dict[str, Any],
) -> tuple[str, int | None]:
    """Map artifact to producing execution boundary."""
    art = abi.get(aid)
    if art is None:
        return ("unknown", None)

    pid = art.producer_event_id
    if pid and pid in ebi:
        p = ebi[pid]
        et = p.event_type
        si = p.payload.get("step_index")
        if et == EventType.INPUT:
            return ("input", None)
        if et == EventType.TOOL_CALL:
            return ("tool", si)
        if et == EventType.OUTPUT:
            return ("output", None)
        if et == EventType.PLANNING:
            return ("planning", None)

    for evt in run.events:
        if aid in evt.output_artifact_ids:
            et = evt.event_type
            si = evt.payload.get("step_index")
            if et == EventType.REASONING:
                return ("reasoning", si)
            if et == EventType.PLANNING:
                return ("planning", None)
            if et == EventType.OUTPUT:
                return ("output", None)

    return ("unknown", None)


def _r_idx(si: int | None, steps: list[dict[str, Any]]) -> int | None:
    """Index in reasoning_results for a step_index."""
    if si is None:
        return None
    ri = 0
    for s in steps:
        if s["step_index"] == si and not s["is_tool"]:
            return ri
        if not s["is_tool"]:
            ri += 1
    return None


# ===================================================================
# Internal: apply interventions
# ===================================================================


def _apply(
    iset: InterventionSet,
    data: dict[str, Any],
    run: ExecutionRun,
) -> dict[str, Any]:
    """Apply interventions to produce modified replay inputs.

    When tool results are overridden, downstream LLM responses are
    updated to reflect the new tool output.  This simulates a
    responsive LLM that incorporates tool results into its reasoning
    and final output.
    """
    task = data["task_text"]
    llm = list(data["llm"])
    ovr: dict[str, dict[int, str]] = {}
    dis: set[int] = set()
    applied: list[str] = []

    ebi = data["ebi"]
    abi = data["abi"]
    steps = data["steps"]
    tcm = data["tcm"]

    # Track original tool results for causal propagation
    tool_result_changes: list[tuple[str, str]] = []

    def _rv(intv: Intervention) -> str:
        v = intv.replacement_value
        return str(v) if v is not None else ""

    for intv in iset.interventions:
        it = intv.intervention_type

        if it == InterventionType.ARTIFACT_REPLACEMENT:
            task, llm, ovr = _do_art(
                intv,
                run,
                ebi,
                abi,
                steps,
                tcm,
                task,
                llm,
                ovr,
            )
            applied.append(intv.intervention_id)

        elif it == InterventionType.TOOL_RESULT_OVERRIDE:
            evt = ebi.get(intv.target_id)
            if evt:
                si = evt.payload.get("step_index")
                if si is not None and si in tcm:
                    nm, ci = tcm[si]
                    new_val = _rv(intv)
                    ovr.setdefault(nm, {})[ci] = new_val
                    applied.append(intv.intervention_id)
                    # Record original → new for propagation
                    orig = evt.payload.get("result", "")
                    if orig and orig != new_val:
                        tool_result_changes.append((orig, new_val))

        elif it == InterventionType.EVENT_DISABLE:
            evt = ebi.get(intv.target_id)
            if evt:
                if evt.event_type in _ESSENTIAL:
                    msg = f"Cannot disable {evt.event_type.value} '{intv.target_id}': essential"
                    raise _UnsupportedError(msg)
                si = evt.payload.get("step_index")
                if si is not None:
                    dis.add(si)
                    applied.append(intv.intervention_id)
                else:
                    msg = f"Cannot disable '{intv.target_id}': no step"
                    raise _UnsupportedError(msg)

        elif it == InterventionType.EVENT_OUTPUT_OVERRIDE:
            evt = ebi.get(intv.target_id)
            if evt:
                si = evt.payload.get("step_index")
                et = evt.event_type
                if et in (
                    EventType.TOOL_CALL,
                    EventType.TOOL_RESULT,
                ):
                    if si is not None and si in tcm:
                        nm, ci = tcm[si]
                        new_val = _rv(intv)
                        ovr.setdefault(nm, {})[ci] = new_val
                        # Record for propagation
                        orig = evt.payload.get("result", "")
                        if orig and orig != new_val:
                            tool_result_changes.append((orig, new_val))
                elif et == EventType.REASONING:
                    ri = _r_idx(si, steps)
                    if ri is not None:
                        llm[1 + ri] = _rv(intv)
                elif et == EventType.OUTPUT:
                    llm[-1] = _rv(intv)
                applied.append(intv.intervention_id)

    if dis:
        llm, ovr = _rebuild(data, dis, ovr)

    # ---------------------------------------------------------------
    # Causal propagation: when a tool result changes, downstream
    # LLM responses that incorporated that result must also change.
    #
    # A real LLM produces text that references tool outputs.  The
    # MockLLM's scripted responses were generated from original tool
    # results.  Propagation substitutes original result text with
    # the replacement in all downstream LLM responses (reasoning
    # steps and final output).
    #
    # This does NOT change the evaluator, the CEE formula, or
    # any causal definition.  It makes the mock agent responsive
    # to its inputs, which is the prerequisite for meaningful
    # counterfactual measurement.
    # ---------------------------------------------------------------
    if tool_result_changes:
        llm = _propagate_tool_overrides(llm, tool_result_changes)

    return {
        "task_text": task,
        "llm": llm,
        "ovr": ovr,
        "applied": applied,
    }


def _propagate_tool_overrides(
    llm: list[str],
    changes: list[tuple[str, str]],
) -> list[str]:
    """Propagate tool result changes to downstream LLM responses.

    For each (original, replacement) pair, substitute in reasoning
    responses (llm[1:-1]) and the final output (llm[-1]).

    The plan response (llm[0]) is NOT modified because it is
    generated before any tool calls.

    Scientific justification:
    -  A real LLM's reasoning output references tool results.
    -  The baseline MockLLM responses contain original tool text.
    -  When the tool result changes, the text that a responsive LLM
       would have produced also changes.
    -  This propagation simulates that dependency without requiring
       a real LLM.
    """
    result = list(llm)
    # Propagate to reasoning + final output (indices 1 onward)
    for i in range(1, len(result)):
        for orig, repl in changes:
            if orig in result[i]:
                result[i] = result[i].replace(orig, repl)
    return result


def _do_art(
    intv: Intervention,
    run: ExecutionRun,
    ebi: dict[str, Any],
    abi: dict[str, Any],
    steps: list[dict[str, Any]],
    tcm: dict[int, tuple[str, int]],
    task: str,
    llm: list[str],
    ovr: dict[str, dict[int, str]],
) -> tuple[str, list[str], dict[str, dict[int, str]]]:
    """Apply ARTIFACT_REPLACEMENT."""
    v = str(intv.replacement_value) if intv.replacement_value else ""
    kind, si = _art_boundary(intv.target_id, run, ebi, abi)
    if kind == "input":
        task = v
    elif kind == "tool" and si is not None and si in tcm:
        nm, ci = tcm[si]
        ovr.setdefault(nm, {})[ci] = v
    elif kind == "reasoning":
        ri = _r_idx(si, steps)
        if ri is not None:
            llm[1 + ri] = v
    elif kind == "output":
        llm[-1] = v
    elif kind == "planning":
        llm[0] = v
    return task, llm, ovr


def _rebuild(
    data: dict[str, Any],
    dis: set[int],
    ovr: dict[str, dict[int, str]],
) -> tuple[list[str], dict[str, dict[int, str]]]:
    """Rebuild LLM responses and remap tool overrides."""
    steps = data["steps"]
    descs = data["plan_descs"]
    final = data["final"]

    nd: list[str] = []
    nt: dict[int, str] = {}
    ni = 0
    for i, d in enumerate(descs):
        if i in dis:
            continue
        s = next((s for s in steps if s["step_index"] == i), None)
        if s and s["is_tool"]:
            nt[ni] = s["tool_name"]
        nd.append(d)
        ni += 1

    lines: list[str] = []
    for i, d in enumerate(nd):
        if i in nt:
            lines.append(f"{i + 1}. [TOOL:{nt[i]}] {d}")
        else:
            lines.append(f"{i + 1}. {d}")
    pt = "\n".join(lines)

    rr = [s["result"] for s in steps if not s["is_tool"] and s["step_index"] not in dis]
    llm = [pt, *rr, final]

    # Remap tool override indices
    oc: dict[str, int] = {}
    nc: dict[str, int] = {}
    o2n: dict[tuple[str, int], int] = {}
    for s in steps:
        if s["is_tool"] and s["tool_name"]:
            nm = s["tool_name"]
            oi = oc.get(nm, 0)
            oc[nm] = oi + 1
            if s["step_index"] not in dis:
                nci = nc.get(nm, 0)
                nc[nm] = nci + 1
                o2n[(nm, oi)] = nci

    remapped: dict[str, dict[int, str]] = {}
    for nm, os in ovr.items():
        no: dict[int, str] = {}
        for oi, val in os.items():
            k = (nm, oi)
            if k in o2n:
                no[o2n[k]] = val
        if no:
            remapped[nm] = no

    return llm, remapped


# ===================================================================
# Internal: replay execution
# ===================================================================


def _run_replay(
    mods: dict[str, Any],
    reg: ToolRegistry,
    baseline: ExecutionRun,
    iset: InterventionSet,
) -> ExecutionRun:
    """Execute counterfactual via TracedAgent."""
    llm = MockLLMProvider(responses=mods["llm"])

    registry = ToolRegistry()
    ovr = mods["ovr"]
    for tool in reg.list_tools():
        if tool.name in ovr:
            registry.register(_OverrideTool(tool, ovr[tool.name]))
        else:
            registry.register(tool)

    agent = Agent(llm=llm, tool_registry=registry)
    traced = TracedAgent(agent)

    task = TaskInput.from_text(mods["task_text"])
    meta = {
        "is_counterfactual": True,
        "baseline_run_id": baseline.run_id,
        "intervention_ids": [i.intervention_id for i in iset.interventions],
    }

    _resp, collector = traced.run(task, metadata=meta)
    cf = collector.get_run()
    cf.parent_run_id = baseline.run_id
    return cf


# ===================================================================
# Public engine
# ===================================================================


class CounterfactualReplayEngine:
    """Engine for counterfactual replay of reference agent runs.

    Scoped to the CAPTAIN Stage 1 reference agent.  Re-executes
    the agent under validated interventions to produce a genuine
    new ``ExecutionRun``.

    Usage::

        result = CounterfactualReplayEngine.replay(
            baseline_run, intervention
        )
        if result.status == ReplayStatus.SUCCESS:
            cf_run = result.counterfactual_run
    """

    @staticmethod
    def replay(
        baseline_run: ExecutionRun,
        intervention: Intervention | InterventionSet,
        *,
        tool_registry: ToolRegistry | None = None,
    ) -> CounterfactualResult:
        """Execute a counterfactual replay.

        Args:
            baseline_run: The observed execution to replay.
            intervention: The intervention(s) to apply.
            tool_registry: Optional tool registry.  Defaults
                to the standard reference-agent registry.

        Returns:
            :class:`CounterfactualResult` with replay outcome.
        """
        if isinstance(intervention, Intervention):
            iset = InterventionSet(
                baseline_run_id=intervention.baseline_run_id,
                interventions=[intervention],
            )
        else:
            iset = intervention

        ids = [i.intervention_id for i in iset.interventions]

        # Validate
        val = InterventionValidator.validate_set(iset, baseline_run)
        if not val.is_valid:
            return CounterfactualResult(
                status=ReplayStatus.REJECTED,
                baseline_run_id=baseline_run.run_id,
                intervention_ids=ids,
                rejection_reason="; ".join(e.message for e in val.errors),
            )

        # Extract baseline
        try:
            data = _extract_baseline(baseline_run)
        except Exception as exc:
            return CounterfactualResult(
                status=ReplayStatus.FAILED,
                baseline_run_id=baseline_run.run_id,
                intervention_ids=ids,
                rejection_reason=(f"Baseline extraction failed: {exc}"),
            )

        # Apply interventions
        try:
            mods = _apply(iset, data, baseline_run)
        except _UnsupportedError as exc:
            return CounterfactualResult(
                status=ReplayStatus.REJECTED,
                baseline_run_id=baseline_run.run_id,
                intervention_ids=ids,
                rejection_reason=str(exc),
            )

        # Execute replay
        try:
            reg = tool_registry or create_default_tool_registry()
            cf = _run_replay(mods, reg, baseline_run, iset)
        except Exception as exc:
            return CounterfactualResult(
                status=ReplayStatus.FAILED,
                baseline_run_id=baseline_run.run_id,
                intervention_ids=ids,
                rejection_reason=(f"Replay failed: {exc}"),
            )

        return CounterfactualResult(
            status=ReplayStatus.SUCCESS,
            counterfactual_run=cf,
            baseline_run_id=baseline_run.run_id,
            intervention_ids=ids,
            metadata={
                "applied": mods["applied"],
                "is_counterfactual": True,
            },
        )
