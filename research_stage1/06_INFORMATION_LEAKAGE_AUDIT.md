# 06 INFORMATION LEAKAGE AUDIT

## Summary: NO LEAKAGE FOUND

## Information Boundaries

### Boundary 1: Ground Truth -> Methods
- **Rule:** ScenarioGroundTruth NEVER passed to methods
- **Verified by:** test_scenario_ground_truth_not_in_method_inputs (PASS)
- **Evidence:** Method.select() signature: (candidates, failure, evidence_graph, run, evaluator)
- **Ground truth fields NOT in any method input:** causal_channel_ids, required_prevention_sets, redundancy_groups, complementary_groups, single_intervention_outcomes

### Boundary 2: Evaluator Independence
- **Rule:** Evaluator checks execution output only, not method identity
- **Verified by:** test_evaluator_does_not_inspect_method_identity (PASS)
- **Evidence:** FailureEvaluator is Callable[[ExecutionRun], bool]; no method reference

### Boundary 3: Equal Information for All Methods
- **Rule:** All baselines and CELA methods receive identical inputs
- **Verified by:** test_all_baselines_receive_same_information (PASS)
- **Evidence:** All use BaselineMethod.select() with same signature

### Boundary 4: Candidate IDs Do Not Encode Truth
- **Rule:** Intervention IDs must not contain hidden causal information
- **Verified by:** test_candidate_generation_does_not_encode_answer (PASS)
- **Evidence:** IDs are hash-based (deterministic_ids) or uuid-based, contain no tool names or keywords

### Boundary 5: Step and Channel Methods Have Matched Information
- **Rule:** Step-level and channel-level baselines receive same candidate list
- **Evidence:** Both use the same ChannelIntervention objects; only the mapping to Intervention differs (channel_to_intervention vs step_level_intervention)
- **Verified by:** Smoke campaign uses identical scenario for both

### Boundary 6: Benchmark Construction Does Not Leak
- **Rule:** The evaluator is built from keyword specification, NOT from causal channel IDs
- **Evidence:** _build_keyword_evaluator() receives keyword list, not channel IDs. The fact that "42" is the failure keyword is visible in the evaluator, but the evaluator does not reveal WHICH channel carries "42"
- **Status:** PASS

### Boundary 7: Hidden Causal Mechanism Not in Method Inputs
- **Rule:** CausalMechanismSpec is in ground_truth only
- **Evidence:** scenarios.py line 14: "The hidden causal mechanism is NEVER passed to methods."
- **Code audit:** BenchmarkScenario.ground_truth contains CausalMechanismSpec. Methods receive BenchmarkScenario.{run, evidence_graph, failure, candidates} only.
- **Status:** PASS

## Verdict: PASS
All 7 information boundaries verified. No ground truth leakage detected.
