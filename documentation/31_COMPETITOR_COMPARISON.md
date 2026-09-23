# Competitor Comparison

This document provides a detailed comparison between CAPTAIN/CELA and 12+ competitor systems based on the `competitor_matrix.csv` data.

**Note: Counts across systems are not directly comparable because evaluation units and objectives differ.**

## Key Competitor Systems

1. **Who&When Pro**
   - **Focus:** Agent failure attribution benchmark
   - **Scale:** Trajectory-scale benchmark (12K+ trajectories)
   - **Mechanism:** Observational, no intervention. Uses step-level accuracy / failure attribution based on human annotation.

2. **CAR (Causal Agent Replay)**
   - **Focus:** Causal failure step identification
   - **Mechanism:** Step-level do() intervention with contrastive + Monte-Carlo Shapley. Uses forward stochastic replay.

3. **CausalFlow**
   - **Focus:** Interventional failure diagnosis
   - **Mechanism:** Step-level Causal Responsibility Scores (CRS) with counterfactual intervention for minimal repairs.

4. **From Spark to Fire**
   - **Focus:** Error cascade modeling
   - **Mechanism:** Cascade modeling in multi-agent environments using a governance layer. Analyzes message-level structural cascades.

5. **AgentRx**
   - **Focus:** First unrecoverable failure step
   - **Mechanism:** Trajectory IR to find the first unrecoverable step based on constraint violations.

6. **AgenticRAG-FP**
   - **Focus:** RAG failure propagation
   - **Mechanism:** Hop-level propagation and retrieval re-execution to measure signal loss depth in RAG pipelines.

7. **Oat**
   - **Focus:** Unsupervised anomaly detection at step-level.

8. **AgentProcessBench**
   - **Focus:** Process-level step evaluation.

9. **AgenTracer**
   - **Focus:** Multi-agent failure attribution with fault injection.

10. **RAFFLES**
    - **Focus:** Reasoning-based attribution via LLM-as-judge probing.

11. **DoVer**
    - **Focus:** Multi-agent failure testing via segment-level message edit.

12. **SAFARI**
    - **Focus:** Ultra-long context fault debugging via tool-augmented search.

## CAPTAIN/CELA Differentiator

Unlike prior work that relies on step-level isolation or observational heuristics, CAPTAIN/CELA operationalizes causal analysis at the **evidence-flow channel level**. This granularity (below step, above bit-level) allows for selective intervention (ARTIFACT_REPLACEMENT) rather than treating the entire execution step/source event as the only intervention unit. CELA explicitly traces how individual evidence artifacts propagate through steps and calculates Causal Evidence Effect (CEE) using deterministic paired replay.
