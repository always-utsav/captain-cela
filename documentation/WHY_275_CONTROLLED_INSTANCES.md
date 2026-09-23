# Why 275 Controlled Instances?

A common question regarding the CAPTAIN/CELA evaluation is the relatively small scale of the dataset: **275 instances** (11 families × 5 seeds × 5 instances).

## Controlled Causal Mechanism Coverage vs. Large-Scale Trajectory Coverage

The CAPTAIN/CELA benchmark suite is designed for **controlled causal mechanism coverage** rather than **large-scale trajectory coverage**. 

### The Purpose of Controlled Instances
The 275 instances are rigorously constructed unit tests for causal attribution. Each instance guarantees a specific, unambiguous ground-truth causal topology (e.g., OR-logic, AND-logic, Cascade, Distractors). This allows us to mathematically verify if an attribution algorithm can isolate a specific structural confounder.

### Why not thousands of instances?
In large-scale benchmarks (e.g., running an agent on 10,000 real-world web-browsing tasks), the exact causal mechanism of a failure is often ambiguous, subjective, and entangled with stochastic model errors. Evaluating an attribution algorithm on such datasets makes it impossible to distinguish between:
1. The attribution algorithm failing to find the cause.
2. The evaluator disagreeing with the algorithm on what the "true" cause is.
3. The LLM acting non-deterministically during counterfactual replay.

### Conclusion
Neither approach is universally better. Large-scale trajectory datasets measure real-world applicability and system robustness, whereas our 275 controlled instances measure the precise algorithmic correctness of the causal reasoning framework. For evaluating a novel causal attribution mechanism like CELA, strict topological control is a prerequisite.
