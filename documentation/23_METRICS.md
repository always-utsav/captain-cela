# 23: Metrics

The evaluation employs several metrics to capture different dimensions of causal attribution performance.

## Core Attribution Metrics

- **causal_precision**: The proportion of selected interventions that are part of the true causal set.
- **causal_recall**: The proportion of the true causal set that is selected for intervention.
- **causal_f1**: The harmonic mean of causal precision and causal recall.
- **recall_at_1**: Whether the top-ranked intervention is part of the true causal set.

## Functional Metrics

- **failure_prevention_rate**: The rate at which the selected intervention set successfully prevents the failure from occurring in counterfactual replay.
- **prevention_set_recall**: The ability of the method to identify the full prevention set required to stop the failure (critical for multi-cause scenarios).
- **cee_set**: The set-level Counterfactual Effect Estimate (CEE).

## Granularity Metrics (Channel vs. Source-Event)

- **preserved_evidence**: The count of benign evidence artifacts correctly preserved during an intervention.
- **collateral**: The rate or count of non-causal (collateral) modifications introduced by an intervention.
- **affected_evidence**: The total amount of evidence altered by the intervention.
