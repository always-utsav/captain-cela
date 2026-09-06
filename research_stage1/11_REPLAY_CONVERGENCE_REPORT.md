# 11 REPLAY CONVERGENCE REPORT

## Experiment Setup
- Scenario: BF-A (single_cause), seed=42
- Candidate: First causal candidate
- Replay counts: N = 1, 3, 5, 10, 25
- CEE estimator: CEEEstimator with bootstrap CI

## Results

| N (replays) | CEE | CI Lower | CI Upper | CI Width | Valid Trials |
|-------------|-----|----------|----------|----------|--------------|
| 1 | 0.000 | 0.000 | 0.000 | 0.000 | 1 |
| 3 | 0.000 | 0.000 | 0.000 | 0.000 | 3 |
| 5 | 0.000 | 0.000 | 0.000 | 0.000 | 5 |
| 10 | 0.000 | 0.000 | 0.000 | 0.000 | 10 |
| 25 | 0.000 | 0.000 | 0.000 | 0.000 | 25 |

## Interpretation

**CEE = 0 at all replay counts** because the MockLLMProvider replays pre-scripted responses. The failure keyword "42" appears in the LLM reasoning and output regardless of whether the calculator tool result is overridden. Therefore intervention does not change the outcome.

This is NOT a convergence failure — it is a ceiling/floor effect. The intervention IS applied correctly (verified by fidelity tests), but the downstream LLM response is invariant to its input.

## Scientific Implication

The convergence experiment demonstrates:
1. The replay engine is deterministic (0 variance across replays)
2. All replays produce identical outcomes (MockLLM determinism)
3. CI width = 0 trivially (no variance)

**Meaningful convergence testing requires a reactive LLM** (or stochastic MockLLM with temperature > 0). This is a Stage 2 task.

## Verdict: PASS (trivially — no variance)
Replay engine works correctly. Convergence analysis deferred to Stage 2 with stochastic replays.
