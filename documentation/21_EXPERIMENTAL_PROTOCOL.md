# 21: Experimental Protocol

The experimental protocol for the CAPTAIN/CELA evaluation is strictly controlled to ensure reproducibility and fair comparison across baseline methods.

## Campaign Configuration

- **Seeds**: 5 distinct random seeds (42, 123, 456, 789, 1024) to ensure robustness against initialization and procedural variance.
- **Instances**: 5 instances generated per benchmark family per seed.
- **Methods**: 10 total methods evaluated (5 baselines B1-B5, 5 CELA variants A1-A5).
- **Evaluator**: A deterministic evaluator is used across all families to determine task failure or success based on the specific benchmark logic (e.g., keyword presence).

## Evaluation Parameters

- **Replay Budget**: Evaluated methods operate within a strict replay budget for counterfactual testing.
- **Bootstrap Protocol**: Confidence intervals are calculated using bootstrap resampling with 2000 resamples and the percentile method (α=0.05).
- **Comparison**: Methods are compared on paired scenario instances to control for instance-level difficulty. Paired statistical tests are employed to determine the significance of performance differences.
