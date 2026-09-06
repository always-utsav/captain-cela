"""Stage 1 smoke campaign — shared-source and step-vs-channel experiments.

This script runs the PRIMARY NOVELTY EXPERIMENT (Section 7) plus
seed robustness and replay convergence checks.

Results are written to research_stage1/raw/ as machine-readable JSON.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")

from captain.agent.tools import create_default_tool_registry
from captain.analysis.cascade import CascadeEstimator, CostModel, GreedyCascadeSelector
from captain.analysis.estimator import CEEEstimator, channel_to_intervention
from captain.benchmarks.baselines import (
    CELAMethod,
    CostAwareBaseline,
    GraphStructuralBaseline,
    ProvenanceOnlyBaseline,
    RandomBaseline,
)
from captain.benchmarks.runner import BenchmarkRunner, MetricEvaluator
from captain.benchmarks.scenarios import (
    BenchmarkScenario,
    generate_cascade,
    generate_complementary,
    generate_cost_asymmetric,
    generate_distractor,
    generate_redundant,
    generate_single_cause,
    get_evaluator,
)
from captain.intervention.model import Intervention, InterventionSet, InterventionType
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine


# ===================================================================
# Step-level baseline: intervene on the MEDIATING event
# ===================================================================


def step_level_intervention(
    channel, baseline_run, evidence_graph=None
) -> Intervention:
    """Create a STEP-LEVEL intervention (entire event output replaced).

    Unlike channel_to_intervention which targets the SOURCE evidence's
    producing event, this targets the MEDIATING event — the event through
    which the evidence flows. This affects ALL channels through that event.

    This is the step-level comparator for the novelty experiment.
    """
    return Intervention(
        intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
        baseline_run_id=channel.baseline_run_id,
        target_id=channel.event_id,
        replacement_value="",
        description=(
            f"STEP-LEVEL BLOCK: event {channel.event_id[:16]} "
            f"(affects all channels through this event)"
        ),
        metadata={
            "channel_intervention_id": channel.intervention_id,
            "intervention_type": "step_block",
            "channel_level": False,
            "step_level": True,
        },
    )


# ===================================================================
# Experiment result schema
# ===================================================================


@dataclass
class ExperimentEntry:
    """Single experiment result entry."""

    experiment_id: str
    scenario_id: str
    family: str
    method: str
    intervention_granularity: str
    seed: int
    replay_count: int
    candidate_id: str
    cee: float
    ci_lower: float
    ci_upper: float
    factual_outcome: bool
    counterfactual_outcome: bool | None
    prevented: bool
    num_valid_trials: int
    runtime_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "scenario_id": self.scenario_id,
            "family": self.family,
            "method": self.method,
            "intervention_granularity": self.intervention_granularity,
            "seed": self.seed,
            "replay_count": self.replay_count,
            "candidate_id": self.candidate_id,
            "cee": self.cee,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "factual_outcome": self.factual_outcome,
            "counterfactual_outcome": self.counterfactual_outcome,
            "prevented": self.prevented,
            "num_valid_trials": self.num_valid_trials,
            "runtime_ms": self.runtime_ms,
            "error": self.error,
        }


@dataclass
class SmokeSummary:
    """Summary of a smoke campaign method result."""

    method: str
    family: str
    seed: int
    f1: float | None = None
    recall_at_1: float | None = None
    prevention_rate: float | None = None
    utility: float | None = None
    cost: float | None = None


# ===================================================================
# Shared-source experiment (Section 7)
# ===================================================================


def run_shared_source_experiment(
    seeds: list[int],
    n_replays: int = 5,
) -> list[dict]:
    """Run the PRIMARY NOVELTY EXPERIMENT.

    Construct scenario where a single tool produces output that
    flows through two channels: one causal, one irrelevant.

    Compare:
    A. step-level intervention (blocks entire tool output)
    B. CELA channel-level intervention (blocks only causal channel)
    """
    results = []

    for seed in seeds:
        print(f"  Shared-source experiment seed={seed}")

        with deterministic_ids(seed=seed):
            scenario = generate_single_cause(seed=seed)

        evaluator = get_evaluator(scenario)
        tool_registry = create_default_tool_registry()

        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        irrelevant_ids = set(scenario.ground_truth.irrelevant_channel_ids)

        for ci in scenario.candidates:
            is_causal = ci.intervention_id in causal_ids
            is_irrelevant = ci.intervention_id in irrelevant_ids
            label = "causal" if is_causal else ("irrelevant" if is_irrelevant else "unknown")

            # A. Channel-level CEE
            t0 = time.perf_counter_ns()
            try:
                ch_intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
                ch_iset = InterventionSet(
                    baseline_run_id=scenario.run.run_id,
                    interventions=[ch_intv],
                )
                engine = CounterfactualReplayEngine()
                ch_result = engine.replay(scenario.run, ch_iset)

                if ch_result.counterfactual_run is not None:
                    ch_failed = evaluator(ch_result.counterfactual_run)
                    ch_cee = 1.0 - (1.0 if ch_failed else 0.0)  # Simple: 1 if prevented
                else:
                    ch_cee = 0.0
                    ch_failed = True
                ch_err = None
            except Exception as e:
                ch_cee = 0.0
                ch_failed = True
                ch_err = str(e)

            ch_ms = (time.perf_counter_ns() - t0) / 1e6

            results.append({
                "experiment": "shared_source",
                "method": "channel_level",
                "seed": seed,
                "candidate_id": ci.intervention_id,
                "candidate_label": label,
                "cee": ch_cee,
                "prevented": not ch_failed if ch_err is None else False,
                "runtime_ms": ch_ms,
                "error": ch_err,
            })

            # B. Step-level CEE
            t0 = time.perf_counter_ns()
            try:
                st_intv = step_level_intervention(ci, scenario.run)
                st_iset = InterventionSet(
                    baseline_run_id=scenario.run.run_id,
                    interventions=[st_intv],
                )
                st_result = engine.replay(scenario.run, st_iset)

                if st_result.counterfactual_run is not None:
                    st_failed = evaluator(st_result.counterfactual_run)
                    st_cee = 1.0 - (1.0 if st_failed else 0.0)
                else:
                    st_cee = 0.0
                    st_failed = True
                st_err = None
            except Exception as e:
                st_cee = 0.0
                st_failed = True
                st_err = str(e)

            st_ms = (time.perf_counter_ns() - t0) / 1e6

            results.append({
                "experiment": "shared_source",
                "method": "step_level",
                "seed": seed,
                "candidate_id": ci.intervention_id,
                "candidate_label": label,
                "cee": st_cee,
                "prevented": not st_failed if st_err is None else False,
                "runtime_ms": st_ms,
                "error": st_err,
            })

    return results


# ===================================================================
# Negative controls (Section 9)
# ===================================================================


def run_negative_controls(seeds: list[int]) -> list[dict]:
    """Run interventions expected to have zero effect."""
    results = []

    for seed in seeds:
        print(f"  Negative control seed={seed}")
        with deterministic_ids(seed=seed):
            scenario = generate_distractor(seed=seed)

        evaluator = get_evaluator(scenario)
        irrelevant_ids = set(scenario.ground_truth.irrelevant_channel_ids)

        for ci in scenario.candidates:
            if ci.intervention_id not in irrelevant_ids:
                continue

            try:
                intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
                iset = InterventionSet(
                    baseline_run_id=scenario.run.run_id,
                    interventions=[intv],
                )
                engine = CounterfactualReplayEngine()
                result = engine.replay(scenario.run, iset)

                if result.counterfactual_run is not None:
                    still_failed = evaluator(result.counterfactual_run)
                    cee = 1.0 - (1.0 if still_failed else 0.0)
                else:
                    cee = 0.0
                    still_failed = True

                results.append({
                    "experiment": "negative_control",
                    "seed": seed,
                    "candidate_id": ci.intervention_id,
                    "expected_cee": 0.0,
                    "actual_cee": cee,
                    "false_positive": cee > 0,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "experiment": "negative_control",
                    "seed": seed,
                    "candidate_id": ci.intervention_id,
                    "expected_cee": 0.0,
                    "actual_cee": None,
                    "false_positive": None,
                    "error": str(e),
                })

    return results


# ===================================================================
# Replay convergence (Section 10)
# ===================================================================


def run_replay_convergence(seed: int = 42) -> list[dict]:
    """Test how CEE estimates change with replay count."""
    results = []
    replay_counts = [1, 3, 5, 10, 25]

    with deterministic_ids(seed=seed):
        scenario = generate_single_cause(seed=seed)
    evaluator = get_evaluator(scenario)
    tool_registry = create_default_tool_registry()

    if not scenario.candidates:
        return results

    ci = scenario.candidates[0]  # Causal candidate

    for n_trials in replay_counts:
        print(f"  Replay convergence n={n_trials}")
        estimator = CEEEstimator(
            baseline_run=scenario.run,
            evaluator=evaluator,
            evidence_graph=scenario.evidence_graph,
            tool_registry=tool_registry,
            num_trials=n_trials,
        )
        cee_result = estimator.estimate(ci, ci)

        results.append({
            "experiment": "replay_convergence",
            "seed": seed,
            "n_trials": n_trials,
            "cee": cee_result.cee,
            "ci_lower": cee_result.ci_lower,
            "ci_upper": cee_result.ci_upper,
            "ci_width": cee_result.ci_upper - cee_result.ci_lower,
            "num_valid_trials": cee_result.num_valid_trials,
        })

    return results


# ===================================================================
# Seed robustness (Section 11)
# ===================================================================


def run_seed_robustness(seeds: list[int]) -> list[dict]:
    """Test metric stability across seeds."""
    results = []
    tool_registry = create_default_tool_registry()

    for seed in seeds:
        print(f"  Seed robustness seed={seed}")
        with deterministic_ids(seed=seed):
            scenario = generate_single_cause(seed=seed)
        evaluator = get_evaluator(scenario)

        if not scenario.candidates:
            continue

        # Use first causal candidate
        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        causal_candidates = [
            ci for ci in scenario.candidates
            if ci.intervention_id in causal_ids
        ]

        if not causal_candidates:
            continue

        ci = causal_candidates[0]
        estimator = CEEEstimator(
            baseline_run=scenario.run,
            evaluator=evaluator,
            evidence_graph=scenario.evidence_graph,
            tool_registry=tool_registry,
            num_trials=5,
        )
        cee_result = estimator.estimate(ci, ci)

        results.append({
            "experiment": "seed_robustness",
            "seed": seed,
            "family": "BF-A",
            "candidate_id": ci.intervention_id,
            "cee": cee_result.cee,
            "ci_lower": cee_result.ci_lower,
            "ci_upper": cee_result.ci_upper,
            "num_valid_trials": cee_result.num_valid_trials,
        })

    return results


# ===================================================================
# Full benchmark smoke (Section 18)
# ===================================================================


def run_benchmark_smoke(seeds: list[int]) -> list[dict]:
    """Run the benchmark runner on all families with 3 seeds."""
    results = []

    families = {
        "BF-A": generate_single_cause,
        "BF-B": generate_redundant,
        "BF-C": generate_complementary,
        "BF-D": generate_distractor,
        "BF-E": generate_cascade,
        "BF-F": generate_cost_asymmetric,
    }

    for seed in seeds:
        for family, generator in families.items():
            print(f"  Benchmark smoke: {family} seed={seed}")
            try:
                with deterministic_ids(seed=seed):
                    scenario = generator(seed=seed)
                evaluator = get_evaluator(scenario)

                # Run all methods
                methods_to_test = {
                    "B1_random": RandomBaseline(scenario_seed=seed),
                    "B2_provenance": ProvenanceOnlyBaseline(),
                    "B4_structural": GraphStructuralBaseline(),
                }

                for method_name, method in methods_to_test.items():
                    try:
                        selection = method.select(
                            scenario.candidates,
                            scenario.failure,
                            scenario.evidence_graph,
                            scenario.run,
                            evaluator,
                        )

                        # Compute metrics
                        metric_eval = MetricEvaluator()
                        metrics = metric_eval.compute(selection, scenario.ground_truth)

                        results.append({
                            "experiment": "benchmark_smoke",
                            "seed": seed,
                            "family": family,
                            "method": method_name,
                            "f1": metrics.attribution.causal_f1 if metrics.attribution else None,
                            "recall_at_1": metrics.attribution.recall_at_1 if metrics.attribution else None,
                            "precision": metrics.attribution.causal_precision if metrics.attribution else None,
                            "prevention_rate": metrics.prevention.failure_prevention_rate if metrics.prevention else None,
                            "error": None,
                        })
                    except Exception as e:
                        results.append({
                            "experiment": "benchmark_smoke",
                            "seed": seed,
                            "family": family,
                            "method": method_name,
                            "f1": None,
                            "recall_at_1": None,
                            "precision": None,
                            "prevention_rate": None,
                            "error": str(e),
                        })

            except Exception as e:
                results.append({
                    "experiment": "benchmark_smoke",
                    "seed": seed,
                    "family": family,
                    "method": "SCENARIO_GENERATION",
                    "f1": None,
                    "recall_at_1": None,
                    "precision": None,
                    "prevention_rate": None,
                    "error": str(e),
                })

    return results


# ===================================================================
# Main
# ===================================================================


def main():
    out_dir = Path("research_stage1/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = [42, 1, 7]
    all_results: dict[str, list] = {}

    print("=" * 60)
    print("STAGE 1 SMOKE CAMPAIGN")
    print("=" * 60)
    print()

    # 1. Shared-source experiment
    print("[1/5] Shared-source experiment (PRIMARY NOVELTY)")
    ss_results = run_shared_source_experiment(seeds)
    all_results["shared_source"] = ss_results
    with open(out_dir / "shared_source.json", "w") as f:
        json.dump(ss_results, f, indent=2)
    print(f"  -> {len(ss_results)} entries\n")

    # 2. Negative controls
    print("[2/5] Negative controls")
    nc_results = run_negative_controls(seeds)
    all_results["negative_controls"] = nc_results
    with open(out_dir / "negative_controls.json", "w") as f:
        json.dump(nc_results, f, indent=2)
    print(f"  -> {len(nc_results)} entries\n")

    # 3. Replay convergence
    print("[3/5] Replay convergence")
    rc_results = run_replay_convergence(seed=42)
    all_results["replay_convergence"] = rc_results
    with open(out_dir / "replay_convergence.json", "w") as f:
        json.dump(rc_results, f, indent=2)
    print(f"  -> {len(rc_results)} entries\n")

    # 4. Seed robustness
    print("[4/5] Seed robustness")
    sr_seeds = [1, 2, 3, 42, 100]
    sr_results = run_seed_robustness(sr_seeds)
    all_results["seed_robustness"] = sr_results
    with open(out_dir / "seed_robustness.json", "w") as f:
        json.dump(sr_results, f, indent=2)
    print(f"  -> {len(sr_results)} entries\n")

    # 5. Benchmark smoke
    print("[5/5] Benchmark smoke (3 seeds x 6 families x 3 methods)")
    bm_results = run_benchmark_smoke(seeds)
    all_results["benchmark_smoke"] = bm_results
    with open(out_dir / "benchmark_smoke.json", "w") as f:
        json.dump(bm_results, f, indent=2)
    print(f"  -> {len(bm_results)} entries\n")

    # Summary
    print("=" * 60)
    print("SMOKE CAMPAIGN SUMMARY")
    print("=" * 60)

    # Shared source summary
    print("\n--- SHARED SOURCE (PRIMARY NOVELTY) ---")
    for method in ["channel_level", "step_level"]:
        causal = [r for r in ss_results if r["method"] == method and r["candidate_label"] == "causal"]
        irrel = [r for r in ss_results if r["method"] == method and r["candidate_label"] == "irrelevant"]

        causal_prevented = sum(1 for r in causal if r["prevented"])
        irrel_prevented = sum(1 for r in irrel if r["prevented"])

        print(f"  {method}:")
        print(f"    Causal: {causal_prevented}/{len(causal)} prevented")
        print(f"    Irrelevant: {irrel_prevented}/{len(irrel)} prevented (false positives)")

    # Negative controls
    print("\n--- NEGATIVE CONTROLS ---")
    fp_count = sum(1 for r in nc_results if r.get("false_positive"))
    total = len([r for r in nc_results if r.get("false_positive") is not None])
    print(f"  False positive rate: {fp_count}/{total}")

    # Replay convergence
    print("\n--- REPLAY CONVERGENCE ---")
    for r in rc_results:
        print(f"  n={r['n_trials']:3d}: CEE={r['cee']:.3f} CI=[{r['ci_lower']:.3f}, {r['ci_upper']:.3f}] width={r['ci_width']:.3f}")

    # Seed robustness
    print("\n--- SEED ROBUSTNESS ---")
    cees = [r["cee"] for r in sr_results if r["cee"] is not None]
    if cees:
        mean_cee = sum(cees) / len(cees)
        var_cee = sum((c - mean_cee) ** 2 for c in cees) / len(cees)
        std_cee = var_cee ** 0.5
        cv = std_cee / mean_cee if mean_cee > 0 else float("inf")
        print(f"  CEE: mean={mean_cee:.3f} std={std_cee:.3f} CV={cv:.3f}")
        for r in sr_results:
            print(f"    seed={r['seed']}: CEE={r['cee']:.3f}")

    # Benchmark smoke
    print("\n--- BENCHMARK SMOKE ---")
    errors = [r for r in bm_results if r.get("error")]
    print(f"  Total entries: {len(bm_results)}")
    print(f"  Errors: {len(errors)}")
    for r in errors:
        print(f"    {r['family']}/{r['method']}/seed={r['seed']}: {r['error'][:80]}")

    # Write full summary
    with open(out_dir / "smoke_summary.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nAll raw results written to {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
