"""CAPTAIN Trace Explorer -- Flask application.

A lightweight local browser-based interface for inspecting CAPTAIN
execution traces, graphs, provenance, and artifacts.

Launch::

    python -m captain.explorer

Or::

    python scripts/launch_explorer.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

from captain.adapters.llm import MockLLMProvider
from captain.agent.agent import Agent
from captain.agent.tools import create_default_tool_registry
from captain.agent.types import TaskInput
from captain.graph.analysis import GraphAnalyzer
from captain.graph.builder import ExecutionGraphBuilder
from captain.graph.validation import GraphValidator
from captain.models.execution import ExecutionRun
from captain.provenance.query import ProvenanceQuery
from captain.storage.store import FileTraceStore
from captain.tracing.traced_agent import TracedAgent

# Default storage directory
_DEFAULT_STORE_DIR = Path("./captain_traces")

# In-memory run cache (for demo runs not yet stored)
_run_cache: dict[str, ExecutionRun] = {}


def create_app(store_dir: Path | None = None) -> Flask:
    """Create and configure the Flask application."""
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    store_path = store_dir or _DEFAULT_STORE_DIR
    store = FileTraceStore(store_path)

    # --- Page routes --------------------------------------------------------

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    # --- API routes ---------------------------------------------------------

    @app.route("/api/demo", methods=["POST"])
    def run_demo() -> Any:
        """Run a deterministic demo execution and return the run."""
        llm = MockLLMProvider(
            responses=[
                "1. [TOOL:calculator] Compute 6*7\n"
                "2. [TOOL:echo] Report result\n"
                "3. Generate response",
                "Computation complete: 42",
                "Echo confirmed",
                "The answer to 6 times 7 is 42. I computed this using the calculator tool.",
            ]
        )
        registry = create_default_tool_registry()
        agent = Agent(llm=llm, tool_registry=registry)
        traced = TracedAgent(agent)
        _response, collector = traced.run(
            TaskInput.from_text("What is 6 times 7? Use the calculator.")
        )
        run = collector.get_run()

        # Store and cache
        store.save(run)
        _run_cache[run.run_id] = run

        return jsonify(_run_summary(run))

    @app.route("/api/runs")
    def list_runs() -> Any:
        """List all stored run IDs."""
        run_ids = store.list_runs()
        summaries = []
        for rid in run_ids:
            loaded = store.load(rid)
            if loaded:
                summaries.append(_run_summary(loaded))
        return jsonify(summaries)

    @app.route("/api/run/<run_id>")
    def get_run(run_id: str) -> Any:
        """Get full run details."""
        run = _get_run(run_id, store)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        return jsonify(_run_detail(run))

    @app.route("/api/graph/<run_id>")
    def get_graph(run_id: str) -> Any:
        """Get graph data for vis.js rendering."""
        run = _get_run(run_id, store)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        graph = ExecutionGraphBuilder.build(run)
        validation = GraphValidator.validate(graph)
        analyzer = GraphAnalyzer(graph)
        return jsonify(
            {
                "graph": _graph_to_vis(graph),
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.error_count,
                    "warnings": validation.warning_count,
                },
                "analysis": analyzer.summary(),
            }
        )

    @app.route("/api/event/<run_id>/<event_id>")
    def get_event(run_id: str, event_id: str) -> Any:
        """Get event details."""
        run = _get_run(run_id, store)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        for evt in run.events:
            if evt.event_id == event_id:
                return jsonify(_event_detail(evt))
        return jsonify({"error": "Event not found"}), 404

    @app.route("/api/artifact/<run_id>/<artifact_id>")
    def get_artifact(run_id: str, artifact_id: str) -> Any:
        """Get artifact details with provenance."""
        run = _get_run(run_id, store)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        for art in run.artifacts:
            if art.artifact_id == artifact_id:
                pq = ProvenanceQuery(run)
                return jsonify(_artifact_detail(art, pq))
        return jsonify({"error": "Artifact not found"}), 404

    @app.route("/api/provenance/<run_id>/<artifact_id>")
    def get_provenance(run_id: str, artifact_id: str) -> Any:
        """Get full provenance lineage for an artifact."""
        run = _get_run(run_id, store)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        pq = ProvenanceQuery(run)
        return jsonify(
            {
                "artifact_id": artifact_id,
                "producer": pq.get_producer(artifact_id),
                "consumers": pq.get_consumers(artifact_id),
                "upstream": pq.trace_upstream(artifact_id),
                "downstream": pq.trace_downstream(artifact_id),
            }
        )

    # Stage 18 Caches
    _scenario_cache: dict[str, Any] = {}
    _experiment_cache: dict[str, Any] = {}

    @app.route("/api/demo/benchmark", methods=["POST"])
    def run_benchmark_demo() -> Any:
        try:
            from captain.benchmarks.runner import BenchmarkRunner
            from captain.benchmarks.scenarios import (
                generate_single_cause,
            )
        except ImportError as e:
            return jsonify({"error": str(e)}), 500

        scenario = generate_single_cause(seed=42)
        _scenario_cache[scenario.scenario_id] = scenario
        # evaluator = get_evaluator(scenario)  # used by BenchmarkRunner internally

        runner = BenchmarkRunner(k=2, max_set_size=3, lambda_cost=0.1)
        result = runner.run([scenario], methods=None, run_oracle=True)

        gt = scenario.ground_truth
        candidates_summary = [
            {
                "id": c.intervention_id,
                "source": c.source_evidence_id,
                "target": c.target_evidence_id,
                "type": c.intervention_type.value
                if hasattr(c.intervention_type, "value")
                else str(c.intervention_type),
            }
            for c in scenario.candidates
        ]

        # Cache result for counterfactual/cascade views
        _scenario_cache[scenario.scenario_id + "_result"] = result

        return jsonify(
            {
                "scenario_id": scenario.scenario_id,
                "family": gt.family,
                "ground_truth": {
                    "label": "POST-HOC EVALUATION ONLY",
                    "causal_channel_ids": gt.causal_channel_ids,
                    "evaluation_only": True,
                },
                "candidates": candidates_summary,
                "method_results": [
                    {
                        "method": mr.method_name,
                        "metrics": mr.metrics.model_dump(),
                    }
                    for mr in result.results
                ],
            }
        )

    @app.route("/api/evidence/<run_id>")
    def get_evidence(run_id: str) -> Any:
        try:
            from captain.evidence.lineage import EvidenceLineageBuilder
        except ImportError as e:
            return jsonify({"error": str(e)}), 500
        run = _get_run(run_id, store)
        if not run:
            return jsonify({"error": "Not found"}), 404
        builder = EvidenceLineageBuilder(run)
        evidence_list, transformations = builder.build()

        nodes = []
        for n in evidence_list:
            nodes.append(
                {
                    "id": n.evidence_id,
                    "evidence_type": n.evidence_type.value
                    if hasattr(n.evidence_type, "value")
                    else str(n.evidence_type),
                    "artifact_id": n.artifact_id,
                    "producer": n.creation_event_id,
                    "sequence": n.sequence_number,
                }
            )

        edges = []
        for t in transformations:
            edges.append(
                {
                    "source": t.source_evidence_id,
                    "target": t.target_evidence_id,
                    "type": t.transformation_type.value
                    if hasattr(t.transformation_type, "value")
                    else str(t.transformation_type),
                    "event_id": t.event_id,
                    "provenance": t.provenance_method.value
                    if hasattr(t.provenance_method, "value")
                    else str(t.provenance_method),
                }
            )

        return jsonify(
            {
                "evidence": nodes,
                "transformations": edges,
                "count": len(nodes),
            }
        )

    @app.route("/api/failure/<run_id>")
    def get_failure(run_id: str) -> Any:
        try:
            from captain.evidence.graph import EvidenceFlowGraph
            from captain.evidence.lineage import EvidenceLineageBuilder
            from captain.failures.analyzer import FailureAnalyzer
            from captain.failures.model import Failure, FailureType
        except ImportError as e:
            return jsonify({"error": str(e)}), 500
        run = _get_run(run_id, store)
        if not run:
            return jsonify({"error": "Not found"}), 404

        builder = EvidenceLineageBuilder(run)
        evidence_list, transformations = builder.build()
        graph = EvidenceFlowGraph.from_lineage(evidence_list, transformations)

        failure = Failure(
            failure_id="f1",
            run_id=run_id,
            failure_type=FailureType.TASK_FAILURE,
            description="Demonstration failure analysis",
        )

        analyzer = FailureAnalyzer(graph, failure)
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()

        return jsonify(
            {
                "failure": {
                    "failure_id": failure.failure_id,
                    "failure_type": failure.failure_type.value,
                    "description": failure.description,
                },
                "candidates": [
                    {
                        "id": c.candidate_id,
                        "source": c.source_evidence_id,
                        "target": c.target_evidence_id,
                        "score": c.screening_score,
                    }
                    for c in candidates
                ],
                "interventions": [
                    {
                        "id": ci.intervention_id,
                        "source": ci.source_evidence_id,
                        "target": ci.target_evidence_id,
                    }
                    for ci in interventions
                ],
            }
        )

    @app.route("/api/counterfactual/<scenario_id>")
    def get_counterfactual(scenario_id: str) -> Any:
        if scenario_id not in _scenario_cache:
            return jsonify({"error": "Not found"}), 404
        scenario = _scenario_cache[scenario_id]  # noqa: F841
        result_key = scenario_id + "_result"
        result = _scenario_cache.get(result_key)

        method_cees = []
        if result:
            for mr in result.results:
                method_cees.append(
                    {
                        "method": mr.method_name,
                        "causal_f1": mr.metrics.attribution.causal_f1
                        if mr.metrics.attribution
                        else None,
                        "cee_set": mr.metrics.prevention.cee_set
                        if mr.metrics.prevention
                        else None,
                    }
                )

        return jsonify(
            {
                "scenario_id": scenario_id,
                "factual": {
                    "label": "FACTUAL (OBSERVED)",
                    "failure": True,
                    "description": "Original execution with failure",
                },
                "counterfactual": {
                    "label": "COUNTERFACTUAL",
                    "description": "Execution with intervention applied",
                    "method_results": method_cees,
                },
            }
        )

    @app.route("/api/cascade/<scenario_id>")
    def get_cascade(scenario_id: str) -> Any:
        if scenario_id not in _scenario_cache:
            return jsonify({"error": "Not found"}), 404
        scenario = _scenario_cache[scenario_id]
        result_key = scenario_id + "_result"
        result = _scenario_cache.get(result_key)

        gt = scenario.ground_truth
        method_summaries = []
        if result:
            for mr in result.results:
                eff = mr.metrics.efficiency
                prev = mr.metrics.prevention
                method_summaries.append(
                    {
                        "method": mr.method_name,
                        "set_size": eff.set_size if eff else 0,
                        "cost": eff.intervention_cost if eff else 0,
                        "utility": eff.utility if eff else 0,
                        "prevention_rate": prev.failure_prevention_rate if prev else 0,
                    }
                )

        oracle_data = None
        if result and result.oracle_results:
            # Dict keyed by scenario_id
            first_key = next(iter(result.oracle_results))
            orc = result.oracle_results[first_key]
            oracle_data = {
                "label": "EVALUATION ONLY",
                "optimal_objective": orc.optimal_objective,
                "sets_evaluated": orc.sets_evaluated,
            }

        return jsonify(
            {
                "scenario_id": scenario_id,
                "family": gt.family,
                "method_cascade_results": method_summaries,
                "oracle": oracle_data,
                "ground_truth_label": "POST-HOC EVALUATION ONLY",
            }
        )

    @app.route("/api/experiment", methods=["POST"])
    def run_experiment() -> Any:
        try:
            from captain.experiments import ExperimentConfig, ExperimentRunner
        except ImportError as e:
            return jsonify({"error": str(e)}), 500
        req = request.json or {}
        config = ExperimentConfig(
            master_seed=req.get("master_seed", 42),
            instances_per_family=req.get("instances_per_family", 3),
            families=req.get("families", ["BF-A", "BF-B", "BF-C"]),
            methods=req.get("methods", ["B1", "B2", "A2", "A4"]),
            bootstrap_resamples=req.get("bootstrap_resamples", 200),
        )
        runner = ExperimentRunner(config)
        result = runner.run()
        _experiment_cache["last"] = result
        return jsonify(result.model_dump() if hasattr(result, "model_dump") else result)

    @app.route("/api/experiment/summary")
    def get_experiment_summary() -> Any:
        if "last" not in _experiment_cache:
            return jsonify({"message": "No experiment has been run"})
        result = _experiment_cache["last"]
        rows = []
        for mname, agg in result.overall_aggregates.items():
            f1 = agg.summaries.get("causal_f1")
            prev = agg.summaries.get("failure_prevention_rate")
            cee = agg.summaries.get("cee_set")
            cost = agg.summaries.get("intervention_cost")
            ci = agg.confidence_intervals.get("causal_f1")
            rows.append(
                {
                    "method": mname,
                    "causal_f1": f1.mean if f1 else None,
                    "prevention": prev.mean if prev else None,
                    "cee_set": cee.mean if cee else None,
                    "cost": cost.mean if cost else None,
                    "ci_lower": ci.ci_lower if ci else None,
                    "ci_upper": ci.ci_upper if ci else None,
                    "n_scenarios": agg.n_scenarios,
                }
            )
        return jsonify(
            {
                "summary": rows,
                "seed": result.metadata.master_seed,
                "total_scenarios": result.metadata.total_scenarios,
                "comparisons": len(result.comparisons),
            }
        )

    @app.route("/api/experiment/export", methods=["POST"])
    def export_experiment() -> Any:
        if "last" not in _experiment_cache:
            return jsonify({"error": "No experiment to export"}), 400
        result = _experiment_cache["last"]
        import uuid

        exp_id = uuid.uuid4().hex
        out_path = Path("captain_results") / f"experiment_{exp_id}.json"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            f.write(
                result.model_dump_json() if hasattr(result, "model_dump_json") else str(result)
            )
        return jsonify({"path": str(out_path)})

    # --- Stage 2 Research Routes ---
    @app.route('/research')
    def research_page() -> str:
        return render_template("research.html")

    def _load_research_json(filename: str) -> Any:
        filepath = Path(__file__).parent.parent.parent / "research" / "raw" / filename
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except UnicodeDecodeError:
            with open(filepath, encoding="cp1252") as f:
                return json.load(f)

    @app.route('/api/research/campaign')
    def research_campaign() -> Any:
        return jsonify(_load_research_json("campaign_full.json"))

    @app.route('/api/research/granularity')
    def research_granularity() -> Any:
        return jsonify(_load_research_json("granularity_experiment.json"))

    @app.route('/api/research/negative_controls')
    def research_negative_controls() -> Any:
        return jsonify(_load_research_json("negative_controls.json"))

    @app.route('/api/research/convergence')
    def research_convergence() -> Any:
        return jsonify(_load_research_json("replay_convergence.json"))

    @app.route('/api/research/real_llm')
    def research_real_llm() -> Any:
        return jsonify(_load_research_json("real_llm_validation.json"))

    @app.route('/api/research/claims')
    def research_claims() -> Any:
        return jsonify(_load_research_json("claim_registry.json"))

    @app.route('/api/research/figures/<name>')
    def research_figures(name: str) -> Any:
        figs_dir = Path(__file__).parent.parent.parent / "research" / "figures"
        return send_from_directory(str(figs_dir), name)

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_run(run_id: str, store: FileTraceStore) -> ExecutionRun | None:
    """Get a run from cache or store."""
    if run_id in _run_cache:
        return _run_cache[run_id]
    return store.load(run_id)


def _run_summary(run: ExecutionRun) -> dict[str, Any]:
    """Minimal run summary for list view."""
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "task_input": run.task_input[:200],
        "event_count": run.event_count,
        "artifact_count": run.artifact_count,
    }


def _run_detail(run: ExecutionRun) -> dict[str, Any]:
    """Full run details."""
    return {
        **_run_summary(run),
        "events": [_event_detail(e) for e in run.events],
        "artifacts": [_artifact_brief(a) for a in run.artifacts],
    }


def _event_detail(evt: Any) -> dict[str, Any]:
    """Event detail for inspection."""
    return {
        "event_id": evt.event_id,
        "event_type": evt.event_type.value,
        "sequence_number": evt.sequence_number,
        "timestamp": evt.timestamp.isoformat(),
        "component": evt.component,
        "payload": evt.payload,
        "input_artifact_ids": evt.input_artifact_ids,
        "output_artifact_ids": evt.output_artifact_ids,
        "parent_event_id": evt.parent_event_id,
        "metadata": evt.metadata,
    }


def _artifact_brief(art: Any) -> dict[str, Any]:
    """Artifact summary."""
    return {
        "artifact_id": art.artifact_id,
        "artifact_type": art.artifact_type.value,
        "has_value": art.value is not None,
        "has_reference": art.reference is not None,
        "producer_event_id": art.producer_event_id,
    }


def _artifact_detail(art: Any, pq: ProvenanceQuery) -> dict[str, Any]:
    """Artifact detail with provenance."""
    value_display = None
    if art.value is not None:
        if isinstance(art.value, str):
            value_display = art.value[:500]
        else:
            value_display = json.dumps(art.value, default=str)[:500]

    return {
        "artifact_id": art.artifact_id,
        "artifact_type": art.artifact_type.value,
        "value": value_display,
        "reference": art.reference,
        "producer_event_id": art.producer_event_id,
        "producer": pq.get_producer(art.artifact_id),
        "consumers": pq.get_consumers(art.artifact_id),
        "upstream": pq.trace_upstream(art.artifact_id),
        "downstream": pq.trace_downstream(art.artifact_id),
        "metadata": art.metadata,
        "created_at": art.created_at.isoformat(),
    }


def _graph_to_vis(graph: Any) -> dict[str, Any]:
    """Convert ExecutionGraph to vis.js compatible format."""
    from captain.graph.model import NodeType

    nodes = []
    edges = []

    graph_dict = graph.to_dict()

    for node_data in graph_dict["nodes"]:
        is_event = node_data["node_type"] == NodeType.EVENT.value
        nodes.append(
            {
                "id": node_data["node_id"],
                "label": (
                    f"{node_data['label'].upper()}\n#{node_data.get('sequence_number', '?')}"
                    if is_event
                    else f"{node_data['label'].upper()}\n{node_data['node_id'][-8:]}"
                ),
                "group": "event" if is_event else "artifact",
                "title": node_data["node_id"],
                "shape": "box" if is_event else "ellipse",
                "node_type": node_data["node_type"],
                "node_id": node_data["node_id"],
            }
        )

    for i, edge_data in enumerate(graph_dict["edges"]):
        edges.append(
            {
                "id": f"edge_{i}",
                "from": edge_data["source_id"],
                "to": edge_data["target_id"],
                "label": edge_data["edge_type"],
                "arrows": "to",
                "edge_type": edge_data["edge_type"],
            }
        )

    return {"nodes": nodes, "edges": edges}
