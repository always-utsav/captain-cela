"""Determinism verification script.

Run the same benchmark scenario 3 times with deterministic IDs
and verify that outputs are identical.
"""

import json
import sys

sys.path.insert(0, ".")

from captain.benchmarks.scenarios import generate_single_cause
from captain.models.ids import deterministic_ids


def run_once(seed: int) -> dict:
    """Run a single benchmark scenario and extract key identifiers."""
    with deterministic_ids(seed):
        scenario = generate_single_cause(seed=seed)

    return {
        "scenario_id": scenario.scenario_id,
        "run_id": scenario.run.run_id,
        "event_ids": [e.event_id for e in scenario.run.events],
        "artifact_ids": [a.artifact_id for a in scenario.run.artifacts],
        "evidence_ids": [e.evidence_id for e in scenario.evidence_graph.evidence],
        "candidate_ids": [c.intervention_id for c in scenario.candidates],
        "causal_channel_ids": scenario.ground_truth.causal_channel_ids,
        "irrelevant_channel_ids": scenario.ground_truth.irrelevant_channel_ids,
        "num_events": len(scenario.run.events),
        "num_artifacts": len(scenario.run.artifacts),
        "num_evidence": scenario.evidence_graph.evidence_count,
        "num_candidates": len(scenario.candidates),
    }


def main():
    print("=== DETERMINISM VERIFICATION ===")
    print()

    results = []
    for trial in range(3):
        r = run_once(42)
        results.append(r)
        print(f"Trial {trial + 1}:")
        print(f"  run_id: {r['run_id']}")
        print(f"  events: {r['num_events']}, artifacts: {r['num_artifacts']}")
        print(f"  evidence: {r['num_evidence']}, candidates: {r['num_candidates']}")
        print(f"  first event: {r['event_ids'][0]}")
        print(f"  first artifact: {r['artifact_ids'][0]}")
        print(f"  first evidence: {r['evidence_ids'][0]}")
        print()

    # Compare all trials
    all_match = True
    for i in range(1, len(results)):
        for key in results[0]:
            if results[i][key] != results[0][key]:
                print(f"MISMATCH at trial {i + 1}, key={key}")
                print(f"  Expected: {results[0][key]}")
                print(f"  Got:      {results[i][key]}")
                all_match = False

    if all_match:
        print("DETERMINISM: PASS — All 3 trials produced identical outputs")
    else:
        print("DETERMINISM: FAIL — Outputs differ across trials")

    # Also verify WITHOUT deterministic context (should be different)
    r_nondeterministic1 = run_nondeterministic(42)
    r_nondeterministic2 = run_nondeterministic(42)
    nd_match = r_nondeterministic1["run_id"] == r_nondeterministic2["run_id"]
    print(f"\nNon-deterministic control: IDs {'SAME' if nd_match else 'DIFFERENT'} (expected: DIFFERENT)")

    return 0 if all_match and not nd_match else 1


def run_nondeterministic(seed: int) -> dict:
    """Run without deterministic context."""
    scenario = generate_single_cause(seed=seed)
    return {
        "run_id": scenario.run.run_id,
    }


if __name__ == "__main__":
    sys.exit(main())
