# Mathematical Formulation

## Formal Definitions
- **Execution Trace** $T = (E, A, R)$: Set of events $E$, artifacts $A$, and relationships $R$.
- **Evidence-flow Graph** $G = (V, F)$: Vertices $V$ (evidence objects) and flow edges $F$ (channels).
- **Channel** $C_e$: A specific evidence pathway mapping source evidence to target evidence.
- **Intervention** $do(C_e = \emptyset)$: An action blocking the information flow along channel $C_e$.

## Estimands
- **CEE (Counterfactual Evidence-Flow Effect)**: 
  $CEE(e) = P(Y=1) - P(Y=1 | do(C_e = \emptyset))$
  Note: CEE is an operationalization of standard intervention effect, NOT a novel causal estimand.

- **Set-Level CEE**: 
  $CEE(S) = P(Y=1) - P(Y=1 | do(C_S))$
  This requires joint paired replay and is not the sum of individual CEEs.

- **Propagation Profile**: 
  For lineage $L = (e_1, ..., e_k)$: $\Pi(L) = [CEE(e_1), ..., CEE(e_k)]$

- **Utility Model**: 
  $U(S) = CEE(S) - \lambda \cdot Cost(S)$

## Confidence Intervals
Bootstrap confidence intervals (percentile method) are employed due to binary empirical outcomes over $N$ paired trials.
