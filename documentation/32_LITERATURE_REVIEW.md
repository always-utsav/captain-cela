# Literature Review

This literature review contextualizes CAPTAIN/CELA within the broader landscape of AI failure analysis, causal inference, and provenance tracking.

## Foundational Causal Inference
Foundational work in causal inference, particularly Pearl's do-calculus and structural causal models, forms the theoretical basis for counterfactual reasoning. Traditional methods evaluate causal effects by intervening on specific variables and observing the outcomes. CELA adapts these principles to the domain of autonomous agents by formally defining interventions at the evidence-flow channel level.

## Provenance
Data provenance tracks the origins and history of data artifacts. In database systems and scientific workflows, provenance graphs capture dependencies. CELA integrates these concepts to form an `EvidenceFlowGraph`, ensuring that causal interventions are structurally grounded in the actual data flow rather than temporal correlations.

## Agent Tracing
Recent advances in agent tracing (e.g., LangSmith, AgentOps) focus on logging execution trajectories, prompts, and tool uses. While highly detailed, these logs often remain observational. CELA builds upon standard agent tracing by turning passive logs into active structural graphs that can be manipulated during replay.

## Failure Attribution
Identifying why an agent failed is a critical challenge. Works like Who&When Pro, AgentRx, and RAFFLES have explored identifying failure steps or anomalous actions using heuristics, human annotations, or LLM-as-a-judge. However, these methods often struggle to differentiate root causes from downstream symptoms without interventional evidence.

## Counterfactual Debugging
Counterfactual debugging actively alters execution to isolate faults. Systems like CAR (Causal Agent Replay) and CausalFlow introduce step-level interventions to compute causal responsibility. CELA differentiates itself by refining the intervention unit to the evidence channel, allowing for more precise, surgical modifications that reduce collateral changes.

## Benchmarking
Evaluating attribution methods requires rigorous benchmarks. Existing benchmarks (e.g., AgentProcessBench) provide extensive datasets for step-level evaluation. CELA introduces a synthetic, controlled benchmark suite (11 families) designed specifically to isolate and test causal mechanisms like redundant paths, cascades, and distractors, establishing a verifiable ground truth for causal attribution.
