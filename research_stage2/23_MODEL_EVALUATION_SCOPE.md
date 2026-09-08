# CELA Model Evaluation Scope

This document defines the boundaries of evaluation for the CELA framework, distinguishing between what is evaluated in the current setup and what is deferred to external benchmarks or future work.

## 1. Deterministic Synthetic MockLLM Validity
- **Scope:** Validates the core algorithmic correctness of the CELA framework.
- **Components Tested:**
  - Graph construction and provenance tracking mechanisms.
  - Counterfactual replay logic and channel-level intervention application.
  - Correctness of the Causal Evidence Effect (CEE) computation.
  - Cost-aware greedy cascade prevention algorithms.
- **Objective:** Ensure the mathematical and logical foundation of the framework behaves perfectly under controlled, deterministic conditions where ground truth is known.

## 2. Real-LLM Validation Scope (Gemini)
- **Scope:** Validates CELA's performance in real-world, non-deterministic scenarios using state-of-the-art LLMs (e.g., Gemini).
- **Components Tested:**
  - Robustness of failure attribution when facing LLM variability and stochasticity.
  - Efficacy of the causal intervention on real semantic data and reasoning steps.
  - Demonstration of joint set-level interventions capturing real interaction effects.
- **Objective:** Demonstrate that the framework translates effectively from synthetic theory to practical applicability on real-world multimodal and reasoning tasks.

## 3. What External Benchmarks Would Test (Deferred)
- **Scope:** Generalization and comparative performance across diverse domains.
- **Components to be Evaluated Externally:**
  - Out-of-the-box performance on standardized benchmarks (e.g., SWE-bench, AgentBench).
  - Direct head-to-head empirical comparison of localization accuracy against state-of-the-art baselines like CAR, CausalFlow, or CHIEF.
  - Scalability analysis on massive, thousand-node multi-agent trajectories.

## 4. Known Limitations
- CEE is utilized as an operational metric, but not claimed as a novel estimand.
- The framework assumes access to intermediate execution states (glass-box/grey-box), limiting its applicability to pure black-box APIs where intermediate provenance cannot be traced.
- The cost-aware cascade prevention uses greedy heuristics, which may not always find the globally optimal budget allocation in highly non-linear intervention spaces.
