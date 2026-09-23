# 28: Robustness

Robustness analysis verifies that the results are not artifacts of specific initializations or instance procedural generation.

## Seed Robustness
The benchmark campaign was executed across 5 distinct random seeds (`42`, `123`, `456`, `789`, `1024`).

## Coefficient of Variation (CV) Analysis
The stability of metrics across these 5 seeds is evaluated using the Coefficient of Variation (CV). A CV threshold of `< 0.2` indicates stable results, confirming that the performance characteristics of the attribution mechanisms are robust to seed variation and do not fluctuate wildly based on initialization.
