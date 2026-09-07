# 10 STAGE 1.1 VERDICT

**Date:** 2026-09-07
**Seed:** 42
**Tests:** 677 passed, 0 failed
**Linters:** ruff check PASS, ruff format PASS, mypy PASS

---

## VERDICT: PASS — READY FOR STAGE 2

---

## 1. What Was Changed

### captain/agent/tools.py
- Added `FixedValueTool` class — returns pre-configured value for benchmarks

### captain/replay/engine.py
- Added `_propagate_tool_overrides()` function
- Modified `_apply()` to track tool result changes and propagate to LLM responses

### captain/benchmarks/scenarios.py
- All 6 generators (BF-A through BF-F) updated to use FixedValueTool
- Added `generate_shared_source()` (BF-G) for multi-channel validation
- Added BF-G to `all_scenarios()`

### tests/unit/test_stage1_1_validation.py
- 10 new tests covering all acceptance criteria

## 2. Why Each Change Was Necessary

| Change | Reason |
|--------|--------|
| FixedValueTool | Tool results must match LLM responses to establish causal chain |
| Causal propagation | MockLLM ignores input; propagation simulates responsive LLM |
| BF-G scenario | Need multi-channel structure to distinguish step vs channel |

## 3. How CEE Becomes Responsive

**Before:** tool result changes but LLM output is hardcoded → evaluator
finds keyword → CEE = 0.

**After:** tool result changes → propagated to LLM reasoning/output →
evaluator finds no keyword → CEE = 1.0 for causal interventions.

## 4. How Negative Controls Remain Zero

Blocking distractor tool results (echo, validator, timestamp) removes
non-keyword text from LLM responses. The failure keyword "42" remains
because it came from a different tool (calculator/analyzer). Evaluator
still finds keyword → CEE = 0.

## 5. How Shared-Source Channels Are Represented

BF-G: `data_source` → `analyzer` (channel A) + `validator` (channel B).
Each tool is a separate event in the trace with its own evidence in the
flow graph. The evidence lineage builder creates distinct transformations
for each tool's output.

## 6. How Channel Differs From Step Intervention

| Aspect | Channel-Level | Step-Level |
|--------|--------------|------------|
| Target | Source tool_result event | Mediating event |
| Type | TOOL_RESULT_OVERRIDE | EVENT_OUTPUT_OVERRIDE |
| Scope | Single channel | All channels through event |
| targets_differ | **true** | — |

## 7. Leakage Audit Result: PASS

Evaluator source code does not reference: intervention_id, ground_truth,
is_counterfactual. Propagation function uses only original/replacement
text pairs.

## 8. Reproducibility Result: PASS

3 trials with seed=42: CEE = [1.0, 1.0, 1.0] — identical.

## 9. Full Test Result

```
677 passed in 4.16s
```

- 0 existing tests broken
- 10 new Stage 1.1 tests added
- ruff, mypy clean

## 10. Remaining Limitations

| Limitation | Impact | Stage 2 Mitigation |
|-----------|--------|-------------------|
| String substitution propagation | May fail if tool result appears in unrelated text | Use unique failure keywords per scenario |
| MockLLM still ignores prompt | Propagation works around this, not fixes it | Real LLM integration in Stage 2 |
| BF-G channel isolation is via separate tools | True shared-source would be one tool → multiple artifacts | Multi-output tool in Stage 2 |
| CEE is binary (0 or 1) | No continuous effect measurement | Stochastic replays in Stage 2 |

## 11. Final Verdict

### PASS — READY FOR STAGE 2

All 7 acceptance criteria satisfied:

| Criterion | Status |
|-----------|--------|
| A. CEE responsiveness (CEE > 0 for causal) | **PASS** |
| B. Negative control (CEE = 0 for distractor) | **PASS** |
| C. No leakage | **PASS** |
| D. Channel isolation | **PASS** |
| E. Step-channel distinction | **PASS** |
| F. Reproducibility | **PASS** |
| G. Regression safety | **PASS** |

## Repository State

- GitHub: https://github.com/always-utsav/captain-cela.git (PRIVATE)
- Branch: master
- Tests: 677 passed
- Linters: clean
