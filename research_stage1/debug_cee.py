"""Validate CEE responsiveness after Blocker A fix."""

import sys

sys.path.insert(0, ".")

from captain.analysis.estimator import channel_to_intervention
from captain.benchmarks.scenarios import generate_single_cause, get_evaluator
from captain.intervention.model import InterventionSet
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine

with deterministic_ids(42):
    s = generate_single_cause(seed=42)
ev = get_evaluator(s)

print("=== FACTUAL ===")
print(f"  Factual failed: {ev(s.run)}")
print(f"  Candidates: {len(s.candidates)}")
print(f"  Causal IDs: {s.ground_truth.causal_channel_ids}")
print()

for i, ci in enumerate(s.candidates):
    is_causal = ci.intervention_id in s.ground_truth.causal_channel_ids
    label = "CAUSAL" if is_causal else "DISTRACTOR"

    intv = channel_to_intervention(ci, s.run, s.evidence_graph)
    iset = InterventionSet(baseline_run_id=s.run.run_id, interventions=[intv])
    engine = CounterfactualReplayEngine()
    result = engine.replay(s.run, iset)

    if result.counterfactual_run:
        cf_failed = ev(result.counterfactual_run)
        cee = 1.0 if (ev(s.run) and not cf_failed) else 0.0

        # Show what changed
        cf_events = result.counterfactual_run.events
        for e in cf_events:
            p = e.payload if isinstance(e.payload, dict) else {}
            r = p.get("result", "")
            if r:
                print(f"  CF {e.event_type.value}[si={p.get('step_index')}]: {str(r)[:60]}")
        content = ""
        for e in cf_events:
            p = e.payload if isinstance(e.payload, dict) else {}
            if p.get("content"):
                content = p["content"]
        if content:
            print(f"  CF output: {content[:60]}")

        print(f"  [{label}] candidate {i}: CF_failed={cf_failed} CEE={cee}")
    else:
        print(f"  [{label}] candidate {i}: REJECTED - {result.rejection_reason}")
    print()
