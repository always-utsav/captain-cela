# 02: Experiment Manifest

This document summarizes the experiment manifest detailing the scope of the evaluation campaign.

## Campaign Configuration
- **Total Families**: 11 (BF-A through BF-K)
- **Seeds Tested**: 5 (`42`, `123`, `456`, `789`, `1024`)
- **Instances per Family (per seed)**: 5
- **Methods Evaluated**: 10 total (Baselines: `B1`-`B5`, Ablations/Proposed: `A1`-`A5`)
- **Total Scenarios Evaluated**: 275 (11 families × 5 seeds × 5 instances)
- **Software Commit**: `98e6366c6e47`

The benchmark uses a controlled environment (MockLLM) to rigorously evaluate causal localization before stochastic variables are introduced in Real-LLM validation.
