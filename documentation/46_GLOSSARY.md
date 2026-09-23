# Glossary

- **CAPTAIN**: Counterfactual Analysis Platform for Trace-based Investigation of Autonomous Agent Cascades. The engineering infrastructure and reference agent platform.
- **CELA**: Counterfactual Evidence-Lineage Attribution. The research method built on CAPTAIN that performs causal attribution via evidence-channel interventions.
- **CEE**: Counterfactual Evidence-Flow Effect. The primary causal estimand: `CEE(e) = P(Y=1) - P(Y=1 | do(C_e = empty))`.
- **Evidence-Flow Channel**: An information-bearing transformation or transfer between two evidence objects (e.g., an artifact passed from a tool output to a reasoning step).
- **Source Event**: The execution event (e.g., a tool call or reasoning step) that produced an artifact or piece of evidence.
- **Intervention**: A targeted modification to an execution trace during counterfactual replay (e.g., replacing an artifact value or blocking a channel).
- **Counterfactual Replay**: Re-executing an agent trace under a specific intervention to observe if the failure outcome changes.
- **Factual Execution**: The original, un-intervened baseline execution run of the agent.
- **MockLLM**: A deterministic, scripted LLM provider used in CAPTAIN benchmarks to ensure reproducible, controlled counterfactual replays.
- **Benchmark Family (BF-A through BF-K)**: A set of controlled synthetic scenario generators representing different causal topologies (e.g., single channel, redundant OR, cascade).
- **Deterministic IDs**: A context manager used in benchmarks to generate predictable UUIDs, ensuring identical graph structures across identical runs.
- **Candidate**: An evidence-flow channel identified by screening heuristics as potentially relevant to a failure, warranting CEE estimation.
- **Propagation**: The movement of failure-causing information across multiple hops in the evidence-flow graph.
- **Cascade**: A multi-hop sequence where a failure in one piece of evidence leads to subsequent failures in downstream reasoning or actions.
