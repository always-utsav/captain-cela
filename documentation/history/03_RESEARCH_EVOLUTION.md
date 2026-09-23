# Evolution of the Research Question

The core research question of the CAPTAIN project underwent significant refinement, transitioning from general agent observability to a highly specific, causal intervention framework.

## Initial Concept: Agent Tracing
Originally (Stages 0-8), the project was primarily an engineering effort aimed at building "CAPTAIN"—a robust multimodal agent tracing and visualization framework. The goal was simply to record what an agent did (events) and what data it produced (artifacts), and to visualize the resulting execution graph. The research questions implicitly revolved around observability and provenance tracking.

## The Causal Turn: Counterfactuals
In Stages 9-10, the introduction of the `CounterfactualReplayEngine` shifted the focus from static observability to dynamic causal analysis. The ability to re-run traces while mutating the environment opened the door to asking *why* a failure occurred, rather than just *how* the agent reached that failure.

## The CELA Research Lock (Stage 11)
Stage 11 formally codified the shift. The project locked its research identity as CELA (Counterfactual Evidence-Lineage Attribution). 
The core realization was that traditional debugging looks at *steps* (e.g., "The web search tool failed"). However, for LLM agents, failure often stems from the *information* (evidence) flowing between steps.

**The shift from Source-Event to Evidence-Channel:**
- **Source-Event Intervention**: Blocking or overriding the event that generated bad data (e.g., disabling the tool). This is coarse and often destroys unrelated valid data produced by the same event.
- **Evidence-Channel Intervention**: Intervening on the specific piece of evidence (artifact) flowing into a subsequent step, preserving the rest of the source event's outputs.

## Final Formulated Research Question
This evolution culminated in the final research question established for scientific closure (Sept 22):

> *Can causal attribution in autonomous AI-agent failure analysis be made more selective by intervening at the evidence-flow channel level rather than at the source-event level?*

This explicitly targets the granularity of intervention, comparing the precision of `ARTIFACT_REPLACEMENT` against `TOOL_RESULT_OVERRIDE`. It deliberately scopes down from "proving causality universally" to evaluating a specific, structural intervention technique in controlled environments.
