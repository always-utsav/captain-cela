# 12 SEED ROBUSTNESS REPORT

## Experiment Setup
- Scenario: BF-A (single_cause)
- Seeds: 1, 2, 3, 42, 100
- Metric: CEE of first causal candidate
- Replays: 5 per candidate

## Results

| Seed | CEE | CI Lower | CI Upper | Valid Trials |
|------|-----|----------|----------|--------------|
| 1 | 0.000 | 0.000 | 0.000 | 5 |
| 2 | 0.000 | 0.000 | 0.000 | 5 |
| 3 | 0.000 | 0.000 | 0.000 | 5 |
| 42 | 0.000 | 0.000 | 0.000 | 5 |
| 100 | 0.000 | 0.000 | 0.000 | 5 |

## Summary Statistics
- Mean CEE: 0.000
- Standard deviation: 0.000
- Coefficient of variation: undefined (0/0)

## Interpretation

Results are trivially robust because CEE=0 for all seeds (MockLLM ceiling effect). Robustness testing of SELECTION METRICS (F1, recall) requires the full BenchmarkRunner flow, which is confirmed working in the benchmark smoke campaign.

## Benchmark Smoke Cross-Seed Stability

From the benchmark smoke campaign (3 seeds x 6 families x 3 methods = 54 entries):
- 0 execution errors
- F1 values are deterministic per family (same F1 for all 3 seeds within each family/method)
- This confirms the deterministic ID system is working correctly

## Verdict: PASS (trivial — no variance in CEE; selection metrics stable)
