# 04: Benchmark Specification

The CAPTAIN/CELA benchmark suite contains 11 families evaluating distinct causal reasoning mechanisms:

| Family | Mechanism / Structure Tested | Ground Truth Type | Objective |
|---|---|---|---|
| **BF-A** | Simple Direct Causation | Binary Failure | Verify basic detection of a single failing artifact. |
| **BF-B** | Conjunctive Causation (AND) | Joint Failure | Tests if multiple necessary conditions are identified together. |
| **BF-C** | Disjunctive Causation (OR) | Independent Failures | Tests if independent sufficient causes are properly isolated. |
| **BF-D** | Masking / Overshadowing | Hidden Failure | Tests if the system detects failures masked by other events. |
| **BF-E** | Cascading Failure (Linear) | Upstream Failure | Evaluates attribution tracing back through a chain of events. |
| **BF-F** | Spurious Correlation | Confounding | Tests robustness against falsely attributing cause to correlated but benign events. |
| **BF-G** | Granular Provenance | Channel vs Source | Evaluates if channel interventions are more selective than source-event interventions. |
| **BF-H** | Temporal Delay | Delayed Effect | Tests if causes are correctly linked to temporally distant outcomes. |
| **BF-I** | Multi-hop Conjunction | Complex Graph | Tests capability to traverse multi-step causal graphs with joint requirements. |
| **BF-J** | Circular / Feedback Loop | Cycle Resolution | Tests handling of reciprocal causal structures. |
| **BF-K** | Epistemic Uncertainty | Missing Information | Evaluates behavior when critical causal evidence is absent. |
