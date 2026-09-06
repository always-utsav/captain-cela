# 03 RESEARCH COMPONENT MAP

## 1. Evidence Model & Lineage
- **Purpose:** Map artifacts/events to semantic information units
- **Scientific Role:** Defines CELA's unique intervention granularity
- **Inputs:** ExecutionRun, ProvenanceRecords
- **Outputs:** Evidence, EvidenceTransformation
- **Dependencies:** captain.models, captain.provenance
- **Tests:** test_evidence.py
- **Confounds:** Evidence ID nondeterminism (FIXED via deterministic_ids)
- **Limitations:** 1:1 artifact-to-evidence mapping in current impl

## 2. Evidence-Flow Graph
- **Purpose:** Build traversable information-flow structure
- **Scientific Role:** Basis for failure-relevant upstream region extraction
- **Inputs:** Evidence list, EvidenceTransformation list
- **Outputs:** EvidenceFlowGraph (traversable)
- **Dependencies:** captain.evidence.model
- **Tests:** test_evidence.py
- **Confounds:** Graph structure is NOT a causal claim
- **Limitations:** No cycles, no temporal edges

## 3. Failure Model & Analyzer
- **Purpose:** Represent failures, extract candidate interventions
- **Scientific Role:** Reduce search space from all edges to failure-relevant upstream
- **Inputs:** EvidenceFlowGraph, Failure
- **Outputs:** Candidate list, ChannelIntervention list
- **Dependencies:** captain.evidence.graph
- **Tests:** test_failures.py
- **Confounds:** Screening score is heuristic, NOT causal probability
- **Limitations:** Score ordering may not match causal ordering

## 4. CEE Estimator
- **Purpose:** Estimate Counterfactual Evidence-Flow Effect
- **Scientific Role:** Core causal measurement via paired replay
- **Inputs:** baseline ExecutionRun, ChannelIntervention, FailureEvaluator
- **Outputs:** CEEResult (cee, CI, trials)
- **Dependencies:** captain.replay.engine, captain.intervention
- **Tests:** test_analysis.py
- **Confounds:** MockLLM replays pre-scripted responses; CEE measures intervention effect on keyword presence, not true causal mechanism
- **Limitations:** CEE=0 when MockLLM response contains keyword regardless of tool result

## 5. Cascade Estimator & Greedy Selector
- **Purpose:** Set-level CEE + cost-aware selection
- **Scientific Role:** Handle redundancy/complementarity
- **Inputs:** ChannelIntervention list, CostModel, FailureEvaluator
- **Outputs:** CascadeResult, SelectionResult
- **Dependencies:** captain.analysis.estimator, captain.replay
- **Tests:** test_analysis.py
- **Confounds:** Greedy is NOT proven optimal
- **Limitations:** Shared-source channels may cause replay rejection

## 6. Benchmark Scenarios (BF-A through BF-F)
- **Purpose:** Independent testbeds with known causal ground truth
- **Scientific Role:** Provide unbiased validation
- **Inputs:** Random seeds
- **Outputs:** BenchmarkScenario
- **Tests:** test_benchmarks.py, test_stage1_integrity.py
- **Confounds:** Synthetic-only; single agent architecture
- **Limitations:** MockLLM does not react to interventions

## 7. Benchmark Runner & Evaluator
- **Purpose:** Execute methods and compute metrics
- **Scientific Role:** Isolate method selections from ground truth
- **Inputs:** Scenarios, methods
- **Outputs:** BenchmarkResult, BenchmarkMetrics
- **Tests:** test_benchmarks.py
- **Confounds:** Metrics compare selection against ground truth, not actual causal effect
- **Limitations:** No external benchmark evaluation

## 8. Baselines (B1-B5)
- **Purpose:** Non-causal comparison methods
- **Scientific Role:** Demonstrate CELA adds value over simpler approaches
- **Tests:** test_benchmarks.py
- **B1:** Random selection
- **B2:** Provenance-only (structural score)
- **B3:** Individual CEE rank
- **B4:** Graph structural distance
- **B5:** Cost-aware structural

## 9. CELA Methods (A1-A5)
- **Purpose:** Ablation ladder of CELA components
- **Scientific Role:** Demonstrate each component's contribution
- **A1:** Provenance screening
- **A2:** Individual CEE
- **A3:** Marginal gain ordering
- **A4:** Greedy cascade selection
- **A5:** Cost-aware cascade selection

## 10. Experiment Runner
- **Purpose:** Multi-instance, multi-seed experiment orchestration
- **Outputs:** ExperimentResult with reproducibility metadata
- **Dependencies:** BenchmarkRunner, statistics module
- **Tests:** test_experiments.py

## 11. Statistics Module
- **Purpose:** Rigorous statistical testing
- **Implements:** bootstrap_ci, paired_comparison, holm_bonferroni, cohen_d
- **Tests:** test_experiments.py
- **Confounds:** Small sample sizes in smoke campaign

## 12. Counterfactual Replay Engine
- **Purpose:** Re-execute runs under intervention (the do() operator)
- **Scientific Role:** Produces genuine counterfactual execution
- **Inputs:** baseline ExecutionRun, InterventionSet
- **Outputs:** CounterfactualResult (new ExecutionRun)
- **Tests:** test_replay.py, test_stage1_integrity.py
- **Confounds:** MockLLM ignores tool result changes
- **Limitations:** Shared-source intervention rejection

## 13. Intervention Model & Validation
- **Purpose:** Formal specification of execution modifications
- **Types:** ARTIFACT_REPLACEMENT, TOOL_RESULT_OVERRIDE, EVENT_DISABLE, EVENT_OUTPUT_OVERRIDE
- **Tests:** test_intervention.py
- **Confounds:** Channel-level vs step-level targeting depends on evidence_graph availability

## 14. Provenance Extraction & Query
- **Purpose:** Extract deterministic structural links between events/artifacts
- **Scientific Role:** Foundation for "hard" provenance (no semantic inference)
- **Tests:** test_provenance.py
