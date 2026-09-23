# 24: Statistical Methods

The statistical protocol strictly avoids standard parametric assumptions where inappropriate and relies entirely on standard library (`stdlib`) implementations. **No t-tests are performed.**

## Statistical Tests

- **Unit of analysis**: The scenario instance.
- **Paired Comparisons**: 
  - For data with ≤3 unique differences, a **Permutation Test** is used.
  - For data with >3 unique differences, a **Wilcoxon signed-rank test** is used.
- **Confidence Intervals**: Calculated using Bootstrap resampling (2000 resamples, percentile method, α=0.05).
- **Multiple Comparisons**: Corrected using the **Holm-Bonferroni** method.
- **Effect Size**: Measured using Paired **Cohen's d**.
- **Sensitivity/Stability**: Assessed via the Coefficient of Variation (**CV**), with a target of CV < 0.2 indicating stable results across random seeds.
