# Future Work

While CAPTAIN/CELA establishes the foundation for evidence-channel interventions, several areas remain open for future development:

## 1. Genuine Step-Level Baselines
Implement comprehensive step-level causal baselines (like CAR or CausalFlow) directly into the benchmark suite to allow empirical side-by-side comparisons on metric efficacy beyond granularity counts.

## 2. Stochastic Replay Handling
The current benchmark relies on a deterministic `MockLLM`. Future iterations must implement robust statistical estimators capable of handling highly stochastic agent behaviors, potentially through Monte-Carlo sampling or LLM-as-a-judge alignment.

## 3. Real Agent Integration
Extend the pipeline beyond the sanity check phase. Integrate a live, multi-hop agent (e.g., ReAct, Plan-and-Solve) completely within the `EvidenceFlowGraph` tracing framework and run full causal attribution scenarios using real LLM calls.

## 4. Larger and More Complex Benchmarks
The current 11 families focus on isolated logical primitives. Future benchmarks should include multi-domain, long-horizon tasks (similar to SAFARI or WebArena) to test the CELA pipeline's scalability and search efficiency.

## 5. Multi-Model Validation
The real-LLM sanity check was limited to a single model (`gemini-3.6-flash`). Future work should evaluate intervention effects and CEE stability across diverse architectures (e.g., GPT-4o, Claude 3.5 Sonnet, Llama 3) to ensure generalization.
