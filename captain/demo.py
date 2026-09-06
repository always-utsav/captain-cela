#!/usr/bin/env python
"""CAPTAIN/CELA one-command reproducible demonstration.

Usage::

    python -m captain.demo

Exercises the REAL pipeline:

    Agent → TraceCollector → ExecutionRun → EvidenceLineageBuilder →
    EvidenceFlowGraph → FailureAnalyzer → ChannelIntervention →
    CEE/counterfactual replay → Cascade selection → benchmark/experiment

All results are deterministic and serialized to captain_results/.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.analysis.cascade import (
    CascadeEstimator,
    GreedyCascadeSelector,
)
from captain.analysis.estimator import CEEEstimator
from captain.benchmarks.scenarios import generate_single_cause
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.experiments import ExperimentConfig, ExperimentRunner
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import Failure, FailureType
from captain.graph.builder import ExecutionGraphBuilder
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent

# Output directory
RESULTS_DIR = Path("captain_results")
MASTER_SEED = 42


def _print(msg: str) -> None:
    print(f"  {msg}")


def _header(msg: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def run_demo() -> dict[str, object]:
    """Run the complete CELA demonstration."""
    results: dict[str, object] = {}
    start = time.time()

    # ---------------------------------------------------------------
    # 1. Agent execution
    # ---------------------------------------------------------------
    _header("1. AGENT EXECUTION")

    llm = MockLLMProvider(
        responses=[
            "1. [TOOL:calculator] Compute 6*7\n2. [TOOL:echo] Report result\n3. Generate response",
            "Computation complete: 42",
            "Echo confirmed",
            "The answer is 42. Calculator confirmed.",
        ]
    )
    registry = create_default_tool_registry()
    agent = Agent(llm=llm, tool_registry=registry)
    traced = TracedAgent(agent)
    _response, collector = traced.run(
        TaskInput.from_text("What is 6 times 7? Use the calculator.")
    )
    run = collector.get_run()

    _print(f"Run ID: {run.run_id}")
    _print(f"Events: {run.event_count}")
    _print(f"Artifacts: {run.artifact_count}")
    _print(f"Status: {run.status.value}")

    # Store
    RESULTS_DIR.mkdir(exist_ok=True)
    store = FileTraceStore(RESULTS_DIR / "traces")
    store.save(run)

    results["run_id"] = run.run_id
    results["event_count"] = run.event_count
    results["artifact_count"] = run.artifact_count

    # ---------------------------------------------------------------
    # 2. Execution graph
    # ---------------------------------------------------------------
    _header("2. EXECUTION GRAPH")

    graph = ExecutionGraphBuilder.build(run)
    _print(f"Nodes: {graph.node_count}")
    _print(f"Edges: {graph.edge_count}")

    results["graph_nodes"] = graph.node_count
    results["graph_edges"] = graph.edge_count

    # ---------------------------------------------------------------
    # 3. Evidence-flow graph
    # ---------------------------------------------------------------
    _header("3. EVIDENCE-FLOW GRAPH")

    builder = EvidenceLineageBuilder(run)
    evidence_list, transformations = builder.build()
    evidence_graph = EvidenceFlowGraph.from_lineage(evidence_list, transformations)
    _print(f"Evidence nodes: {evidence_graph.evidence_count}")
    _print(f"Evidence edges: {evidence_graph.transformation_count}")

    results["evidence_nodes"] = evidence_graph.evidence_count
    results["evidence_edges"] = evidence_graph.transformation_count

    # ---------------------------------------------------------------
    # 4. Failure analysis
    # ---------------------------------------------------------------
    _header("4. FAILURE ANALYSIS")

    def failure_evaluator(r):  # type: ignore[no-untyped-def]
        """Keyword evaluator: failure if '42' in output."""
        for evt in r.events:
            payload_str = str(evt.payload)
            if "42" in payload_str:
                return True
        return any("42" in str(a.value) for a in r.artifacts)

    failure = Failure(
        failure_id="fail_demo",
        run_id=run.run_id,
        failure_type=FailureType.TASK_FAILURE,
        description="Output contains '42' (injected failure keyword)",
    )

    analyzer = FailureAnalyzer(evidence_graph, failure)
    candidates = analyzer.candidates()
    interventions = analyzer.interventions()

    _print(f"Candidates: {len(candidates)}")
    for c in candidates:
        _print(f"  {c.candidate_id[:12]}... score={c.screening_score:.2f}")
    _print(f"Interventions: {len(interventions)}")

    results["candidates"] = len(candidates)
    results["interventions"] = len(interventions)

    # ---------------------------------------------------------------
    # 5. CEE estimation
    # ---------------------------------------------------------------
    _header("5. CEE ESTIMATION (Counterfactual)")

    if candidates and interventions:
        cee_est = CEEEstimator(
            run,
            failure_evaluator,
            evidence_graph=evidence_graph,
            num_trials=1,
        )
        first_ci = interventions[0]
        cee_result = cee_est.estimate(candidates[0], first_ci)

        _print(f"FACTUAL outcome: failure={True}")
        _print(f"COUNTERFACTUAL outcome: CEE={cee_result.cee:.3f}")
        _print(f"CI: [{cee_result.ci_lower:.3f}, {cee_result.ci_upper:.3f}]")
        _print(f"Trials: {cee_result.num_valid_trials}/{cee_result.num_trials}")

        results["cee"] = cee_result.cee
    else:
        _print("No candidates/interventions available")
        results["cee"] = 0.0

    # ---------------------------------------------------------------
    # 6. Cascade intervention
    # ---------------------------------------------------------------
    _header("6. CASCADE INTERVENTION")

    if interventions:
        cascade_est = CascadeEstimator(
            run,
            failure_evaluator,
            evidence_graph=evidence_graph,
            num_trials=1,
        )
        selector = GreedyCascadeSelector(cascade_est, max_set_size=3, max_evaluations=20)
        sel_result = selector.select(interventions)

        selected_count = 0
        if sel_result.selected_set:
            selected_count = len(sel_result.selected_set.channel_interventions)

        _print(f"Selected channels: {selected_count}")
        _print(f"Status: {sel_result.status.value}")
        _print(f"Evaluations: {sel_result.evaluations_used}")

        results["cascade_selected"] = selected_count
        results["cascade_status"] = sel_result.status.value
    else:
        _print("No interventions available")

    # ---------------------------------------------------------------
    # 7. Benchmark scenario
    # ---------------------------------------------------------------
    _header("7. BENCHMARK SCENARIO (BF-A)")

    scenario = generate_single_cause(seed=MASTER_SEED)
    gt = scenario.ground_truth

    _print(f"Family: {gt.family}")
    _print(f"Causal channels: {len(gt.causal_channel_ids)}")
    _print(f"Candidates: {len(scenario.candidates)}")
    _print("[POST-HOC] Ground truth provided for evaluation only")

    results["benchmark_family"] = gt.family
    results["benchmark_candidates"] = len(scenario.candidates)

    # ---------------------------------------------------------------
    # 8. Experiment
    # ---------------------------------------------------------------
    _header("8. EXPERIMENT (Small Reproducible)")

    exp_config = ExperimentConfig(
        master_seed=MASTER_SEED,
        instances_per_family=3,
        families=["BF-A", "BF-B", "BF-C"],
        methods=["B1", "B2", "A2", "A4"],
        run_oracle=True,
        bootstrap_resamples=200,
    )
    exp_runner = ExperimentRunner(exp_config)
    exp_result = exp_runner.run()

    _print(f"Scenarios: {exp_result.metadata.total_scenarios}")
    _print(f"Evaluations: {exp_result.metadata.total_method_evaluations}")
    _print(f"Comparisons: {len(exp_result.comparisons)}")
    _print(f"Ablation steps: {len(exp_result.ablation_steps)}")

    # Print summary table
    _print("")
    _print(f"{'Method':<16} {'F1':>6} {'Prev':>6} {'CEE':>6} {'N':>4}")
    _print("-" * 42)
    for mname, agg in exp_result.overall_aggregates.items():
        f1 = agg.summaries.get("causal_f1")
        prev = agg.summaries.get("failure_prevention_rate")
        cee = agg.summaries.get("cee_set")
        _print(
            f"{mname:<16} "
            f"{f1.mean if f1 else 0:>6.3f} "
            f"{prev.mean if prev else 0:>6.3f} "
            f"{cee.mean if cee else 0:>6.3f} "
            f"{agg.n_scenarios:>4}"
        )

    results["experiment_scenarios"] = exp_result.metadata.total_scenarios
    results["experiment_methods"] = len(exp_result.overall_aggregates)

    # ---------------------------------------------------------------
    # 9. Serialize results
    # ---------------------------------------------------------------
    _header("9. RESULT SERIALIZATION")

    result_path = RESULTS_DIR / f"experiment_{MASTER_SEED}.json"
    result_data = exp_result.model_dump()
    result_path.write_text(json.dumps(result_data, default=str, indent=2))
    _print(f"Saved to: {result_path}")

    summary_path = RESULTS_DIR / "demo_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, default=str))
    _print(f"Summary: {summary_path}")

    results["result_path"] = str(result_path)

    # ---------------------------------------------------------------
    # Done
    # ---------------------------------------------------------------
    elapsed = time.time() - start
    _header("DEMO COMPLETE")
    _print(f"Time: {elapsed:.1f}s")
    _print(f"Results: {RESULTS_DIR}/")
    _print("")
    _print("To launch Explorer:")
    _print("  python -m captain.explorer")
    _print("")

    return results


if __name__ == "__main__":
    run_demo()
