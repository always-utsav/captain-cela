# COMPETITOR EVIDENCE

**Project:** CAPTAIN/CELA
**Date:** 2026-09-04
**Search scope:** Published/preprinted through September 2026

---

## 1. Who&When / Who&When Pro

**Type:** Benchmark dataset (NOT a diagnostic method)
**Scale:** 12,326 failure traces, 26 source benchmarks, 15 agent frameworks
**Modalities:** Text, image, video (multimodal)
**Problem:** Identifying WHICH agent (Who) and WHICH step (When) caused failure
**Ground truth:** Controlled pipeline replaying successful prefix + injecting realistic failure
**Comparison to CELA:** Who&When is an evaluation benchmark. CELA would be evaluated ON it.
**Direct reproduction feasible:** YES (benchmark is published)
**Implication:** CELA should be benchmarked against Who&When for external validity.

---

## 2. A2P (Agent Action Path Planning)

**Finding:** NOT a failure attribution system. Generally refers to Application-to-Person messaging.
**Related work:** CausalPlan integrates SCMs into trajectory planning (proactive, not diagnostic).
**Comparison to CELA:** Not directly comparable. Different problem domain.
**Direct reproduction feasible:** N/A

---

## 3. AgentRx (Microsoft Research)

**Type:** Automated diagnostic framework
**Mechanism:** Synthesizes guarded executable constraints from tool schemas/policies. Evaluates trajectories step-by-step against constraints.
**Intervention unit:** Step-level constraint checking
**Failure definition:** Identifies "critical failure step" (earliest unrecoverable failure point). LLM-based judge with grounded taxonomy.
**Causal mechanism:** Constraint-based, NOT counterfactual re-execution
**Benchmark:** >100 manually annotated failed trajectories
**Comparison to CELA:** AgentRx is constraint/log-driven. CELA uses counterfactual replay and evidence-flow channels for deeper causal tracing.
**What CELA does differently:** Provenance-based channel-level intervention vs. schema constraint checking
**What CELA might do worse:** AgentRx is more practical for deployment (no replay needed)
**Direct reproduction feasible:** Code available

---

## 4. CHIEF (Causal HIErarchical Failure attribution)

**Type:** Root-cause identification framework for MAS
**Mechanism:** Transforms flat logs into hierarchical causal graph of task/information flows. Uses "virtual oracles" for hierarchical backtracking. Progressive causal screening strategy for counterfactual attribution.
**Causal object:** Hierarchical information flow graph
**Intervention unit:** Agent/task level in hierarchy
**CRITICAL OVERLAP:** CHIEF's "information flow" causal graph is HIGHLY ANALOGOUS to CELA's evidence-flow channels
**Comparison to CELA:** Both map information flows for counterfactual screening. CELA must differentiate by emphasizing provenance-LINEAGE granularity (below agent/task level, at specific data/evidence level).
**What CELA does differently:** Sub-agent evidence-level granularity vs. agent/task-level hierarchy
**What CELA might do worse:** CHIEF may scale better to multi-agent systems
**Direct reproduction feasible:** LIKELY (recent literature)

---

## 5. DoVer (Do-then-Verify)

**Type:** Intervention-driven automated debugging for MAS
**Mechanism:** Generates failure hypotheses and actively verifies them by performing real interventions (editing messages, altering plans, modifying code) to see if outcome flips.
**Intervention unit:** State/plan level (active intervention)
**Causal mechanism:** Hypothesis-driven active debugging via real intervention
**Comparison to CELA:** DoVer tests multiple hypotheses via active state/plan interventions. CELA's approach is more structural (provenance-graph-guided). DoVer may be costlier (trial-and-error).
**What CELA does differently:** Structural provenance guidance vs. hypothesis-driven trial-and-error
**Direct reproduction feasible:** LIKELY

---

## 6. CausalFlow

**Type:** Causal attribution and counterfactual repair framework
**Mechanism:** Calculates Causal Responsibility Scores (CRS) using step-level counterfactual interventions
**Intervention unit:** STEP-LEVEL
**Estimand:** CRS = step-level counterfactual effect
**Repair:** Generates minimally edited repairs for failure-inducing step. Generates contrastive pairs for offline preference optimization.
**CRITICAL FOR CELA:** CausalFlow intervenes at STEP level. CELA at CHANNEL level. This is exactly the comparison needed for CELA's core novelty claim.
**What CELA does differently:** Channel-level vs. step-level intervention granularity
**What CELA might do worse:** CausalFlow may be simpler and more directly applicable
**Direct reproduction feasible:** LIKELY

