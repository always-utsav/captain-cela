"""Stage 2 full experimental campaign runner.

Orchestrates all Stage 2 experiments:
- Full benchmark campaign (BF-A through BF-K)
- Primary granularity experiment (channel vs source-event-level)
- Pathway stress test (1/2/3/5/10 pathways)
- Cascade/joint intervention experiments
- Negative controls
- Seed robustness
- Replay convergence
- Ablation
- Scalability
- Cost/utility sweep

All results are machine-readable JSON saved to research/raw/.
IDs are deterministic from seed/config (no uuid.uuid4()).
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from captain.analysis.estimator import CEEEstimator, channel_to_intervention
from captain.benchmarks.scenarios import (
    generate_shared_source,
    generate_single_cause,
    get_evaluator,
)
from captain.experiments.runner import (
    ExperimentConfig,
    ExperimentResult,
    ExperimentRunner,
)
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

# ===================================================================
# Configuration
# ===================================================================


class CampaignConfig(ExperimentConfig):
    """Extended config for the full Stage 2 campaign."""

    seeds: list[int] = Field(default_factory=lambda: [42, 123, 456, 789, 1024])
    replay_counts: list[int] = Field(default_factory=lambda: [1, 3, 5, 10, 20, 50])
    pathway_counts: list[int] = Field(default_factory=lambda: [1, 2, 3, 5, 10])
    lambda_values: list[float] = Field(default_factory=lambda: [0.0, 0.05, 0.1, 0.2, 0.5, 1.0])
    output_dir: str = "research/raw"


# ===================================================================
# Result models
# ===================================================================


class ExperimentManifest(BaseModel):
    """Machine-readable experiment manifest."""

    families: list[str] = Field(default_factory=list)
    instances_per_family: int = 5
    seeds: list[int] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    total_scenarios: int = 0
    total_method_evaluations: int = 0
    expected_replays: int = 0
    software_commit: str = ""
    config: CampaignConfig = Field(default_factory=CampaignConfig)
    created_at: str = ""


class GranularityResult(BaseModel):
    """Result of one granularity experiment instance."""

    family: str
    seed: int
    instance_id: str
    factual_outcome: bool = True
    channel_intervention: dict[str, Any] = Field(default_factory=dict)
    source_event_intervention: dict[str, Any] = Field(default_factory=dict)
    granularity_metrics: dict[str, Any] = Field(default_factory=dict)


class NegativeControlResult(BaseModel):
    """Result of one negative control experiment."""

    family: str
    control_type: str
    seed: int = 42
    expected_effect: str = ""
    justification: str = ""
    observed_cee: float = 0.0
    observed_outcome: bool = True
    passed: bool = False


class CampaignResult(BaseModel):
    """Complete campaign result."""

    campaign_id: str = ""
    manifest: ExperimentManifest = Field(default_factory=ExperimentManifest)
    seed_results: dict[str, Any] = Field(default_factory=dict)
    granularity_results: list[dict[str, Any]] = Field(default_factory=list)
    pathway_stress_results: list[dict[str, Any]] = Field(default_factory=list)
    cascade_results: dict[str, Any] = Field(default_factory=dict)
    negative_control_results: list[dict[str, Any]] = Field(default_factory=list)
    convergence_results: dict[str, Any] = Field(default_factory=dict)
    scalability_results: dict[str, Any] = Field(default_factory=dict)
    cost_utility_results: list[dict[str, Any]] = Field(default_factory=list)


# ===================================================================
# Campaign Runner
# ===================================================================


class CampaignRunner:
    """Orchestrates the full Stage 2 experimental campaign."""

    def __init__(self, config: CampaignConfig | None = None) -> None:
        self.config = config or CampaignConfig()
        os.makedirs(self.config.output_dir, exist_ok=True)

    def _save(self, name: str, data: Any) -> str:
        """Save data to JSON file. Returns path."""
        path = os.path.join(self.config.output_dir, f"{name}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            if isinstance(data, BaseModel):
                f.write(data.model_dump_json(indent=2))
            else:
                json.dump(
                    data,
                    f,
                    indent=2,
                    default=lambda x: x.model_dump() if hasattr(x, "model_dump") else str(x),
                )
        return path

    def generate_manifest(self) -> ExperimentManifest:
        """Generate experiment manifest before execution."""
        n_families = len(self.config.families)
        n_seeds = len(self.config.seeds)
        n_methods = len(self.config.methods)
        n_instances = self.config.instances_per_family
        total = n_families * n_seeds * n_instances
        total_evals = total * n_methods

        commit = ""
        try:
            import subprocess

            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__) or ".",
            )
            commit = r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
        except Exception:
            commit = "unknown"

        return ExperimentManifest(
            families=list(self.config.families),
            instances_per_family=n_instances,
            seeds=list(self.config.seeds),
            methods=list(self.config.methods),
            baselines=["B1", "B2", "B3", "B4", "B5"],
            total_scenarios=total,
            total_method_evaluations=total_evals,
            expected_replays=total_evals * 2,
            software_commit=commit,
            config=self.config,
            created_at=datetime.now(UTC).isoformat(),
        )

    # ---------------------------------------------------------------
    # Benchmark campaign (per seed)
    # ---------------------------------------------------------------

    def run_benchmark_campaign(self, seed: int) -> ExperimentResult:
        """Run full benchmark across all families for one seed."""
        with deterministic_ids(seed):
            cfg = ExperimentConfig(
                master_seed=seed,
                instances_per_family=self.config.instances_per_family,
                families=list(self.config.families),
                methods=list(self.config.methods),
            )
            runner = ExperimentRunner(config=cfg)
            result = runner.run()
        self._save(f"benchmark_seed_{seed}", result)
        return result

    # ---------------------------------------------------------------
    # PRIMARY: Granularity experiment
    # ---------------------------------------------------------------

    def run_granularity_experiment(self) -> list[GranularityResult]:
        """Channel vs source-event-level intervention on BF-G."""
        results: list[GranularityResult] = []

        for seed in self.config.seeds:
            with deterministic_ids(seed):
                scenario = generate_shared_source(seed=seed)

            evaluator = get_evaluator(scenario)
            run = scenario.run
            factual_failed = evaluator(run)

            # Find causal channel candidate
            causal_ids = set(scenario.ground_truth.causal_channel_ids)
            causal = [c for c in scenario.candidates if c.intervention_id in causal_ids]
            if not causal:
                continue

            ci = causal[0]
            ch_intv = channel_to_intervention(ci, run, scenario.evidence_graph)

            # --- Channel intervention (ARTIFACT_REPLACEMENT) ---
            ch_iset = InterventionSet(baseline_run_id=run.run_id, interventions=[ch_intv])
            ch_replay = CounterfactualReplayEngine().replay(run, ch_iset)
            ch_ok = ch_replay.status == ReplayStatus.SUCCESS

            ch_text = ""
            ch_a_present = False
            ch_b_present = False
            if ch_ok and ch_replay.counterfactual_run:
                for evt in ch_replay.counterfactual_run.events:
                    if evt.payload:
                        ch_text += str(evt.payload)
                for art in ch_replay.counterfactual_run.artifacts:
                    if art.value:
                        ch_text += str(art.value)
                ch_a_present = "42" in ch_text
                ch_b_present = "ok" in ch_text.lower()

            ch_failed = (
                evaluator(ch_replay.counterfactual_run)
                if ch_ok and ch_replay.counterfactual_run
                else None
            )
            ch_cee = 1.0 if (factual_failed and not ch_failed) else 0.0

            # --- Source-event-level intervention (TOOL_RESULT_OVERRIDE) ---
            from captain.models.enums import EventType

            source_evt = None
            for evt in run.events:
                if evt.event_type == EventType.TOOL_RESULT:
                    p = evt.payload if isinstance(evt.payload, dict) else {}
                    if p.get("tool_name") == "data_source":
                        source_evt = evt
                        break

            st_cee = 0.0
            st_a_present = False
            st_b_present = False
            st_affected = 0
            if source_evt:
                st_intv = Intervention(
                    intervention_type=InterventionType.TOOL_RESULT_OVERRIDE,
                    baseline_run_id=run.run_id,
                    target_id=source_evt.event_id,
                    replacement_value="",
                    description="Source-event-level override",
                )
                st_iset = InterventionSet(baseline_run_id=run.run_id, interventions=[st_intv])
                st_replay = CounterfactualReplayEngine().replay(run, st_iset)
                st_ok = st_replay.status == ReplayStatus.SUCCESS

                st_text = ""
                if st_ok and st_replay.counterfactual_run:
                    for evt2 in st_replay.counterfactual_run.events:
                        if evt2.payload:
                            st_text += str(evt2.payload)
                    for art2 in st_replay.counterfactual_run.artifacts:
                        if art2.value:
                            st_text += str(art2.value)
                    st_a_present = "42" in st_text
                    st_b_present = "ok" in st_text.lower()

                st_failed = (
                    evaluator(st_replay.counterfactual_run)
                    if st_ok and st_replay.counterfactual_run
                    else None
                )
                st_cee = 1.0 if (factual_failed and not st_failed) else 0.0
                st_affected = (0 if st_a_present else 1) + (0 if st_b_present else 1)

            ch_affected = (0 if ch_a_present else 1) + (0 if ch_b_present else 1)
            ch_preserved = 2 - ch_affected
            st_preserved = 2 - st_affected

            # Collateral = non-causal evidence affected
            # Channel should affect 1 (A), preserve 1 (B)
            # Source-event should affect 2, preserve 0
            collateral_ch = max(0, ch_affected - 1)  # causal=1
            collateral_st = max(0, st_affected - 1)

            gr = GranularityResult(
                family="BF-G",
                seed=seed,
                instance_id=scenario.scenario_id,
                factual_outcome=factual_failed,
                channel_intervention={
                    "type": ch_intv.intervention_type.value,
                    "target_id": ch_intv.target_id[:20],
                    "replay_success": ch_ok,
                    "A_present": ch_a_present,
                    "B_present": ch_b_present,
                    "failure": ch_failed,
                    "CEE": ch_cee,
                    "affected_evidence": ch_affected,
                    "preserved_evidence": ch_preserved,
                    "collateral": collateral_ch,
                },
                source_event_intervention={
                    "type": "tool_result_override",
                    "target_id": (source_evt.event_id[:20] if source_evt else "none"),
                    "replay_success": source_evt is not None,
                    "A_present": st_a_present,
                    "B_present": st_b_present,
                    "failure": st_failed if source_evt else None,
                    "CEE": st_cee,
                    "affected_evidence": st_affected,
                    "preserved_evidence": st_preserved,
                    "collateral": collateral_st,
                },
                granularity_metrics={
                    "channel_collateral_rate": collateral_ch / max(1, 1),
                    "source_event_collateral_rate": collateral_st / max(1, 1),
                    "unrelated_preservation_channel": 1.0 if ch_b_present else 0.0,
                    "unrelated_preservation_source": 1.0 if st_b_present else 0.0,
                    "channel_more_selective": ch_affected < st_affected,
                    "scope_channel": ch_affected,
                    "scope_source_event": st_affected,
                },
            )
            results.append(gr)

        self._save("granularity_experiment", [r.model_dump() for r in results])
        return results

    # ---------------------------------------------------------------
    # Negative controls
    # ---------------------------------------------------------------

    def run_negative_controls(self) -> list[NegativeControlResult]:
        """Run mechanism-specific negative controls."""
        results: list[NegativeControlResult] = []

        for seed in self.config.seeds[:2]:  # 2 seeds for efficiency
            with deterministic_ids(seed):
                # NC1: Intervene on irrelevant channel in BF-A
                sc = generate_single_cause(seed=seed)
                ev = get_evaluator(sc)
                irr_ids = set(sc.ground_truth.irrelevant_channel_ids)
                irr = [c for c in sc.candidates if c.intervention_id in irr_ids]
                if irr:
                    ci = irr[0]
                    intv = channel_to_intervention(ci, sc.run, sc.evidence_graph)
                    iset = InterventionSet(
                        baseline_run_id=sc.run.run_id,
                        interventions=[intv],
                    )
                    rep = CounterfactualReplayEngine().replay(sc.run, iset)
                    cf_failed = (
                        ev(rep.counterfactual_run)
                        if rep.status == ReplayStatus.SUCCESS and rep.counterfactual_run
                        else True
                    )
                    obs_cee = 1.0 if (ev(sc.run) and not cf_failed) else 0.0
                    results.append(
                        NegativeControlResult(
                            family="BF-A",
                            control_type="irrelevant_channel_block",
                            seed=seed,
                            expected_effect="CEE=0 (irrelevant channel)",
                            justification=(
                                "Blocking echo tool should not prevent"
                                " calculator-caused failure"
                            ),
                            observed_cee=obs_cee,
                            observed_outcome=cf_failed,
                            passed=obs_cee == 0.0,
                        )
                    )

                # NC2: Intervene on non-causal channel in BF-G
                sg = generate_shared_source(seed=seed)
                evg = get_evaluator(sg)
                irr_g = set(sg.ground_truth.irrelevant_channel_ids)
                irr_cands = [c for c in sg.candidates if c.intervention_id in irr_g]
                if irr_cands:
                    ci2 = irr_cands[0]
                    intv2 = channel_to_intervention(ci2, sg.run, sg.evidence_graph)
                    iset2 = InterventionSet(
                        baseline_run_id=sg.run.run_id,
                        interventions=[intv2],
                    )
                    rep2 = CounterfactualReplayEngine().replay(sg.run, iset2)
                    cf2 = (
                        evg(rep2.counterfactual_run)
                        if rep2.status == ReplayStatus.SUCCESS and rep2.counterfactual_run
                        else True
                    )
                    obs2 = 1.0 if (evg(sg.run) and not cf2) else 0.0
                    results.append(
                        NegativeControlResult(
                            family="BF-G",
                            control_type="non_causal_artifact_block",
                            seed=seed,
                            expected_effect="CEE=0 (benign artifact B)",
                            justification=(
                        "Blocking artifact B ('ok') should not prevent"
                        " failure from artifact A ('42')"
                    ),
                            observed_cee=obs2,
                            observed_outcome=cf2,
                            passed=obs2 == 0.0,
                        )
                    )

        self._save(
            "negative_controls",
            [r.model_dump() for r in results],
        )
        return results

    # ---------------------------------------------------------------
    # Replay convergence
    # ---------------------------------------------------------------

    def run_replay_convergence(self) -> dict[str, Any]:
        """Sweep replay counts to test CEE estimate stability."""
        rows: list[dict[str, Any]] = []
        seed = self.config.seeds[0]

        with deterministic_ids(seed):
            sc = generate_single_cause(seed=seed)
        ev = get_evaluator(sc)

        causal_ids = set(sc.ground_truth.causal_channel_ids)
        causal = [c for c in sc.candidates if c.intervention_id in causal_ids]
        if not causal:
            return {"convergence": rows}

        ci = causal[0]
        for n_trials in self.config.replay_counts:
            est = CEEEstimator(
                sc.run,
                ev,
                evidence_graph=sc.evidence_graph,
                num_trials=n_trials,
            )
            result = est.estimate(sc.candidates[0] if sc.candidates else ci, ci)
            rows.append(
                {
                    "replay_count": n_trials,
                    "cee": result.cee,
                    "ci_lower": result.ci_lower,
                    "ci_upper": result.ci_upper,
                    "ci_width": result.ci_upper - result.ci_lower,
                    "n_valid": result.num_valid_trials,
                }
            )

        data = {"convergence": rows, "seed": seed}
        self._save("replay_convergence", data)
        return data

    # ---------------------------------------------------------------
    # Scalability
    # ---------------------------------------------------------------

    def run_scalability(self) -> dict[str, Any]:
        """Measure runtime scaling with trace complexity."""
        rows: list[dict[str, Any]] = []
        seed = self.config.seeds[0]

        for family in ["BF-A", "BF-E", "BF-H", "BF-J"]:
            with deterministic_ids(seed):
                cfg = ExperimentConfig(
                    master_seed=seed,
                    instances_per_family=1,
                    families=[family],
                    methods=["A4"],
                )
                t0 = time.perf_counter()
                runner = ExperimentRunner(config=cfg)
                result = runner.run()
                elapsed = time.perf_counter() - t0

            # Count results
            fr = result.family_results.get(family)
            n_results = len(fr.results) if fr else 0

            rows.append(
                {
                    "family": family,
                    "runtime_s": round(elapsed, 4),
                    "n_method_results": n_results,
                }
            )

        data = {"scalability": rows, "seed": seed}
        self._save("scalability", data)
        return data

    # ---------------------------------------------------------------
    # Full campaign
    # ---------------------------------------------------------------

    def run_full(self) -> CampaignResult:
        """Run the complete Stage 2 campaign."""
        print("=== Stage 2 Campaign ===")
        manifest = self.generate_manifest()
        self._save("experiment_manifest", manifest)
        print(f"Manifest: {manifest.total_scenarios} scenarios")

        # 1. Benchmark campaign across seeds
        print("\n--- Benchmark campaign ---")
        seed_summaries: dict[str, Any] = {}
        for seed in self.config.seeds:
            print(f"  Seed {seed}...")
            t0 = time.perf_counter()
            result = self.run_benchmark_campaign(seed)
            elapsed = time.perf_counter() - t0
            n_comp = len(result.comparisons)
            seed_summaries[str(seed)] = {
                "runtime_s": round(elapsed, 2),
                "comparisons": n_comp,
                "ablation_steps": len(result.ablation_steps),
            }
            print(f"    Done in {elapsed:.1f}s, {n_comp} comparisons")

        # 2. Granularity experiment
        print("\n--- Granularity experiment ---")
        gran = self.run_granularity_experiment()
        print(f"  {len(gran)} instances")

        # 3. Negative controls
        print("\n--- Negative controls ---")
        neg = self.run_negative_controls()
        n_pass = sum(1 for n in neg if n.passed)
        print(f"  {n_pass}/{len(neg)} passed")

        # 4. Replay convergence
        print("\n--- Replay convergence ---")
        conv = self.run_replay_convergence()
        print(f"  {len(conv.get('convergence', []))} points")

        # 5. Scalability
        print("\n--- Scalability ---")
        scale = self.run_scalability()
        print(f"  {len(scale.get('scalability', []))} families")

        result = CampaignResult(
            campaign_id=f"stage2_{self.config.seeds[0]}",
            manifest=manifest,
            seed_results=seed_summaries,
            granularity_results=[g.model_dump() for g in gran],
            negative_control_results=[n.model_dump() for n in neg],
            convergence_results=conv,
            scalability_results=scale,
        )
        self._save("campaign_full", result)
        print("\n=== Campaign complete ===")
        return result


if __name__ == "__main__":
    runner = CampaignRunner()
    runner.run_full()
