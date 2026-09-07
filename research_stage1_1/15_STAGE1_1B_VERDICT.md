# 15 STAGE 1.1-B VERDICT

**Date:** 2026-09-07
**Seed:** 42
**Tests:** 682 passed, 0 failed
**Linters:** ruff check PASS, ruff format PASS, mypy PASS

---

## VERDICT: PASS -- READY FOR STAGE 2

---

## What Was Changed

### captain/agent/tools.py
- Added `MULTI_OUTPUT_SEPARATOR = "|||"` module-level constant
- When a tool returns a result containing this separator, TracedAgent
  splits it into multiple artifacts from the same source event

### captain/tracing/traced_agent.py
- Extended tool result handling: if result contains `MULTI_OUTPUT_SEPARATOR`,
  splits into N artifacts, each with same `producer_event_id`, all listed
  in the TOOL_RESULT event's `output_artifact_ids`

### captain/analysis/estimator.py
- Extended `channel_to_intervention()`: for multi-artifact source events
  (`len(output_artifact_ids) > 1`), uses `ARTIFACT_REPLACEMENT` targeting
  the specific artifact ID, not the whole event

### captain/replay/engine.py
- Extended `_do_art()` to track per-artifact value changes for propagation
- Extended `TOOL_RESULT_OVERRIDE` to propagate individual parts of
  multi-output results via `MULTI_OUTPUT_SEPARATOR` splitting
- Updated `_apply()` to pass `tool_result_changes` to `_do_art`

### captain/benchmarks/scenarios.py
- Rewrote `generate_shared_source()` to use single `data_source` tool
  returning `"42|||ok"` — produces 2 artifacts from 1 event
- Channel classification now based on artifact value matching

### tests/unit/test_stage1_1_validation.py
- Added 5 new tests in `TestMultiArtifactSharedSource`:
  - test_source_event_has_multiple_artifacts
  - test_artifacts_share_producer
  - test_shared_source_channel_intervention_preserves_sibling
  - test_source_step_intervention_has_broader_scope
  - test_channel_scope_strictly_narrower

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| One source event produces multiple evidence artifacts | **PASS** (2 artifacts) |
| A and B are provenance-distinct channels | **PASS** (separate evidence nodes) |
| Channel-A intervention removes A | **PASS** ("42" absent) |
| Channel-A intervention preserves B | **PASS** ("ok" present) |
| Source-step has broader observed scope | **PASS** (2 affected vs 1) |
| Factual/counterfactual outcomes measured independently | **PASS** |
| Causal intervention has positive CEE | **PASS** (CEE=1.0) |
| Negative control remains zero | **PASS** |
| No information leakage | **PASS** |
| Deterministic/reproducible | **PASS** (3 trials) |
| All regression tests pass | **PASS** (682 tests) |

## Three-Way Results

| Condition | A | B | Failure | CEE |
|-----------|---|---|---------|-----|
| Factual | Y | Y | True | - |
| Channel A block | N | Y | False | 1.0 |
| Source-step block | N | N | False | - |

## What This Proves

1. ONE source event (`data_source` TOOL_RESULT) genuinely produces
   TWO artifacts that share the same `producer_event_id`

2. Channel-level intervention using `ARTIFACT_REPLACEMENT` targets
   only artifact_A, preserving artifact_B — empirically verified
   by inspecting actual counterfactual execution text

3. Source-step intervention using `TOOL_RESULT_OVERRIDE` blocks
   BOTH artifacts — empirically verified

4. `Scope(channel_A) < Scope(source_step)` — demonstrated by
   affected evidence counts (1 vs 2) and B preservation (yes vs no)

## STAGE 1.1-B PASS -- READY FOR STAGE 2
