"""Debug the CEE=0 issue."""
import sys
sys.path.insert(0, ".")

from captain.benchmarks.scenarios import generate_single_cause, get_evaluator
from captain.models.ids import deterministic_ids
from captain.analysis.estimator import channel_to_intervention
from captain.intervention.model import InterventionSet
from captain.replay.engine import CounterfactualReplayEngine

with deterministic_ids(42):
    s = generate_single_cause(seed=42)
ev = get_evaluator(s)

# Show events
for e in s.run.events:
    p = e.payload
    if isinstance(p, dict) and "result" in p:
        print(f"  {e.event_type.value}[si={p.get('step_index')}]: result={str(p['result'])[:80]}")
    elif isinstance(p, dict) and "content" in p:
        print(f"  {e.event_type.value}: content={str(p['content'])[:80]}")

print()
ci = s.candidates[0]
intv = channel_to_intervention(ci, s.run, s.evidence_graph)
print(f"Intervention: type={intv.intervention_type} target={intv.target_id[:20]}")

iset = InterventionSet(baseline_run_id=s.run.run_id, interventions=[intv])
engine = CounterfactualReplayEngine()
result = engine.replay(s.run, iset)
cf = result.counterfactual_run
print(f"CF status: {result.status}")
if cf:
    for e in cf.events:
        p = e.payload
        if isinstance(p, dict) and "result" in p:
            print(f"  CF {e.event_type.value}[si={p.get('step_index')}]: result={str(p['result'])[:80]}")
        elif isinstance(p, dict) and "content" in p:
            print(f"  CF {e.event_type.value}: content={str(p['content'])[:80]}")
    print(f"CF still failed: {ev(cf)}")
