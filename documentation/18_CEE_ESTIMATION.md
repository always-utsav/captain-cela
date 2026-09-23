# CEE Estimation

The `CEEEstimator` measures causal effects using deterministic paired replays.

- **Process**: Executes the factual scenario, constructs a counterfactual by intervening on a `ChannelIntervention`, and executes the counterfactual scenario.
- **Comparison**: Evaluates $Y$ and $Y_{cf}$ using a provided `FailureEvaluator`.
- **Confidence Intervals**: Employs paired bootstrap sampling over $N$ paired trials to compute robust confidence intervals.
- **Limitations**: Relies on deterministic mock LLM behavior and simulator-level propagation, restricting variance to explicitly modeled environmental factors.

See [estimator.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/analysis/estimator.py).
