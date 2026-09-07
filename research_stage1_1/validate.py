"""Stage 1.1 comprehensive validation runner.

Runs ALL acceptance criteria and produces machine-readable results.
"""

from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, ".")

from captain.agent.tools import create_default_tool_registry
from captain.analysis.estimator import CEEEstimator, channel_to_intervention
from captain.benchmarks.scenarios import (
    generate_distractor,
    generate_shared_source,
    generate_single_cause,
    get_evaluator,
)
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus


def _run_cee(scenario, candidate, evaluator, evidence_graph):
    """Run a single CEE measurement."""
    intv = channel_to_intervention(candidate, scenario.run, evidence_graph)
    iset = InterventionSet(
        baseline_run_id=scenario.run.run_id,
        interventions=[intv],
    )
    result = CounterfactualReplayEngine().replay(scenario.run, iset)
    if result.counterfactual_run is None:
        return {"status": "rejected", "reason": result.rejection_reason}

    f = evaluator(scenario.run)
    cf = evaluator(result.counterfactual_run)
    cee = (1.0 if f else 0.0) - (1.0 if cf else 0.0)
    return {
        "status": "success",
        "factual_failed": f,
        "cf_failed": cf,
        "cee": cee,
        "target_id": intv.target_id[:20],
        "intervention_type": str(intv.intervention_type.value),
    }


