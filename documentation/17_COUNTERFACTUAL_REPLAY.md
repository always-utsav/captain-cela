# Counterfactual Replay

The `CounterfactualReplayEngine` performs full paired re-execution.

1. **Extraction**: Baseline LLM responses, plan structure, and tool results are extracted.
2. **Application**: The `MockLLMProvider` is modified via string substitution. Specifically, when tool outputs change, downstream LLM responses reflecting those outputs are automatically substituted to maintain propagation consistency without external API calls.
3. **Execution**: A fresh `TracedAgent` executes deterministically. 
4. **Linkage**: The new counterfactual `ExecutionRun` is linked to its baseline via `parent_run_id`.

See [engine.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/replay/engine.py).
