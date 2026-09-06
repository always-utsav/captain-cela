# 10 DETERMINISM REPORT

## Implementation

### Mechanism
- `captain/models/ids.py`: `deterministic_ids(seed)` context manager
- Uses `hashlib.sha256(f"{seed}:{prefix}:{counter}")` for deterministic hex IDs
- Thread-local storage for per-prefix counters
- When context NOT active: falls back to `uuid.uuid4()` (default)

### Files Modified
| File | Functions | Prefixes |
|------|-----------|----------|
| captain/models/ids.py | generate_run_id, generate_event_id, generate_artifact_id | run_, evt_, art_ |
| captain/evidence/model.py | generate_evidence_id | evi_ |
| captain/analysis/estimator.py | _gen_trial_id, _gen_result_id | trial_, cee_ |
| captain/analysis/cascade.py | _gen_set_id, _gen_cascade_id, _gen_selection_id | iset_, casc_, sel_ |
| captain/failures/model.py | generate_failure_id, generate_candidate_id, ChannelIntervention | fail_, cand_, cintv_ |
| captain/intervention/model.py | generate_intervention_id | intv_ |
| captain/benchmarks/scenarios.py | BenchmarkScenario.scenario_id | bench_ |
| captain/benchmarks/baselines.py | OracleResult.oracle_id | oracle_ |

### Design Constraints
- Preserved all ID prefixes and types
- Did NOT break existing interfaces
- Did NOT overwrite historical Stage-18 artifacts
- IDs do NOT encode hidden causal truth
- Non-deterministic mode unchanged (uuid4 fallback)

## Verification

### Test 1: Three-Run Identity (PASS)
```
Trial 1: run_id: run_7339c7e46fec947e769ab7b7f1e68fd7
Trial 2: run_id: run_7339c7e46fec947e769ab7b7f1e68fd7
Trial 3: run_id: run_7339c7e46fec947e769ab7b7f1e68fd7
DETERMINISM: PASS -- All 3 trials produced identical outputs
```

### Test 2: Non-Deterministic Control (PASS)
```
Non-deterministic control: IDs DIFFERENT (expected: DIFFERENT)
```

### Test 3: pytest Determinism Suite (5 tests, all PASS)
- test_same_seed_same_scenario
- test_different_seeds_different_ids
- test_evidence_ids_deterministic
- test_candidate_ids_deterministic
- test_metrics_deterministic_across_runs

## Verdict: PASS
Deterministic ID generation verified. Same seed produces byte-identical outputs.