def run_validation(seed=42, n_replays=3, n_reproducibility=3):
    """Run full Stage 1.1 validation."""
    results = {
        "stage": "1.1",
        "seed": seed,
        "n_replays": n_replays,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    print("=" * 60)
    print("STAGE 1.1 VALIDATION")
    print("=" * 60)

    # ---- A. Positive controls ----
    print("\n--- A. CEE Responsiveness ---")
    with deterministic_ids(seed):
        s = generate_single_cause(seed=seed)
    ev = get_evaluator(s)
    causal_ids = set(s.ground_truth.causal_channel_ids)
    irrel_ids = set(s.ground_truth.irrelevant_channel_ids)

    positive_controls = []
    for ci in s.candidates:
        if ci.intervention_id in causal_ids:
            r = _run_cee(s, ci, ev, s.evidence_graph)
            r["label"] = "causal"
            r["candidate_id"] = ci.intervention_id[:20]
            positive_controls.append(r)
            print(f"  CAUSAL: CEE={r.get('cee', 'N/A')}, CF_failed={r.get('cf_failed')}")

    results["positive_controls"] = positive_controls
    a_pass = any(p.get("cee", 0) > 0 for p in positive_controls)
    print(f"  A. PASS: {a_pass}")

    # ---- B. Negative controls ----
    print("\n--- B. Negative Controls ---")
    negative_controls = []
    for ci in s.candidates:
        if ci.intervention_id in irrel_ids:
            r = _run_cee(s, ci, ev, s.evidence_graph)
            r["label"] = "distractor"
            r["candidate_id"] = ci.intervention_id[:20]
            negative_controls.append(r)
            print(f"  DISTRACTOR: CEE={r.get('cee', 'N/A')}, CF_failed={r.get('cf_failed')}")

    # Also test BF-D scenario distractors
    with deterministic_ids(seed):
        sd = generate_distractor(seed=seed)
    evd = get_evaluator(sd)
    dist_ids = set(sd.ground_truth.irrelevant_channel_ids)
    for ci in sd.candidates:
        if ci.intervention_id in dist_ids:
            r = _run_cee(sd, ci, evd, sd.evidence_graph)
            r["label"] = "bf_d_distractor"
            r["candidate_id"] = ci.intervention_id[:20]
            negative_controls.append(r)

    results["negative_controls"] = negative_controls
    b_pass = all(n.get("cee", 1) == 0.0 for n in negative_controls)
    print(f"  B. PASS: {b_pass}")

    # ---- C. No leakage ----
    print("\n--- C. Leakage Check ---")
    import inspect

    ev_src = inspect.getsource(ev)
    leakage_checks = {
        "evaluator_uses_intervention_id": "intervention_id" in ev_src,
        "evaluator_uses_ground_truth": "ground_truth" in ev_src,
        "evaluator_uses_is_counterfactual": "is_counterfactual" in ev_src,
    }
    c_pass = not any(leakage_checks.values())
    results["leakage_checks"] = leakage_checks
    print(f"  C. PASS: {c_pass}")

    # ---- D. Channel isolation ----
    print("\n--- D. Channel Isolation (Shared-Source) ---")
    with deterministic_ids(seed):
        ss = generate_shared_source(seed=seed)
    evs = get_evaluator(ss)
    ss_causal = set(ss.ground_truth.causal_channel_ids)

    shared_source_tests = []
    for ci in ss.candidates:
        r = _run_cee(ss, ci, evs, ss.evidence_graph)
        r["label"] = "causal" if ci.intervention_id in ss_causal else "non_causal"
        r["candidate_id"] = ci.intervention_id[:20]
        shared_source_tests.append(r)
        print(f"  {r['label']}: CEE={r.get('cee', 'N/A')}")

    # Verify channel isolation: check that validator output survives
    causal_cands = [ci for ci in ss.candidates if ci.intervention_id in ss_causal]
    d_pass = False
    if causal_cands:
        ci = causal_cands[0]
        intv = channel_to_intervention(ci, ss.run, ss.evidence_graph)
        iset = InterventionSet(
            baseline_run_id=ss.run.run_id,
            interventions=[intv],
        )
        r = CounterfactualReplayEngine().replay(ss.run, iset)
        if r.counterfactual_run:
            cf_text = ""
            for evt in r.counterfactual_run.events:
                if evt.payload:
                    cf_text += str(evt.payload)
            d_pass = "ok" in cf_text.lower()
    results["shared_source_tests"] = shared_source_tests
    print(f"  D. Channel isolation PASS: {d_pass}")

    # ---- E. Step-vs-channel distinction ----
    print("\n--- E. Step vs Channel Distinction ---")
    step_vs_channel = []
    if causal_cands:
        ci = causal_cands[0]
        ch_intv = channel_to_intervention(ci, ss.run, ss.evidence_graph)
        st_intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=ci.baseline_run_id,
            target_id=ci.event_id,
            replacement_value="",
            description="Step-level block",
        )
        step_vs_channel.append({
            "channel_target": ch_intv.target_id[:20],
            "channel_type": str(ch_intv.intervention_type.value),
            "step_target": st_intv.target_id[:20],
            "step_type": str(st_intv.intervention_type.value),
            "targets_differ": ch_intv.target_id != st_intv.target_id,
            "types_differ": ch_intv.intervention_type != st_intv.intervention_type,
        })
    e_pass = any(
        sv.get("targets_differ") or sv.get("types_differ")
        for sv in step_vs_channel
    )
    results["step_vs_channel"] = step_vs_channel
    print(f"  E. PASS: {e_pass}")

    # ---- F. Reproducibility ----
    print("\n--- F. Reproducibility ---")
    repro_cees = []
    for trial in range(n_reproducibility):
        with deterministic_ids(seed):
            sr = generate_single_cause(seed=seed)
        evr = get_evaluator(sr)
        causal_r = [c for c in sr.candidates if c.intervention_id in set(sr.ground_truth.causal_channel_ids)]
        if causal_r:
            r = _run_cee(sr, causal_r[0], evr, sr.evidence_graph)
            repro_cees.append(r.get("cee"))

    f_pass = len(set(repro_cees)) == 1 and repro_cees[0] is not None
    results["reproducibility"] = {
        "trials": n_reproducibility,
        "cee_values": repro_cees,
        "identical": f_pass,
    }
    print(f"  F. PASS: {f_pass} (CEEs: {repro_cees})")

    # ---- G. Regression ----
    print("\n--- G. Regression ---")
    # Run via subprocess to capture exit code
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True,
    )
    test_output = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
    g_pass = r.returncode == 0
    results["test_summary"] = {
        "returncode": r.returncode,
        "summary": test_output,
        "pass": g_pass,
    }
    print(f"  G. PASS: {g_pass} ({test_output})")

    # ---- Final verdict ----
    all_pass = all([a_pass, b_pass, c_pass, d_pass, e_pass, f_pass, g_pass])

    criteria = {
        "A_cee_responsiveness": a_pass,
        "B_negative_control": b_pass,
        "C_no_leakage": c_pass,
        "D_channel_isolation": d_pass,
        "E_step_channel_distinction": e_pass,
        "F_reproducibility": f_pass,
        "G_regression": g_pass,
    }
    results["criteria"] = criteria

    if all_pass:
        results["status"] = "PASS"
        verdict = "PASS -- READY FOR STAGE 2"
    else:
        failed = [k for k, v in criteria.items() if not v]
        results["status"] = "FAIL"
        verdict = f"FAIL -- {', '.join(failed)}"

    results["verdict"] = verdict
    print(f"\n{'=' * 60}")
    print(f"VERDICT: {verdict}")
    print(f"{'=' * 60}")

    return results


if __name__ == "__main__":
    results = run_validation(seed=42)

    # Save machine-readable results
    out_path = "research_stage1_1/09_STAGE1_1_RESULTS.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
