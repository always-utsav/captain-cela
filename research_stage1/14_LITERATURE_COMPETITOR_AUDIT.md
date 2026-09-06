# 14 LITERATURE / COMPETITOR AUDIT

## Most Relevant Competitors

### 1. CAR (Causal Agent Replay)
- **Approach:** Step-level SCM + do-calculus, Monte-Carlo Shapley values
- **Granularity:** STEP (entire execution step)
- **Causal framework:** SCM with learned structural equations
- **Distinguishing from CELA:** CAR operates at step granularity; CELA targets evidence-flow channels within steps
- **Comparison feasibility:** Conceptual only (no public implementation)

### 2. CausalFlow
- **Approach:** Step-level Counterfactual Replay Score (CRS)
- **Granularity:** STEP
- **Causal framework:** Counterfactual replay per step
- **Distinguishing from CELA:** CausalFlow replays entire step ablation; CELA targets specific information channels
- **Comparison feasibility:** Conceptual only

### 3. CHIEF
- **Approach:** Hierarchical causal graph of agent/task interactions
- **Granularity:** AGENT/TASK (coarser than step)
- **Causal framework:** Hierarchical causal model
- **Distinguishing from CELA:** CHIEF models inter-agent causality; CELA models intra-agent evidence flow
- **Comparison feasibility:** Conceptual only

### 4. DoVer
- **Approach:** Active hypothesis-driven causal debugging
- **Granularity:** STEP + hypothesis testing
- **Distinguishing from CELA:** Active probing vs passive replay

### 5. AgentRx
- **Approach:** Constraint-based causal reasoning (no counterfactual replay)
- **Distinguishing from CELA:** No replay; uses constraint propagation

## Non-Competitors Surveyed

| System | Category | Why Not Competitor |
|--------|----------|-------------------|
| Who&When/Pro | Benchmark (12,326 traces) | Evaluation framework, not method |
| AgenticRAG-FP | RAG failure benchmark | Domain-specific |
| AgenTracer | Learned model (8B params) | Neural approach, not causal |
| AGENTSCOPE | Neuro-symbolic | Analytical, not interventional |
| RAFFLES | LLM-as-Judge | Evaluation, not attribution |
| SAFARI | Search-based investigation | Active debugging |
| OAT | Neural ODE anomaly detection | Not causal attribution |
| A2P | Process mining | NOT failure attribution |

## CELA Novelty Assessment

### Provisional Novelty Claim
CELA operationalizes causal intervention at the provenance-defined evidence-flow channel level rather than treating an entire execution step as the atomic intervention unit.

### Claims to AVOID
- First causal replay (CAR, CausalFlow do this)
- First counterfactual debugging (DoVer does this)
- First causal attribution (many systems do this)
- First provenance analysis (standard)
- First multimodal failure analysis (not unique)

### What CELA MAY claim (if empirically demonstrated)
- Evidence-flow channels as a finer intervention unit than steps
- Provenance-grounded channel identification (hard provenance, not semantic)
- Set-level causal estimation with joint replay (not summing individual CEEs)

## Verdict: GREEN — Novelty hypothesis is defensible but NOT yet empirically demonstrated