---

## 7. Causal Agent Replay (CAR)

**Type:** Diagnostic framework using counterfactual attribution
**Mechanism:** Models agent's run as SCM. Applies do(·) intervention to specific step. Re-executes forward trajectory using same stochastic policy.
**Intervention unit:** STEP-LEVEL (state-action trace)
**Estimand:** "Causal Locus" — shift in outcome distributions
**Statistical method:** Budget-bounded Monte-Carlo Shapley estimator for multi-step credit splitting
**MOST DIRECT METHODOLOGICAL COMPETITOR:** CAR uses stochastic re-execution and counterfactuals, like CELA. But CAR operates on state-action trace (step-level).
**What CELA does differently:** Evidence-PROVENANCE graph vs. state-action trace. Channel-level vs. step-level.
**What CELA might do worse:** CAR's Shapley approach provides principled multi-step credit assignment
**Direct reproduction feasible:** YES (code available)

---

## 8. AgenticRAG-FP (Failure Propagation)

**Type:** Benchmark for failure propagation in multi-hop Agentic RAG
**Mechanism:** Certified fault injection at specific reasoning hops + downstream re-execution
**Key finding:** Extreme signal loss (0.00 diagnostic accuracy) at deeper hops
**Comparison to CELA:** Proves the EXACT problem CELA aims to solve. CELA's evidence-lineage tracking could address the "signal loss" problem.
**Direct reproduction feasible:** YES (benchmark)

---

## 9. AgenTracer

**Type:** Automated failure attribution framework + distilled model (AgenTracer-8B)
**Mechanism:** Counterfactual replay and programmed fault injection for dataset curation. Multi-granular RL training of lightweight diagnostic model.
**Approach:** Learned model vs. CELA's algorithmic approach
**What CELA does differently:** Structural algorithmic approach vs. learned model
**Direct reproduction feasible:** LIKELY

---

## 10. AGENTSCOPE

**Type:** Neuro-symbolic failure attribution framework
**Mechanism:** Structured behavior abstractions + "neural invariants" (formal specifications). LLM-guided reasoning checks trajectories against invariants.
**Approach:** Static/symbolic analysis, no counterfactual replay
**Comparison to CELA:** Fundamentally different approach (symbolic vs. counterfactual)
**Direct reproduction feasible:** LIKELY

---

## COMPETITOR POSITIONING SUMMARY

| System | Intervention Unit | Counterfactual? | Provenance? | Channel-level? | Code? |
|--------|-------------------|-----------------|-------------|----------------|-------|
| CELA | Evidence channel | YES | YES | YES | YES |
| Who&When | Benchmark only | N/A | N/A | N/A | YES |
| AgentRx | Step (constraint) | NO | NO | NO | YES |
| CHIEF | Agent/task hierarchy | YES | PARTIAL | PARTIAL | LIKELY |
| DoVer | State/plan | YES (active) | NO | NO | LIKELY |
| CausalFlow | Step | YES | NO | NO | LIKELY |
| CAR | Step (state-action) | YES | NO | NO | YES |
| AgenticRAG-FP | Benchmark only | N/A | N/A | N/A | YES |
| AgenTracer | Learned model | YES (training) | NO | NO | LIKELY |
| AGENTSCOPE | Symbolic/static | NO | NO | NO | LIKELY |

---

## KEY THREATS TO CELA NOVELTY

1. **CHIEF** uses "information flow" causal graphs that are conceptually similar to CELA's evidence-flow channels. CELA must clearly differentiate at the provenance-lineage granularity level.

2. **CAR** is the most direct methodological competitor (counterfactual replay + SCM + do-calculus). CELA must demonstrate that channel-level intervention outperforms step-level intervention.

3. **CausalFlow** provides the clearest step-vs-channel comparison target. Its CRS (step-level) vs. CELA's CEE (channel-level) is the core experiment.

4. "First causal replay for agents" is NOT defensible as a novelty claim. CAR, CausalFlow, DoVer, and CHIEF all use forms of causal/counterfactual analysis.

5. "First provenance-aware causal analysis" MIGHT be defensible if CHIEF's information-flow graph is sufficiently different from CELA's evidence-lineage graph.

---

## SEARCH COMPLETENESS NOTE

This search was conducted via web search as of September 2026. Some systems
(A2P specifically) could not be confirmed as failure-attribution systems.
Additional manual search of arXiv, ACL Anthology, and OpenReview proceedings
is recommended to ensure completeness.
