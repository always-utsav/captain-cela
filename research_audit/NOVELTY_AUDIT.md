# NOVELTY AUDIT

**Project:** CAPTAIN/CELA
**Date:** 2026-09-04

---

## 1. CLAIMED NOVELTY vs ACTUAL NOVELTY

### Potential Claim 1: "First causal replay framework for agents"
**Status:** ❌ RED — NOT NOVEL
**Evidence:** CAR (Causal Agent Replay), CausalFlow, DoVer, AgenTracer all use
forms of causal/counterfactual analysis for agent debugging. Multiple systems
predate or parallel CELA in this space.

### Potential Claim 2: "First counterfactual agent failure attribution system"
**Status:** ❌ RED — NOT NOVEL
**Evidence:** CAR explicitly uses do(·) interventions on SCMs. CausalFlow computes
Causal Responsibility Scores via step-level counterfactual interventions. CHIEF
uses counterfactual screening. DoVer uses active intervention verification.

### Potential Claim 3: "First intervention-based agent debugger"
**Status:** ❌ RED — NOT NOVEL
**Evidence:** DoVer performs real interventions. CAR applies do(·) to state-action
traces. AgentRx uses constraint-based step evaluation.

### Potential Claim 4: "First provenance-aware causal agent analysis"
**Status:** 🟡 YELLOW — PARTIALLY NOVEL
**Evidence:** CHIEF uses "information flow" causal graphs that are conceptually
analogous. However, CHIEF operates at agent/task hierarchy level, while CELA
operates at evidence-lineage level (sub-agent granularity). The distinction
exists but must be clearly articulated and empirically demonstrated.

### Potential Claim 5: "Evidence-channel intervention provides finer causal localization than step-level intervention"
**Status:** 🟢 GREEN (if experimentally supported) — POTENTIALLY NOVEL
**Evidence:** No existing system explicitly defines intervention at the
evidence-flow-channel level. CAR, CausalFlow intervene at step level.
CHIEF operates at agent/task level. CELA's channel-level granularity
(sub-step, provenance-defined) is a genuine gap in the literature.
**Requirement:** Must be experimentally demonstrated, not just claimed.

### Potential Claim 6: "Joint set-level counterfactual intervention for cascading failure prevention"
**Status:** 🟡 YELLOW — PARTIALLY NOVEL
**Evidence:** CAR uses Monte-Carlo Shapley for multi-step credit splitting.
CELA's joint replay (CEE(S) via actual joint intervention) is different from
Shapley decomposition. The greedy cascade optimization with cost/budget
constraints may be novel in this specific application context.
**Requirement:** Must compare against Shapley-based approaches.

### Potential Claim 7: "Provenance-aware multimodal evidence lineage"
**Status:** 🟡 YELLOW — ARCHITECTURE SUPPORTS, NOT EMPIRICALLY DEMONSTRATED
**Evidence:** Who&When Pro supports multimodal traces. CELA's evidence model
supports multiple modalities. But no multimodal experiments have been run.
**Requirement:** Cannot claim multimodal superiority without multimodal experiments.

---

## 2. DEFENSIBLE RESEARCH POSITIONING

### STRONGEST (if experimentally supported)

"CELA studies provenance-defined evidence-flow channels as a causal
intervention granularity for autonomous-agent failure propagation,
providing finer-grained causal localization than step-level intervention."

### Key comparison axis

| Granularity | Systems |
|-------------|---------|
| Agent-level | Who&When |
| Task-level | CHIEF |
| Step-level | CAR, CausalFlow, DoVer, AgenTracer |
| Channel-level | CELA (unique) |

### What makes channel-level potentially novel

1. One execution step can produce MULTIPLE independently traceable evidence
   pathways (e.g., tool result → reasoning AND tool result → memory)
2. Step-level intervention modifies the ENTIRE step output
3. Channel-level intervention can selectively modify ONE pathway while
   preserving others
4. This enables more precise attribution and more selective intervention

### What must be experimentally demonstrated

1. Channel-level actually provides finer localization (higher F1)
2. Channel-level enables more selective intervention (lower collateral)
3. Channel-level enables better prevention (fewer unnecessary interventions)
4. The benefit justifies the additional complexity/cost

---

## 3. COMPETITIVE THREAT ASSESSMENT

| Competitor | Threat Level | Reason |
|------------|-------------|--------|
| CAR | HIGH | Most direct methodology overlap (counterfactual replay + SCM) |
| CausalFlow | HIGH | Direct step-vs-channel comparison target |
| CHIEF | MEDIUM | Conceptually similar information-flow graphs |
| DoVer | MEDIUM | Active intervention approach, different mechanism |
| AgentRx | LOW | Constraint-based, no counterfactual replay |
| AgenTracer | LOW | Learned model, different paradigm |
| AGENTSCOPE | LOW | Symbolic, no counterfactual replay |
| Who&When | BENCHMARK | Evaluation target, not method competitor |
| AgenticRAG-FP | MOTIVATION | Proves the problem CELA solves |

---

## 4. CLAIMS THAT MUST BE REMOVED FROM ANY PAPER

1. "First causal framework for agents"
2. "First counterfactual debugging system"
3. "State of the art" (without supporting comparison)
4. "Multimodal superiority" (without multimodal experiments)
5. "Optimal cascade intervention" (greedy, not proven optimal)
6. "General agent failure attribution" (synthetic benchmark only)
7. "Scalable to arbitrary agent architectures" (only tested on reference agent)

---

## 5. CLAIMS THAT ARE PUBLICATION-GRADE (if experiments support them)

1. "Channel-level intervention enables more precise causal localization
    than step-level intervention in [specific scenario types]"
2. "Provenance-defined evidence-flow channels provide a natural intervention
    granularity for cascading agent failures"
3. "Joint evidence-channel counterfactual intervention captures interaction
    effects that individual-channel analysis misses"
4. "Cost-aware greedy cascade selection provides near-oracle prevention
    efficiency in [specific scenario types]"
