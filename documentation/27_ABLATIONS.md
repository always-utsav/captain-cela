# 27: Ablations

The ablation study isolates the contributions of distinct components within the CELA framework (A1 through A5).

## Ablation Ladder

- **A1 (CELA-provenance)**: Selects interventions based purely on provenance connectivity (equivalent to baseline B2).
- **A2 (CELA-CEE)**: Ranks interventions based on individual Counterfactual Effect Estimates (equivalent to baseline B3).
- **A3 (CELA-cascade)**: Adds cascade estimation to capture multi-hop propagation.
- **A4 (CELA-greedy)**: Employs greedy selection over the cascade estimates.
- **A5 (CELA-full)**: The complete CELA pipeline.

*Note on efficacy*: As documented in the negative results, the full pipeline (A5) did not achieve a statistically significant improvement over random selection (B1) for `causal_f1` on the current benchmark suite (p=0.1156).
