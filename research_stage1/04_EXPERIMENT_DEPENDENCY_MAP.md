# 04 EXPERIMENT DEPENDENCY MAP

## Single-Channel Attribution (BF-A)
- BenchmarkScenario (generate_single_cause)
- FailureAnalyzer -> candidates
- CEEEstimator -> CEEResult
- MetricEvaluator -> AttributionMetrics
- Data flow: Scenario -> Method.select() -> MetricEvaluator.compute()

## Redundancy Detection (BF-B)
- BenchmarkScenario (generate_redundant)
- CascadeEstimator -> CascadeResult
- GreedyCascadeSelector -> SelectionResult
- MetricEvaluator -> InteractionMetrics (redundancy_group_recovery_rate)

## Complementarity Detection (BF-C)
- BenchmarkScenario (generate_complementary)
- CascadeEstimator (joint replay)
- MetricEvaluator -> InteractionMetrics (complementary_group_recovery_rate)

## Cascade Depth (BF-E)
- BenchmarkScenario (generate_cascade)
- FailureAnalyzer -> candidates (multi-hop)
- CEEEstimator per candidate
- MetricEvaluator -> LocalizationMetrics

## Step-vs-Channel Comparison
- channel_to_intervention (channel-level, with evidence_graph)
- step_level_intervention (event-level, targets mediating event)
- Same: factual run, evaluator, replay engine, candidates, seed
- Different: intervention targeting mechanism ONLY
- CounterfactualReplayEngine.replay()
- Compare: attribution precision, collateral modification

## Cost/Utility Analysis (BF-F)
- BenchmarkScenario (generate_cost_asymmetric)
- CostModel with channel_costs
- GreedyCascadeSelector with lambda_cost, budget
- MetricEvaluator -> EfficiencyMetrics, OptimalityMetrics

## Ablation Campaign
- ExperimentRunner
- Methods A1 through A5 (progressive component addition)
- compute_ablation_ladder -> AblationStep deltas
- Paired statistical tests

## Replay Convergence
- CEEEstimator with varying num_trials (1, 3, 5, 10, 25)
- bootstrap_ci -> CI width
- Ranking stability metric

## Seed Robustness
- ExperimentRunner.run_sensitivity
- Multiple seeds -> coefficient of variation
- SensitivityResult -> is_stable
