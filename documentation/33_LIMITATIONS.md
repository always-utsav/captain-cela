# 33: Limitations

The current evaluation of the CAPTAIN/CELA framework has several known limitations that contextualize the findings.

1. **MockLLM Reliance**: All benchmark experiments use a deterministic, scripted MockLLM. They do not reflect the stochasticity or reasoning failures of real LLMs.
2. **Real-LLM Scope**: The Real-LLM validation is merely a sanity check with handcrafted prompts on a single model (`gemini-3.6-flash`), not an end-to-end evaluation.
3. **Synthetic Scenarios**: The benchmark scenarios are strictly controlled synthetic environments that may lack the complexity of real-world agent trajectories.
4. **Statistical Methods**: Statistics are implemented using only the standard library (no `scipy`), necessitating non-standard implementations (though validated).
5. **Shared-Source Limitations**: The granularity (shared-source) experiments assume tool outputs can be perfectly decoupled, which is rarely true for opaque API calls.
6. **Benchmark Mismatches**: 
   - BF-H tests convergent topologies, not branching.
   - BF-J tests parallel sources, not true circular root-vs-symptom loops.
   - BF-K tests downstream persistence, not genuine repair behavior.
7. **Baseline Equivalences**: CELA variants A1 and A2 are functionally equivalent to baselines B2 and B3, respectively.
8. **Unexecuted Experiments**: Pathway stress, cascade/joint intervention, and cost/utility sweep experiments are documented in schemas but were not implemented or executed.
9. **No External Agent**: No external, third-party LLM agent framework was evaluated through the CAPTAIN pipeline.
