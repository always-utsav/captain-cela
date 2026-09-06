# FULL CODE SCIENCE AUDIT

**Project:** CAPTAIN/CELA
**Date:** 2026-09-04
**Baseline:** Stage 18 COMPLETE, 644 tests passing
**Auditor:** Automated scientific audit (Phases 1-3)

---

## 1. SUMMARY VERDICT

The CELA implementation is **scientifically sound**. No CRITICAL or HIGH
issues were found in the core mathematical framework, information isolation,
or statistical methodology.

---

## 2. CEE ESTIMATION — `captain/analysis/estimator.py`

### Verified Correct

- CEE(e) = (1/N) * SUM [Y_r - Y_cf,r,e] — **correctly implemented**
- Paired trial logic correctly pairs factual/counterfactual outcomes
- CI computation uses bootstrap percentile — correct
- Bottleneck analysis operates on propagation profiles — correct

### Issues: NONE CRITICAL/HIGH

---

## 3. CASCADE ESTIMATION — `captain/analysis/cascade.py`

### Verified Correct

- **Joint intervention** used for set-level CEE(S) — does NOT sum individual CEEs
- Greedy marginal gain: D(e|S) = CEE(S ∪ {e}) - CEE(S) — correct
- Utility: U(S) = CEE(S) - λ*Cost(S) — correct
- Budget constraints properly enforced

### Issues

| Severity | Description |
|----------|-------------|
| MEDIUM | **Redundant replay in cascade selection**: After finding `best_candidate` with `cee_with`, the algorithm adds it to `selected` then re-calls `estimate_set(selected)` to check prevention. This wastes one evaluation budget per greedy step by re-evaluating an identical set. |

**Impact:** Computational waste only. Does not affect scientific correctness.

---

## 4. BENCHMARK SCENARIOS — `captain/benchmarks/scenarios.py`

### Verified Correct

- Ground truth (ScenarioGroundTruth) is NEVER passed to methods
- Scenario generation uses deterministic seeds for structural properties
- Evaluator logic uses keyword matching on execution output (independent of method identity)
- Causal mechanism isolation is maintained

### Issues: NONE CRITICAL/HIGH

### Known Limitation (documented)

- Evaluator uses simple keyword matching rather than semantic evaluation
- This is appropriate for controlled synthetic benchmarks but insufficient alone
  for publication-grade external validity claims

---

## 5. BENCHMARK RUNNER — `captain/benchmarks/runner.py`

### Verified Correct

- All methods receive equivalent information (information parity)
- Oracle is isolated — only used for post-hoc evaluation
- Metric computation is correct
- Baseline fairness maintained

### Issues

| Severity | Description |
|----------|-------------|
| MEDIUM | **Hardcoded method names in ablation**: `_compute_ablation` searches for names like `"A1_cela"`, `"A2_cela"`. If `CELAMethod(level=x).name` doesn't exactly match, ablation steps silently return empty. |

---

## 6. FAILURE ANALYSIS — `captain/failures/analyzer.py`

### Verified Correct

- Candidate generation based on evidence-flow graph traversal
- Intervention mapping from candidate channels
- Screening score is structural (not causal) — correctly documented

### Issues: NONE

---

## 7. FAILURE MODEL — `captain/failures/model.py`

### Verified Correct

- Candidate, ChannelIntervention, Failure model fields are clean
- No information leakage through model fields

### Issues: NONE

---

## 8. EVIDENCE LINEAGE — `captain/evidence/lineage.py`

### Verified Correct

- Evidence construction from execution events
- Lineage direction follows temporal ordering
- Transformation types properly categorized

### Issues: NONE

---

## 9. EVIDENCE GRAPH — `captain/evidence/graph.py`

### Verified Correct

- Graph construction from evidence + transformations
- Upstream/downstream traversal correct
- No direction reversal bugs

### Issues: NONE

---

## 10. COUNTERFACTUAL REPLAY — `captain/replay/engine.py`

### Verified Correct

- Intervention application modifies specified channels
- Fresh IDs generated for counterfactual runs
- Factual/counterfactual pairing maintained

