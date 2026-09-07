# 08 STAGE 1.1 TEST REPORT

## New Tests Added

File: `tests/unit/test_stage1_1_validation.py` — 10 tests

### TestCEEResponsiveness (5 tests)

| Test | Status | What It Verifies |
|------|--------|------------------|
| test_positive_control_causal_cee_nonzero | PASS | Causal intervention: Y_f != Y_cf, CEE > 0 |
| test_negative_control_distractor_cee_zero | PASS | Distractor intervention: Y_f == Y_cf, CEE = 0 |
| test_negative_control_distractor_scenario | PASS | BF-D distractors all CEE = 0 |
| test_cee_estimator_nonzero | PASS | CEEEstimator produces CEE > 0 for causal |
| test_reproducibility_three_runs | PASS | Same seed → identical CEE across 3 runs |

### TestSharedSource (3 tests)

| Test | Status | What It Verifies |
|------|--------|------------------|
| test_shared_source_scenario_structure | PASS | BF-G has >= 2 candidates, causal + irrelevant |
| test_channel_intervention_preserves_sibling | PASS | Validator "ok" survives analyzer channel block |
| test_step_vs_channel_different_scope | PASS | Different target events and/or types |

### TestLeakageRecheck (2 tests)

| Test | Status | What It Verifies |
|------|--------|------------------|
| test_evaluator_does_not_know_intervention | PASS | Evaluator takes only ExecutionRun |
| test_evaluator_same_for_factual_and_counterfactual | PASS | Same function applied to both |

## Full Test Suite

```
677 passed in 4.16s
```

Breakdown:
- 644 original tests (pre-Stage 1)
- 23 Stage 1 integrity tests
- 10 Stage 1.1 validation tests

## Linter Results

| Tool | Status |
|------|--------|
| ruff check captain/ tests/ | PASS — 0 errors |
| ruff format --check captain/ tests/ | PASS — 0 reformats |
| mypy captain | PASS — 0 errors in 63 files |

## Acceptance Criteria G: PASS
All existing tests continue to pass.
