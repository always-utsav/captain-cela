# Frequently Asked Questions

### Is CELA proven on real agents in production environments?
No. CELA has been evaluated primarily on controlled, synthetic benchmark scenarios using a deterministic MockLLM. A limited sanity check was performed using a real LLM (Gemini 3.6-flash) to validate the core premise that LLM outputs depend on evidence content, but the full pipeline has not been validated on stochastic, open-ended real-world agents.

### Is the CEE (Counterfactual Evidence-Flow Effect) a novel causal estimand?
No. CEE is a direct operationalization of standard causal do-calculus applied specifically to the domain of agent evidence-flow channels. It measures the change in failure probability when a specific channel is modified or blocked.

### Why use a MockLLM for the primary benchmarks?
Causal analysis via counterfactual replay requires strict isolation of variables. A deterministic MockLLM guarantees that any change in the agent's behavior during replay is caused *only* by the applied intervention, avoiding the confounding noise of stochastic LLM sampling.

### Why does the benchmark suite only have 275 scenarios?
The scenarios are highly controlled and parameterized to test specific causal topologies (families BF-A through BF-K). They are designed for exhaustive coverage of information-flow mechanisms (e.g., redundant OR, converging paths, shared sources) rather than unstructured large-scale testing. 

### What is the "Negative Result C3"?
In statistical testing, the full CELA pipeline (A5) did not achieve a statistically significantly higher causal F1 score compared to a random selection baseline (B1) across the full suite (p=0.1156). We document this genuine negative result, which may indicate that our synthetic scenarios are too simple for the full pipeline to show a significant statistical gap over baseline heuristics.
