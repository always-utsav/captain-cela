"""CELA benchmark scenarios — Stage 16.

Parameterized benchmark scenario generators with independent
ground-truth mechanisms for controlled causal evaluation.

Information flow::

    CausalMechanismSpec (hidden)
        -> scenario generator constructs agent config + evaluator
        -> TracedAgent execution -> ExecutionRun (observable)
        -> CELA / baselines observe ONLY run, graph, failure, candidates
        -> MetricEvaluator compares method output against ScenarioGroundTruth

The hidden causal mechanism is NEVER passed to methods.
Ground truth is used ONLY by the post-hoc metric evaluator.
"""

from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import (
    FixedValueTool,
    ToolRegistry,
    create_default_tool_registry,
)
from captain.agent.types import TaskInput
from captain.analysis.estimator import FailureEvaluator
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    ChannelIntervention,
    Failure,
    FailureType,
)
from captain.models.execution import ExecutionRun
from captain.models.ids import _is_deterministic, _next_deterministic_id
from captain.tracing.traced_agent import TracedAgent

# ===================================================================
# Hidden causal mechanism (never visible to methods)
# ===================================================================


class CausalMechanism(enum.StrEnum):
    """Classification of hidden causal structure."""

    SINGLE_CHANNEL = "single_channel"
    REDUNDANT_OR = "redundant_or"
    COMPLEMENTARY_AND = "complementary_and"
    DISTRACTOR = "distractor"
    CASCADE = "cascade"
    COST_ASYMMETRIC = "cost_asymmetric"


class CausalMechanismSpec(BaseModel):
    """Hidden causal mechanism parameters.

    Used by the scenario generator to construct the environment
    and evaluator. NEVER passed to CELA or baselines.
    """

    mechanism: CausalMechanism
    failure_keywords: list[str] = Field(default_factory=list)
    keyword_logic: str = "any"  # "any" (OR) or "all" (AND)
    causal_tool_names: list[str] = Field(default_factory=list)
    distractor_tool_names: list[str] = Field(default_factory=list)


# ===================================================================
# Ground truth (post-hoc evaluation only)
# ===================================================================


class ScenarioGroundTruth(BaseModel):
    """Independent ground truth for benchmark evaluation.

    Contains causal structure, prevention requirements, and
    expected outcomes. Used ONLY by the MetricEvaluator after
    all methods have produced their selections.

    NEVER passed to CELA or baselines.
    """

    scenario_id: str
    family: str
    seed: int

    # Hidden causal mechanism
    mechanism: CausalMechanismSpec

    # Attribution ground truth
    causal_channel_ids: list[str] = Field(default_factory=list)
    irrelevant_channel_ids: list[str] = Field(default_factory=list)

    # Localization ground truth
    causal_origin_ids: list[str] = Field(default_factory=list)
    propagation_channel_ids: list[str] = Field(default_factory=list)
    failure_actuator_ids: list[str] = Field(default_factory=list)

    # Prevention ground truth
    required_prevention_sets: list[list[str]] = Field(default_factory=list)

    # Interaction structure
    redundancy_groups: list[list[str]] = Field(default_factory=list)
    complementary_groups: list[list[str]] = Field(default_factory=list)

    # Expected factual/counterfactual outcomes
    factual_outcome: bool = True
    single_intervention_outcomes: dict[str, bool] = Field(default_factory=dict)
    joint_intervention_outcome: bool | None = None

    # Cost structure
    channel_costs: dict[str, float] = Field(default_factory=dict)
    budget: float | None = None
    expected_budget_feasible_set: list[str] | None = None


# ===================================================================
# Benchmark scenario
# ===================================================================


class BenchmarkScenario(BaseModel):
    """Complete benchmark scenario for evaluation.

    Contains everything needed to evaluate methods:
    - The observable execution data (run, graph, failure, candidates)
    - The hidden ground truth (for post-hoc metrics only)
    - The failure evaluator function reference

    Methods receive: run, graph, failure, candidates, interventions.
    Methods do NOT receive: ground_truth, mechanism.
    """

    scenario_id: str = Field(
        default_factory=lambda: (
            _next_deterministic_id("bench_")
            if _is_deterministic()
            else f"bench_{uuid.uuid4().hex[:12]}"
        )
    )
    family: str
    seed: int

    # Observable data (available to methods)
    run: ExecutionRun
    evidence_graph: EvidenceFlowGraph
    failure: Failure
    candidates: list[ChannelIntervention] = Field(default_factory=list)

    # Hidden (NOT available to methods)
    ground_truth: ScenarioGroundTruth

    model_config = {"arbitrary_types_allowed": True}


