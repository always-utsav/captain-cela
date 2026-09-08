# 03: Scientific Contract

## Research Question
Does finer provenance-defined evidence-channel intervention provide more selective causal localization and less collateral modification than coarse source-event intervention?

## Causal Evidence Estimand (CEE)
We formalize the core estimand as the Expected Causal Effect of Evidence:
`CEE(e) = P(Y=1) - P(Y=1 | do(C_e = empty))`

*Note: Joint CEE for multiple pieces of evidence is computed via actual joint counterfactual replay, NOT as the sum of individual CEEs, accounting for complex non-linear combinations of evidence.*

## Terminology
- **Source-event-level intervention**: Intervention at the level of the full tool return or event (not to be conflated with "step-level").
- **Evidence-channel intervention**: Intervention on individual facts/artifacts within a source event.

## Environment Setup
- **MockLLM**: Employed as a strictly controlled simulation mechanism. It guarantees isolated analysis of specific causal structures without confounding from LLM stochasticity or unrelated reasoning failures.
