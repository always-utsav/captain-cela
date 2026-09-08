# 10: Ablation Study

An ablation study was conducted via the proposed method ladder `A1` through `A5`.

- **A1/A2**: Equivalent to basic baseline implementations.
- **A3**: Introduces basic channel-level tracking, bypassing raw event-level restrictions.
- **A4**: Adds advanced joint counterfactuals.
- **A5**: Full system implementation including dynamic re-evaluation and granular dependency tracing.

As shown in the campaign benchmark, each successive level in the ladder significantly increases the capability of isolating complex causal artifacts (particularly in families BF-C, BF-D, and BF-I), culminating in the maximum performance exhibited by `A5`.