# ===================================================================
# Evaluator construction
# ===================================================================


def _build_keyword_evaluator(
    keywords: list[str],
    logic: str,
) -> FailureEvaluator:
    """Build a failure evaluator from keyword specification.

    The evaluator checks the execution output content.
    It does NOT check which interventions were applied.
    """

    def evaluator(run: ExecutionRun) -> bool:
        # Gather all output text from the run
        output_text = ""
        for evt in run.events:
            if evt.payload:
                output_text += str(evt.payload) + " "
        for art in run.artifacts:
            if art.value:
                output_text += str(art.value) + " "

        output_lower = output_text.lower()

        if logic == "all":
            # AND: fail only if ALL keywords present
            return all(kw.lower() in output_lower for kw in keywords)
        else:
            # OR: fail if ANY keyword present
            return any(kw.lower() in output_lower for kw in keywords)

    return evaluator


# ===================================================================
# Shared helpers
# ===================================================================


def _execute_scenario(
    responses: list[str],
    task: str,
    tool_registry: ToolRegistry | None = None,
) -> ExecutionRun:
    """Execute a traced agent with scripted responses."""
    llm = MockLLMProvider(responses=responses)
    reg = tool_registry or create_default_tool_registry()
    agent = Agent(llm=llm, tool_registry=reg)
    traced = TracedAgent(agent)
    _resp, collector = traced.run(TaskInput.from_text(task))
    return collector.get_run()


def _build_graph(run: ExecutionRun) -> EvidenceFlowGraph:
    """Build evidence flow graph from execution run."""
    builder = EvidenceLineageBuilder(run)
    evidence, txs = builder.build()
    return EvidenceFlowGraph.from_lineage(evidence, txs)


def _get_tool_channel_interventions(
    run: ExecutionRun,
    graph: EvidenceFlowGraph,
    failure: Failure,
) -> list[ChannelIntervention]:
    """Get channel interventions via FailureAnalyzer."""
    analyzer = FailureAnalyzer(graph, failure)
    return analyzer.interventions()


def _find_channels_by_tool(
    run: ExecutionRun,
    graph: EvidenceFlowGraph,
    interventions: list[ChannelIntervention],
    tool_name: str,
) -> list[ChannelIntervention]:
    """Find interventions associated with a specific tool."""
    from captain.models.enums import EventType

    # Find tool_call event IDs for the given tool
    tool_event_ids: set[str] = set()
    for evt in run.events:
        if evt.event_type == EventType.TOOL_CALL:
            payload = evt.payload if isinstance(evt.payload, dict) else {}
            if payload.get("tool_name") == tool_name:
                tool_event_ids.add(evt.event_id)

    # Find TOOL_RESULT events that are children of these tool calls
    tool_result_event_ids: set[str] = set()
    for evt in run.events:
        if evt.event_type == EventType.TOOL_RESULT and evt.parent_event_id in tool_event_ids:
            tool_result_event_ids.add(evt.event_id)

    # Find evidence produced by these events
    tool_evidence_ids: set[str] = set()
    for evi in graph.evidence:
        if evi.creation_event_id in tool_event_ids | tool_result_event_ids:
            tool_evidence_ids.add(evi.evidence_id)

    # Filter interventions that involve these evidence IDs
    result: list[ChannelIntervention] = []
    for ci in interventions:
        if ci.source_evidence_id in tool_evidence_ids:
            result.append(ci)
    return result


# ===================================================================
# Parameterized scenario generators
# ===================================================================


