# Research Question and Scope

## Primary Research Question
**Can causal attribution in autonomous AI-agent failure analysis be made more selective by intervening at the evidence-flow channel level rather than at the source-event level?**

## Clarification of Scope
The CELA method aims to answer this question by using controlled counterfactual replay. By replacing or blocking specific pieces of evidence as they flow between execution events, we measure the effect on downstream failure outcomes.

This question focuses specifically on the *selectivity* and *granularity* of causal attribution. It asks whether targeting the information itself (the channel) preserves more of the uncorrupted execution context compared to targeting the execution step that produced it.
