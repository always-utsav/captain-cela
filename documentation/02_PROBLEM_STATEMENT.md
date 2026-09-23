# Problem Statement

Autonomous multimodal agents execute complex sequences of observations, reasoning, tool calls, and memory operations. When failures occur, they propagate through the agent's execution trace via information-bearing channels—not merely through sequential step adjacency.

## The Limitation of Existing Approaches
Existing failure-diagnosis methods typically attribute failures at the granularity of execution steps. This conflates the execution event (what happened) with the actual information transformation (what evidence moved or changed). Consequently, step-level attribution may identify *where* a failure manifested, but struggles to explain *how* the failure-causing information specifically propagated through the system. 

## The CELA Question
Understanding the "why" behind agent failures requires tracing evidence flow and determining which specific information pathways *caused* the failure. 

CELA asks: **Can we intervene at the evidence-channel level to achieve more selective causal localization than traditional execution-step-level interventions?**

By shifting the intervention target from the execution event to the evidence-flow channel, we hypothesize that it is possible to isolate the exact information transfer responsible for a failure, minimizing collateral modifications to otherwise benign evidence produced by the same step.