def generate_single_cause(
    *,
    seed: int = 42,
    causal_tool: str = "calculator",
    failure_keyword: str = "42",
) -> BenchmarkScenario:
    """BF-A: Single-cause scenario.

    One tool produces failure-causing content; other tools
    are structurally present but causally irrelevant.
    """
    responses = [
        f"1. [TOOL:{causal_tool}] Compute 6*7\n2. [TOOL:echo] Say hello\n3. Summarise",
        f"The calculator says {failure_keyword} and the echo says hello world",
        f"The answer is {failure_keyword} and hello world.",
    ]

    # Use FixedValueTool so tool results match the LLM's scripted
    # responses.  This establishes the genuine causal chain:
    #   tool result → LLM reasoning → evaluator outcome
    reg = ToolRegistry()
    reg.register(FixedValueTool(causal_tool, failure_keyword))
    reg.register(FixedValueTool("echo", "hello world"))

    run = _execute_scenario(responses, "Compute and greet", tool_registry=reg)
    graph = _build_graph(run)

    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains failure keyword",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    causal_channels = _find_channels_by_tool(run, graph, all_interventions, causal_tool)
    distractor_channels = _find_channels_by_tool(run, graph, all_interventions, "echo")

    causal_ids = [ci.intervention_id for ci in causal_channels]
    distractor_ids = [ci.intervention_id for ci in distractor_channels]

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.SINGLE_CHANNEL,
        failure_keywords=[failure_keyword],
        keyword_logic="any",
        causal_tool_names=[causal_tool],
        distractor_tool_names=["echo"],
    )

    evaluator = _build_keyword_evaluator([failure_keyword], "any")

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_a_{seed}",
        family="BF-A",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=causal_ids,
        irrelevant_channel_ids=distractor_ids,
        causal_origin_ids=causal_ids,
        propagation_channel_ids=[],
        failure_actuator_ids=causal_ids,
        required_prevention_sets=[causal_ids] if causal_ids else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(causal_ids, False),
            **dict.fromkeys(distractor_ids, True),
        },
        joint_intervention_outcome=False,
    )

    # Store evaluator ref in scenario metadata
    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-A",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    # Attach evaluator as a non-serialized attribute
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def generate_redundant(
    *,
    seed: int = 42,
    failure_keywords: list[str] | None = None,
) -> BenchmarkScenario:
    """BF-B: Redundant (OR) scenario.

    Multiple tools independently produce failure-causing content.
    Blocking only one is insufficient — both must be blocked.
    """
    keywords = failure_keywords or ["42", "hello"]

    responses = [
        "1. [TOOL:calculator] Compute 6*7\n2. [TOOL:echo] Say hello\n3. Summarise",
        f"The calculator says {keywords[0]} and the echo says {keywords[1]} world",
        f"The answer is {keywords[0]} and {keywords[1]} world.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("calculator", keywords[0]))
    reg.register(FixedValueTool("echo", f"{keywords[1]} world"))

    run = _execute_scenario(responses, "Compute and greet", tool_registry=reg)
    graph = _build_graph(run)
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains any failure keyword",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    calc_channels = _find_channels_by_tool(run, graph, all_interventions, "calculator")
    echo_channels = _find_channels_by_tool(run, graph, all_interventions, "echo")

    calc_ids = [ci.intervention_id for ci in calc_channels]
    echo_ids = [ci.intervention_id for ci in echo_channels]
    all_causal = calc_ids + echo_ids

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.REDUNDANT_OR,
        failure_keywords=keywords,
        keyword_logic="any",
        causal_tool_names=["calculator", "echo"],
    )

    evaluator = _build_keyword_evaluator(keywords, "any")

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_b_{seed}",
        family="BF-B",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=all_causal,
        irrelevant_channel_ids=[],
        causal_origin_ids=all_causal,
        propagation_channel_ids=[],
        failure_actuator_ids=all_causal,
        required_prevention_sets=[all_causal],
        redundancy_groups=[all_causal] if len(all_causal) > 1 else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(calc_ids, True),
            **dict.fromkeys(echo_ids, True),
        },
        joint_intervention_outcome=False,
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-B",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def generate_complementary(
    *,
    seed: int = 42,
    failure_keywords: list[str] | None = None,
) -> BenchmarkScenario:
    """BF-C: Complementary / Interaction (AND) scenario.

    Failure requires ALL keywords present (AND logic).
    Blocking either tool alone prevents failure.

    Y = has(kw1) AND has(kw2). Non-additive interaction.
    """
    keywords = failure_keywords or ["42", "hello"]

    responses = [
        "1. [TOOL:calculator] Compute 6*7\n2. [TOOL:echo] Say hello\n3. Summarise",
        f"The calculator says {keywords[0]} and the echo says {keywords[1]} world",
        f"The answer is {keywords[0]} and {keywords[1]} world.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("calculator", keywords[0]))
    reg.register(FixedValueTool("echo", f"{keywords[1]} world"))

    run = _execute_scenario(responses, "Compute and greet", tool_registry=reg)
    graph = _build_graph(run)
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains ALL failure keywords",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    calc_channels = _find_channels_by_tool(run, graph, all_interventions, "calculator")
    echo_channels = _find_channels_by_tool(run, graph, all_interventions, "echo")

    calc_ids = [ci.intervention_id for ci in calc_channels]
    echo_ids = [ci.intervention_id for ci in echo_channels]
    all_causal = calc_ids + echo_ids

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.COMPLEMENTARY_AND,
        failure_keywords=keywords,
        keyword_logic="all",
        causal_tool_names=["calculator", "echo"],
    )

    evaluator = _build_keyword_evaluator(keywords, "all")

    # Each channel alone is a sufficient prevention set
    prevention_sets = [[cid] for cid in calc_ids] + [[eid] for eid in echo_ids]

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_c_{seed}",
        family="BF-C",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=all_causal,
        irrelevant_channel_ids=[],
        causal_origin_ids=all_causal,
        propagation_channel_ids=[],
        failure_actuator_ids=all_causal,
        required_prevention_sets=prevention_sets,
        complementary_groups=[all_causal] if len(all_causal) > 1 else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(calc_ids, False),
            **dict.fromkeys(echo_ids, False),
        },
        joint_intervention_outcome=False,
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-C",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def generate_distractor(
    *,
    seed: int = 42,
    failure_keyword: str = "42",
) -> BenchmarkScenario:
    """BF-D: Distractor scenario.

    Multiple tools present but only one causes failure.
    Others are structurally plausible but causally irrelevant.
    """
    responses = [
        (
            "1. [TOOL:calculator] Compute 6*7\n"
            "2. [TOOL:echo] Say hello\n"
            "3. [TOOL:timestamp] Get time\n"
            "4. Summarise"
        ),
        (f"The calculator says {failure_keyword}, the echo says greeting, and the time is now"),
        f"The answer is {failure_keyword}, greeting received, time noted.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("calculator", failure_keyword))
    reg.register(FixedValueTool("echo", "greeting"))
    reg.register(FixedValueTool("timestamp", "now"))

    run = _execute_scenario(responses, "Compute, greet, and check time", tool_registry=reg)
    graph = _build_graph(run)
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains failure keyword",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    calc_channels = _find_channels_by_tool(run, graph, all_interventions, "calculator")
    echo_channels = _find_channels_by_tool(run, graph, all_interventions, "echo")
    ts_channels = _find_channels_by_tool(run, graph, all_interventions, "timestamp")

    calc_ids = [ci.intervention_id for ci in calc_channels]
    echo_ids = [ci.intervention_id for ci in echo_channels]
    ts_ids = [ci.intervention_id for ci in ts_channels]
    irrelevant = echo_ids + ts_ids

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.DISTRACTOR,
        failure_keywords=[failure_keyword],
        keyword_logic="any",
        causal_tool_names=["calculator"],
        distractor_tool_names=["echo", "timestamp"],
    )

    evaluator = _build_keyword_evaluator([failure_keyword], "any")

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_d_{seed}",
        family="BF-D",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=calc_ids,
        irrelevant_channel_ids=irrelevant,
        causal_origin_ids=calc_ids,
        propagation_channel_ids=[],
        failure_actuator_ids=calc_ids,
        required_prevention_sets=[calc_ids] if calc_ids else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(calc_ids, False),
            **dict.fromkeys(echo_ids, True),
            **dict.fromkeys(ts_ids, True),
        },
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-D",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def generate_cascade(
    *,
    seed: int = 42,
    failure_keyword: str = "42",
) -> BenchmarkScenario:
    """BF-E: Multi-hop cascade scenario.

    Calculator -> reasoning -> output. Failure originates at
    calculator and propagates through reasoning to output.
    """
    responses = [
        "1. [TOOL:calculator] Compute 6*7\n2. Summarise",
        f"The calculator says {failure_keyword}."
        f" Based on this result, the answer is {failure_keyword}.",
        f"Final answer: {failure_keyword}.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("calculator", failure_keyword))

    run = _execute_scenario(responses, "Compute a value", tool_registry=reg)
    graph = _build_graph(run)
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains failure keyword from cascade",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    calc_channels = _find_channels_by_tool(run, graph, all_interventions, "calculator")

    calc_ids = [ci.intervention_id for ci in calc_channels]
    # Non-calculator interventions are propagation channels
    non_calc_ids = [
        ci.intervention_id for ci in all_interventions if ci.intervention_id not in calc_ids
    ]

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.CASCADE,
        failure_keywords=[failure_keyword],
        keyword_logic="any",
        causal_tool_names=["calculator"],
    )

    evaluator = _build_keyword_evaluator([failure_keyword], "any")

    # Last evidence is actuator
    actuator_ids = non_calc_ids[-1:] if non_calc_ids else calc_ids

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_e_{seed}",
        family="BF-E",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=calc_ids + non_calc_ids,
        irrelevant_channel_ids=[],
        causal_origin_ids=calc_ids,
        propagation_channel_ids=non_calc_ids,
        failure_actuator_ids=actuator_ids,
        required_prevention_sets=[calc_ids] if calc_ids else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes=dict.fromkeys(calc_ids, False),
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-E",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def generate_cost_asymmetric(
    *,
    seed: int = 42,
    expensive_cost: float = 5.0,
    cheap_cost: float = 1.0,
    budget: float = 3.0,
) -> BenchmarkScenario:
    """BF-F: Cost-asymmetric scenario.

    Calculator (expensive) and echo (cheap) both independently
    cause failure. Budget constraint forces cost-aware selection.
    """
    responses = [
        "1. [TOOL:calculator] Compute 6*7\n2. [TOOL:echo] Say hello\n3. Summarise",
        "The calculator says 42 and the echo says hello world",
        "The answer is 42 and hello world.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("calculator", "42"))
    reg.register(FixedValueTool("echo", "hello world"))

    run = _execute_scenario(responses, "Compute and greet", tool_registry=reg)
    graph = _build_graph(run)
    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Cost-asymmetric failure",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)
    calc_channels = _find_channels_by_tool(run, graph, all_interventions, "calculator")
    echo_channels = _find_channels_by_tool(run, graph, all_interventions, "echo")

    calc_ids = [ci.intervention_id for ci in calc_channels]
    echo_ids = [ci.intervention_id for ci in echo_channels]

    # Build cost map: calculator is expensive, echo is cheap
    costs: dict[str, float] = {}
    for cid in calc_ids:
        costs[cid] = expensive_cost
    for eid in echo_ids:
        costs[eid] = cheap_cost

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.COST_ASYMMETRIC,
        failure_keywords=["42", "hello"],
        keyword_logic="any",
        causal_tool_names=["calculator", "echo"],
    )

    # OR evaluator: blocking either prevents that keyword
    evaluator = _build_keyword_evaluator(["42", "hello"], "any")

    all_causal = calc_ids + echo_ids

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_f_{seed}",
        family="BF-F",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=all_causal,
        irrelevant_channel_ids=[],
        causal_origin_ids=all_causal,
        propagation_channel_ids=[],
        failure_actuator_ids=all_causal,
        # Either alone is a sufficient prevention set
        required_prevention_sets=[[cid] for cid in calc_ids] + [[eid] for eid in echo_ids],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(calc_ids, True),
            **dict.fromkeys(echo_ids, True),
        },
        joint_intervention_outcome=False,
        channel_costs=costs,
        budget=budget,
        expected_budget_feasible_set=echo_ids,
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-F",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


