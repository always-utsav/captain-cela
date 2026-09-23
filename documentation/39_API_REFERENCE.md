# API Reference

This document highlights the key classes in the CAPTAIN/CELA framework.

## Core Classes

### `CEEEstimator`
Calculates the Causal Evidence Effect (CEE) by performing deterministic paired replays with specific evidence-channel interventions.

### `CascadeEstimator`
Extends CEE estimation to analyze error cascades across multiple hops in the evidence graph.

### `ExperimentRunner`
Orchestrates the execution of multiple `BenchmarkScenario` instances across different seeds and configurations.

### `BenchmarkScenario`
Defines a reproducible environment, including the virtual toolset, initial state, and failure conditions based on the benchmark family (e.g., redundant OR, cascade).

### `EvidenceFlowGraph`
A structural representation of data provenance. Nodes represent artifacts or states; edges represent tool operations or transformations.

### `FailureAnalyzer`
The top-level interface for identifying the root cause of a failure. Integrates different estimators.

### `CounterfactualReplayEngine`
Handles the deterministic re-execution of a scenario from a modified state or artifact, enabling the computation of counterfactual metrics.
