# CAPTAIN/CELA Weakness Audit

This document summarizes the findings from the systematic weakness audit of the CAPTAIN/CELA system. 

## Categories Evaluated

### 1. Redundant Pathways (BF-B: OR redundancy)
- **Question**: Does CELA correctly identify that blocking either alone prevents failure?
- **Finding**: **FAILS**
- **Analysis**: In an OR redundancy scenario, blocking a single pathway does NOT prevent the failure (the other redundant path still causes the failure). CELA's `FailureAnalyzer` and `BottleneckAnalyzer` currently evaluate interventions *marginally* (one by one). Consequently, single channel blocks yield a Causal Effect Estimate (CEE) of 0. CELA fails to recognize that a joint intervention is required to prevent the failure. 
- **Classification**: `DESIGN_LIMITATION`

### 2. Complementary Pathways (BF-C: AND complementarity)
- **Question**: Does CELA correctly identify that blocking both is needed?
- **Finding**: **PASSES** (with structural caveat)
- **Analysis**: In an AND complementarity scenario, the premise of the question is slightly misleading—blocking *just one* pathway is sufficient to prevent the failure. CELA correctly evaluates each single intervention as having a high effect (CEE > 0) because blocking any one component breaks the AND condition. However, CELA cannot structurally distinguish this from multiple independent single-causes since it only looks at marginal effects, but it successfully identifies that the failure can be mitigated.
- **Classification**: `DESIGN_LIMITATION` (for not explicitly labeling the AND structure)

### 3. Shared Source (BF-G)
- **Question**: Does channel intervention modify only the targeted artifact?
- **Finding**: **PASSES**
- **Analysis**: Verified in `captain/analysis/estimator.py`. `channel_to_intervention` correctly detects if a source event outputs multiple artifacts (`len(source_event.output_artifact_ids) > 1`). If so, it falls back to an `ARTIFACT_REPLACEMENT` intervention on the specific artifact, correctly achieving channel-level granularity without destroying other artifacts from the same source.
- **Classification**: None (Working as intended)

### 4. Large Candidate Sets
- **Question**: Generate a scenario with many candidates (10+). Does performance degrade?
- **Finding**: **FAILS**
- **Analysis**: CEE estimation runs counterfactual replays iteratively across all candidates. For $N$ candidates, it performs $N \times \text{num\_trials}$ synchronous replays. As candidate sets grow, the analysis time scales linearly, degrading performance noticeably.
- **Classification**: `ENGINEERING_LIMITATION` (Lack of parallel execution for counterfactual replay)

### 5. Near-zero CEE
- **Question**: Create a scenario where intervention has almost no effect. Does CEE correctly report ~0?
- **Finding**: **PASSES**
- **Analysis**: In distractor scenarios (BF-D), blocking an irrelevant structural channel leaves the outcome unchanged. The CEE Estimator calculates this effect as 0.0, properly filtering out false positives.
- **Classification**: None

### 6. Empty Candidate Set
- **Question**: What happens when FailureAnalyzer finds no candidates?
- **Finding**: **PASSES**
- **Analysis**: If the graph is sparse or the failure region yields no candidates, `FailureAnalyzer.candidates()` safely returns `[]`. The downstream `BottleneckAnalyzer` natively handles empty lists and safely returns a result with `supported=False`.
- **Classification**: None

### 7. No Failure
- **Question**: What happens when the evaluator says there was no failure?
- **Finding**: **PASSES**
- **Analysis**: If the baseline run is evaluated as "no failure" (Outcome=False), and a counterfactual intervention also yields "no failure" (Outcome=False), the CEE delta is correctly computed as 0. 
- **Classification**: None

### 8. Single-event Trace
- **Question**: Minimal trace with just one event.
- **Finding**: **PASSES**
- **Analysis**: The pipeline degrades gracefully. A minimal trace yields an empty candidate set, which cascades safely through to a null bottleneck result.
- **Classification**: None

### 9. Deterministic Replay Stability
- **Question**: Same scenario, same seed, two replay runs. Are results identical?
- **Finding**: **PASSES**
- **Analysis**: ID generation (`_is_deterministic()`) and LLM responses (via `MockLLMProvider`) are strictly seed-dependent. Consecutive replays yield the exact same event flow and identical CEE outcomes.
- **Classification**: None

### 10. Evaluator Independence
- **Question**: Does the evaluator use only factual/counterfactual outputs, never ground truth?
- **Finding**: **PASSES**
- **Analysis**: Evaluators like `_build_keyword_evaluator` are constructed as closures that receive strictly an `ExecutionRun` object. They evaluate only the factual/counterfactual payloads and artifacts, never referencing the hidden `ScenarioGroundTruth` object.
- **Classification**: None

## Summary of Weaknesses Discovered
1. **Marginal Evaluation (Design)**: CELA is blind to joint required interventions (Redundancy/OR structures) because single-candidate CEE yields 0. 
2. **Replay Scalability (Engineering)**: Serial counterfactual replays scale poorly ($O(N)$) for large structural spaces.
