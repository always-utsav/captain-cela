# Novelty Evidence Matrix

This matrix explicitly tests CELA's candidate distinction: **CELA operationalizes causal intervention at the provenance-defined evidence-flow channel level.**

| Prior Work | Atomic Intervention Unit | What It Can Isolate | What CELA Isolates | Empirical Experiment Testing Difference | Result |
|------------|--------------------------|---------------------|--------------------|-----------------------------------------|--------|
| Who&When / Who&When Pro | Step/Agent level | Which agent or step caused failure | Specific evidence channels (edges) causing failure | Step vs Channel intervention on branching logic | CELA isolates benign concurrent paths that step-level ablation destroys |
| CAR, CausalFlow | Step level ($S_t, A_t$) | Which individual action/state pair failed | How specific data flow from action A to action B contributed | Channel ablation on shared-source node data | CELA neutralizes failure-carrying data while preserving valid data from the same step |
| CHIEF | Agent/Subtask/Step hierarchy | Faulty hierarchical components | Directed data dependency edges | Hierarchical node ablation vs directed edge ablation | CELA identifies specific faulty interactions between components without discarding entire components |

## Legitimate Claims Validated by CELA
1. First operationalization of causal counterfactual intervention at the provenance-defined evidence-flow channel level.
2. Evidence-channel intervention enables finer causal localization than step-level in branching/shared-source architectures.
3. Joint set-level evidence-channel intervention captures multi-channel interaction effects.
4. Cost-aware greedy cascade prevention under budget constraints.

## Avoided Claims (To ensure scientific rigor)
- "First causal replay framework" (CAR, CausalFlow, DoVer predate)
- "First causal failure attribution" (CAR, CHIEF, CausalFlow already do this)
- "First multimodal failure attribution" (Who&When Pro already explores this)
- "First graph-based failure attribution" (CHIEF, AGENTSCOPE utilize graph structures)
- Claiming CEE as a fundamentally novel estimand (it is an operationalization).
