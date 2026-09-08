# Literature Comparison: CELA vs Competitor Systems

This document provides a detailed comparison of CELA against 12 state-of-the-art competitor systems in the domain of failure attribution and causal intervention for LLM agents.

## Key Finding
**NO prior work operationalizes causal intervention at the provenance-defined evidence-flow channel level.** All existing systems use step-level or coarser intervention units. CELA's channel-level intervention targets specific directed provenance edges between artifacts, enabling selective neutralization of failure-carrying evidence while preserving concurrent benign pathways.

## Comparison Matrix Breakdown

### 1. Who&When / Who&When Pro
- **Problem addressed:** MAS culprit agent and decisive step localization
- **Failure attribution method:** Prefix-replay injection
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Step/Agent level
- **Evidence-channel intervention:** No

### 2. AgenTracer
- **Problem addressed:** Tracing agent reasoning and tool failures
- **Failure attribution method:** RL-distilled model
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Step/Agent level
- **Evidence-channel intervention:** No

### 3. CAR
- **Problem addressed:** Credit assignment in LLM agents
- **Failure attribution method:** SCM do-calculus on state-action pairs, MC Shapley credit
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Step level ($S_t, A_t$)
- **Evidence-channel intervention:** No

### 4. CausalFlow
- **Problem addressed:** Causal discovery and repair in agent flows
- **Failure attribution method:** Step CRS + minimal contrastive repair
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Step level
- **Evidence-channel intervention:** No

### 5. CHIEF
- **Problem addressed:** Hierarchical failure diagnosis
- **Failure attribution method:** Hierarchical causal graph OTAR + virtual oracle backtracking
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Agent/Subtask/Step hierarchy
- **Evidence-channel intervention:** No

### 6. DoVer
- **Problem addressed:** Active debugging in LLM agents
- **Failure attribution method:** Active do-then-verify debugging
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** State/Plan/Message level
- **Evidence-channel intervention:** No

### 7. AgentRx
- **Problem addressed:** Post-hoc agent behavior auditing
- **Failure attribution method:** Constraint-based auditing
- **Counterfactual replay:** No
- **Causal intervention:** No
- **Atomic intervention unit:** Step constraint check
- **Evidence-channel intervention:** No

### 8. RAFFLES
- **Problem addressed:** Agent trajectory evaluation
- **Failure attribution method:** Multi-evaluator LLM judge debate
- **Counterfactual replay:** No
- **Causal intervention:** No
- **Atomic intervention unit:** Step/Agent level
- **Evidence-channel intervention:** No

### 9. AgentProcessBench
- **Problem addressed:** Agent process evaluation and benchmarking
- **Failure attribution method:** Ternary step annotation
- **Counterfactual replay:** No
- **Causal intervention:** No
- **Atomic intervention unit:** Step level
- **Evidence-channel intervention:** No

### 10. SAFARI
- **Problem addressed:** Active log investigation
- **Failure attribution method:** STM log inspection
- **Counterfactual replay:** No
- **Causal intervention:** No
- **Atomic intervention unit:** Step/Segment inspection
- **Evidence-channel intervention:** No

### 11. AGENTSCOPE
- **Problem addressed:** Neuro-symbolic fault localization
- **Failure attribution method:** ReAG + neural invariants
- **Counterfactual replay:** No
- **Causal intervention:** No
- **Atomic intervention unit:** Graph vertex
- **Evidence-channel intervention:** No

### 12. AgenticRAG-FP
- **Problem addressed:** Fault injection in Retrieval-Augmented Generation
- **Failure attribution method:** Certified fault injection at retrieval hops
- **Counterfactual replay:** Yes
- **Causal intervention:** Partial
- **Atomic intervention unit:** Hop/Retrieval-step level
- **Evidence-channel intervention:** No

### CELA (Proposed System)
- **Problem addressed:** Causal failure attribution via evidence-flow channel intervention
- **Failure attribution method:** Evidence-channel targeted counterfactual replay
- **Counterfactual replay:** Yes
- **Causal intervention:** Yes
- **Atomic intervention unit:** Evidence-flow channel (provenance edge)
- **Evidence-channel intervention:** Yes