### Issues

| Severity | Description |
|----------|-------------|
| LOW | **Hardcoded agent payload offsets**: `_apply` modifies `llm[1 + ri]` for REASONING and `llm[-1]` for OUTPUT. Valid for locked reference agent but brittle if agent structure changes. |

---

## 11. EXPERIMENT RUNNER — `captain/experiments/runner.py`

### Verified Correct

- Experiment orchestration with deterministic seeding
- Bootstrap CI computation correct
- Paired tests correctly implemented

### Issues

See item in Section 5 (hardcoded ablation names).

---

## 12. STATISTICS — `captain/experiments/statistics.py`

### Verified Correct

- Bootstrap percentile CI — correct
- Wilcoxon signed-rank — correct implementation
- Permutation tests — correct
- Holm-Bonferroni correction — correct
- Paired Cohen's d — correct

### Issues

| Severity | Description |
|----------|-------------|
| LOW | **Wilcoxon tie correction**: Variance uses `n*(n+1)*(2n+1)/24` without tie correction term `- Σ t(t²-1)/48`. Acceptable for standard usage but slightly imprecise for tied discrete scores. |

---

## 13. INFORMATION LEAKAGE AUDIT

### Verified: NO LEAKAGE FOUND

1. Methods never receive `ScenarioGroundTruth`
2. Methods never receive oracle prevention sets
3. Evaluator does not inspect method identity
4. Evaluator uses independent output evaluation (keyword matching)
5. No future execution information available to methods
6. Hidden failure labels not accessible to methods

### Remaining Risk

- Methods receive the same `BenchmarkScenario` object, which contains
  `ground_truth` field. The field is structurally present but the runner
  code does NOT pass it to methods. Automated leakage tests should verify
  this invariant.

---

## 14. MATHEMATICAL AUDIT SUMMARY

| Formula | Implemented | Status |
|---------|-------------|--------|
| CEE(e) = (1/N) * Σ [Y_r - Y_cf,r,e] | ✅ | CORRECT |
| CEE(S) via joint intervention | ✅ | CORRECT (not summing) |
| D(e\|S) = CEE(S∪{e}) - CEE(S) | ✅ | CORRECT |
| U(S) = CEE(S) - λ*Cost(S) | ✅ | CORRECT |
| S* = argmin Cost(S) s.t. P(Y=1\|do(S)) ≤ ε | ✅ | GREEDY APPROX (documented) |
| Bootstrap percentile CI | ✅ | CORRECT |
| Holm-Bonferroni | ✅ | CORRECT |
| Paired Cohen's d | ✅ | CORRECT |

### CEE(A+B) ≠ CEE(A) + CEE(B) verification

The cascade estimator uses `estimate_set()` which performs a single joint
counterfactual replay with ALL channels in the set intervened simultaneously.
This correctly captures interaction effects and does NOT assume additivity.

**VERIFIED CORRECT.**

---

## 15. INTERVENTION FIDELITY (Preliminary)

The counterfactual replay engine modifies the target channel's evidence
while maintaining other channels. However:

- Off-target modification rate has NOT been empirically measured
- Downstream propagation verification has NOT been systematically tested
- Shared-source channel isolation is a known limitation

**Requires dedicated testing in Phase 4.**

---

## 16. ISSUE SUMMARY

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | Redundant cascade replay; hardcoded ablation names |
| LOW | 2 | Wilcoxon tie correction; hardcoded replay offsets |
| COSMETIC | 0 | — |

**No changes to core methodology required.**

---

## 17. DETERMINISM AUDIT (Preliminary)

Known nondeterminism sources:

1. `uuid.uuid4()` in scenario generation — affects evidence IDs
2. Dictionary ordering — Python 3.7+ guarantees insertion order
3. Timestamp values — metadata only, not result-affecting

**uuid.uuid4() is the primary scientific concern.**
Structural properties (family, candidate count, ground-truth structure)
are deterministic, but exact metric values (Recall@1) vary across runs.

**Requires systematic fix in Phase 5.**
