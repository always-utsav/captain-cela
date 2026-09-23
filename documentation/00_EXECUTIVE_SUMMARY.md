# Executive Summary

CAPTAIN (Counterfactual Analysis Platform for Trace-based Investigation of Autonomous Agent Cascades) is a research platform designed to study how failures propagate through autonomous multimodal AI-agent executions. 

The research method developed on CAPTAIN is CELA (Counterfactual Evidence-Lineage Attribution). CELA operationalizes causal analysis by intervening at the evidence-flow channel level, rather than treating the execution step or source event as the primary intervention unit. This provides a more selective causal localization of failure-propagation bottlenecks.

## Key Findings
- **Experimental Scale**: Evaluated across 682 tests and 275 controlled benchmark scenarios.
- **Mechanism Coverage**: Tested 11 mechanism families (BF-A to BF-K) representing various information topologies (e.g., single channel, redundant OR, cascade, shared source).
- **Intervention Granularity**: Empirical demonstration on the BF-G (shared source) benchmark shows that channel-level intervention (via artifact replacement) provides more selective causal localization than source-event-level intervention, preserving more unrelated evidence and reducing collateral modification.
- **Real-LLM Sanity Check**: A controlled sanity validation using Gemini 3.6-flash confirms that a real LLM's output genuinely depends on the content of its evidence, supporting the premise of the CELA intervention mechanism.

## Notable Limitations and Negative Results
- **Negative Result (C3)**: The full CELA pipeline (A5) did not achieve statistically significantly higher causal F1 scores compared to a random baseline (B1) across the full suite of simple synthetic benchmarks (p=0.1156).
- **Scope**: Validation is performed primarily on synthetic, deterministic controlled scenarios using a MockLLM. 
- **Estimand Novelty**: The primary causal estimand, Counterfactual Evidence-Flow Effect (CEE), is an operationalization of standard causal intervention (do-calculus) applied to evidence channels, not a fundamentally novel causal estimand.