# ===================================================================
# BF-G: Shared-source multi-channel scenario (Stage 1.1)
# ===================================================================


def generate_shared_source(
    *,
    seed: int = 42,
    failure_keyword: str = "42",
) -> BenchmarkScenario:
    """BF-G: Shared-source multi-channel scenario.

    **Stage 1.1 — Blocker B validation.**

    ONE source tool (``data_source``) produces a composite result
    containing a failure keyword AND benign data.  TWO downstream
    tools consume different parts:

    - ``analyzer`` extracts the failure keyword → channel A (causal)
    - ``validator`` extracts the benign status → channel B (non-causal)

    Structure::

                         ┌── analyzer → "42" → FAILURE
        data_source ────┤
                         └── validator → "ok" → SUCCESS

    Channel-level intervention on A (analyzer) should block the
    failure keyword WITHOUT affecting B (validator).

    Step-level intervention on the data_source event would block
    BOTH channels since both depend on the same source event.

    Hidden causal truth:
    - Channel A (data_source → analyzer): CAUSAL
    - Channel B (data_source → validator): NON-CAUSAL
    """
    composite_result = f"ANSWER={failure_keyword};STATUS=ok"

    responses = [
        (
            "1. [TOOL:data_source] Get data\n"
            "2. [TOOL:analyzer] Analyze the answer\n"
            "3. [TOOL:validator] Validate status\n"
            "4. Summarise"
        ),
        (f"The analyzer found {failure_keyword} and the validator confirmed ok."),
        f"Result: {failure_keyword}, status ok.",
    ]

    reg = ToolRegistry()
    reg.register(FixedValueTool("data_source", composite_result))
    reg.register(FixedValueTool("analyzer", failure_keyword))
    reg.register(FixedValueTool("validator", "ok"))

    run = _execute_scenario(
        responses,
        "Get data, analyze and validate",
        tool_registry=reg,
    )
    graph = _build_graph(run)

    failure = Failure(
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains failure keyword from shared source",
        failure_event_id=run.events[-1].event_id,
    )

    all_interventions = _get_tool_channel_interventions(run, graph, failure)

    # Classify channels by tool
    source_channels = _find_channels_by_tool(run, graph, all_interventions, "data_source")
    analyzer_channels = _find_channels_by_tool(run, graph, all_interventions, "analyzer")
    validator_channels = _find_channels_by_tool(run, graph, all_interventions, "validator")

    # Causal: analyzer channels (carry the failure keyword)
    # Non-causal: validator channels + data_source channels
    causal_ids = [ci.intervention_id for ci in analyzer_channels]
    non_causal_ids = [ci.intervention_id for ci in validator_channels] + [
        ci.intervention_id for ci in source_channels
    ]

    mechanism = CausalMechanismSpec(
        mechanism=CausalMechanism.SINGLE_CHANNEL,
        failure_keywords=[failure_keyword],
        keyword_logic="any",
        causal_tool_names=["analyzer"],
        distractor_tool_names=["validator", "data_source"],
    )

    evaluator = _build_keyword_evaluator([failure_keyword], "any")

    ground_truth = ScenarioGroundTruth(
        scenario_id=f"bf_g_{seed}",
        family="BF-G",
        seed=seed,
        mechanism=mechanism,
        causal_channel_ids=causal_ids,
        irrelevant_channel_ids=non_causal_ids,
        causal_origin_ids=causal_ids,
        propagation_channel_ids=[],
        failure_actuator_ids=causal_ids,
        required_prevention_sets=[causal_ids] if causal_ids else [],
        factual_outcome=evaluator(run),
        single_intervention_outcomes={
            **dict.fromkeys(causal_ids, False),
            **dict.fromkeys(non_causal_ids, True),
        },
        joint_intervention_outcome=False,
    )

    scenario = BenchmarkScenario(
        scenario_id=ground_truth.scenario_id,
        family="BF-G",
        seed=seed,
        run=run,
        evidence_graph=graph,
        failure=failure,
        candidates=all_interventions,
        ground_truth=ground_truth,
    )
    scenario._evaluator = evaluator  # type: ignore[attr-defined]
    return scenario


def get_evaluator(scenario: BenchmarkScenario) -> FailureEvaluator:
    """Get the failure evaluator for a scenario.

    Reconstructs from ground truth if not cached.
    """
    if hasattr(scenario, "_evaluator"):
        return scenario._evaluator  # type: ignore[no-any-return]
    # Reconstruct from mechanism spec
    mech = scenario.ground_truth.mechanism
    return _build_keyword_evaluator(mech.failure_keywords, mech.keyword_logic)


def all_scenarios(*, seed: int = 42) -> list[BenchmarkScenario]:
    """Generate one scenario per benchmark family."""
    return [
        generate_single_cause(seed=seed),
        generate_redundant(seed=seed),
        generate_complementary(seed=seed),
        generate_distractor(seed=seed),
        generate_cascade(seed=seed),
        generate_cost_asymmetric(seed=seed),
        generate_shared_source(seed=seed),
    ]
