# 17: Limitations

In the interest of rigorous scientific integrity, we explicitly acknowledge the following limitations of this work:

1. **Deterministic Environment**: The primary benchmark uses a MockLLM that is deterministic. Consequently, CEE is strictly binary (0 or 1), failing to model the subtle probability shifts in stochastic models.
2. **Synthetic Data Formats**: Delimiter-based multi-output parsing was utilized, which is highly synthetic and not a realistic surrogate for true multimodal outputs.
3. **Imperfect Comparators**: The baseline comparator is a source-event-level intervention, which is not genuinely matched to a true step-level intervention architecture.
4. **Limited Generalization**: The real-LLM validation was conducted with exactly one model (`gemini-3.6-flash`). This is NOT a claim of universal generalization across all LLMs.
5. **No External Benchmarks**: External standard benchmarks (AgentBench, SWE-bench, etc.) were deferred and not evaluated.
6. **Not a Novel Estimand**: Causal Evidence Estimand (CEE) is an application of standard causal concepts, NOT a fundamentally novel mathematical estimand.
7. **Simulation Environment**: All evaluations are controlled simulations, not tests in live production deployments.
