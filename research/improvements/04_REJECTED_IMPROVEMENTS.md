# Rejected Improvements — CAPTAIN/CELA V2

## R1: Stochastic Replay Engine

**Proposal**: Replace deterministic MockLLM replay with stochastic
LLM-based replay to capture real output variability.

**Reason for rejection**: Would fundamentally change the evaluation
paradigm. Deterministic replay provides controlled conditions where
CEE differences can be attributed to the intervention alone.
Stochastic replay introduces confounding variability that requires
much larger sample sizes. This is a separate research direction,
not a V2 improvement.

## R2: Multi-Agent Cascade

**Proposal**: Extend CAPTAIN to trace multi-agent systems.

**Reason for rejection**: CAPTAIN traces single-agent execution
with multiple tools. Multi-agent systems involve inter-agent
communication graphs that require fundamentally different
provenance models. Out of V2 scope.

## R3: External Benchmark Porting

**Proposal**: Port Who&When Pro or similar external benchmarks
into CAPTAIN's format for direct comparison.

**Reason for rejection**: External benchmarks use different
evaluation units (trajectory-level vs channel-level), different
ground truth formats (human annotation vs machine-readable spec),
and different intervention semantics. Porting would risk creating
an unfair advantage for CELA by re-encoding competitor tasks in
CELA's native format.

## R4: Shapley-Style Multi-Channel Attribution

**Proposal**: Use Shapley values to account for interaction effects
between evidence channels.

**Reason for rejection**: Requires 2^n replay combinations for n
channels, which is computationally prohibitive for real scenarios.
The current CEE provides per-channel estimates that are sufficient
for the intervention selectivity question. Shapley attribution is
documented as future work.

## R5: Automatic Scenario Discovery

**Proposal**: Automatically discover causal mechanism types from
real agent traces.

**Reason for rejection**: Requires labeled real-agent failures,
which we do not have. The controlled benchmark approach deliberately
avoids relying on real traces to ensure ground truth is available.
