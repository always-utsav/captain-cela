# Novelty and Positioning

## What is Genuinely Novel
CELA's primary novelty lies in its **operationalization** of existing causal methods at a new level of granularity. While prior works (such as CAR, CausalFlow, and CHIEF) have applied counterfactual causal attribution to agent execution steps, CELA shifts the intervention target to the **provenance-defined evidence-flow channel**. 

By targeting the information payload moving between steps rather than the step itself, CELA provides evidence for improved causal selectivity, particularly in complex scenarios where single steps produce multiple disparate pieces of information (the shared-source problem).

## Foundational Reliance
CELA builds upon and does not claim to invent:
- Structural Causal Models and do-calculus (Pearl, 2009)
- Counterfactual replay mechanisms
- Provenance graph structures (W3C PROV)

## Positioning Relative to Competitors
- **Step-Level Systems (CAR, CausalFlow)**: These systems intervene on steps. CELA demonstrates that intervening on evidence channels can prevent collateral modification of benign outputs produced by those steps.
- **Graph-Based Systems (CHIEF)**: While using causal graphs, CELA adds a strict multimodal hard-provenance evidence lineage layer to define exact intervention points.

## Language and Claims
We frame our findings using safe, empirically supported language:
- CELA *operationalizes* causal analysis at the evidence-channel level.
- CELA *demonstrates* improved selectivity on specific controlled benchmarks (BF-G).
- CELA *provides evidence for* the utility of granular interventions.

We strictly avoid claims that the method "proves" generalized causality, is the "first" to perform counterfactual analysis, or is "universally" applicable to all autonomous agents.
