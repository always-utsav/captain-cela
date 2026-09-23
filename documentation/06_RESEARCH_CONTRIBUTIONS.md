# Research Contributions

The CAPTAIN/CELA project provides the following specific, defensible research contributions:

1. **Evidence-Flow Channel as an Intervention Unit**: Operationalizes causal interventions at the granularity of provenance-defined evidence channels, rather than treating execution steps as the sole intervention target.
2. **Shared-Source Multi-Artifact Evidence Isolation**: Demonstrates the ability to isolate failure-causing information even when multiple distinct artifacts are produced by a single source event.
3. **Controlled Benchmark Suite**: Provides a deterministically reproducible suite of benchmark families (BF-A through BF-K) representing various information topologies with machine-readable ground truth for attribution evaluation.
4. **Empirical Selectivity Advantage**: Provides empirical demonstration in controlled synthetic settings (BF-G) that channel-level interventions yield higher selectivity and lower collateral modification than source-event-level interventions.

## Explicit Non-Claims
To maintain scientific honesty, we explicitly note what this research does **NOT** claim:
- We do not claim CELA is "universally superior" to all existing attribution methods across all possible agent architectures.
- We do not claim to have invented counterfactual replay, causal graphs, or causal intervention (these rely on established literature like Pearl's do-calculus).
- We do not claim the full CELA pipeline is definitively proven on arbitrary, real-world stochastic LLM agents (evaluations primarily utilized controlled, deterministic MockLLMs).
