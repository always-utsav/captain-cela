# RESEARCH VALIDATION PLAN

**Project:** CAPTAIN/CELA
**Date:** 2026-09-04
**Version:** v1.0
**Baseline:** Stage 18 COMPLETE, 644 tests, 0 CRITICAL/HIGH science issues

---

## CENTRAL RESEARCH QUESTION

Does provenance-defined evidence-flow channel intervention provide more
precise causal failure localization and more selective cascading failure
prevention than execution-step-level intervention in autonomous agents?

---

## HYPOTHESES

### H1 (PRIMARY): Channel vs Step Localization
Evidence-channel-level intervention provides higher causal attribution
F1 than step-level intervention in scenarios with branching evidence paths.

- Independent variable: intervention granularity (channel vs step)
- Dependent variable: causal F1, Recall@1, Recall@K
- Ground truth: hidden causal mechanism
- Method: CELA A2 vs B3 (individual CEE, channel vs step)
- Statistical test: paired permutation, bootstrap CI, Cohen's d

### H2: Joint Set-Level Intervention
Joint evidence-channel counterfactual intervention captures interaction
effects (redundancy, complementarity) that individual-channel ranking misses.

- Independent variable: selection method (individual vs joint)
- Dependent variable: prevention rate, CEE(S), prevention-set recall
- Ground truth: hidden prevention sets
- Method: A2 (individual) vs A4 (greedy joint) vs Oracle
- Statistical test: paired permutation, bootstrap CI

### H3: Cascade Prevention Efficiency
Cost-aware greedy evidence-channel selection provides better
prevention-efficiency tradeoffs than structural or individual-CEE ranking.

- Independent variable: selection method (B2, B3, B5, A4, A5, Oracle)
- Dependent variable: utility, cost, prevention rate, oracle regret
- Method: full baseline + CELA ladder comparison
- Statistical test: paired comparisons, Holm-Bonferroni correction

### H4: Provenance Guidance
Provenance-based candidate screening reduces evaluation cost while
maintaining attribution quality.

- Independent variable: provenance availability (with/without)
- Dependent variable: F1, cost, replay count
- Method: ablation removing provenance (A1 vs random B1)
- Statistical test: paired comparison

---

## EXPERIMENT REGISTRY

### EXP-01: Current Baseline Reproduction
- experiment_id: baseline_v1
- hypothesis: none (baseline)
- seeds: [1, 2, 3, 4, 5, 10, 20, 42, 100, 2026]
- families: [BF-A, BF-B, BF-C, BF-D, BF-E, BF-F]
- methods: [B1, B2, B3, B4, B5, A1, A2, A3, A4, A5]
- instances_per_family: 10
- replay_budget: 50
- metrics: F1, Recall@1, Recall@K, prevention_rate, CEE, cost, regret
- expected_runtime: <30s
- output: research_results/raw/baseline_v1/

### EXP-02: Step-vs-Channel Intervention (H1, PRIMARY)
- experiment_id: step_vs_channel_v1
- hypothesis: H1
- causal_mechanism: branching evidence paths (1 event -> 2+ channels)
- independent_variable: intervention granularity
- seeds: [1, 2, 3, 4, 5, 10, 20, 42, 100, 2026]
- scenario_types: independent, redundant, complementary, shared-source, branching, convergent
- methods: [CELA-channel, Step-level baseline]
- metrics: F1, Recall@1, collateral_modification, evidence_preservation
- leakage_risks: step baseline must not receive channel info
- output: research_results/raw/step_vs_channel_v1/

### EXP-03: Negative Controls / Placebo
- experiment_id: negative_controls_v1
- hypothesis: CEE of irrelevant channels ~ 0
- mechanism: intervene on known-irrelevant channels
- expected: no systematic causal effect
- seeds: [42, 1, 2, 3, 4]
- metrics: placebo CEE, false positive rate
- output: research_results/raw/negative_controls_v1/

### EXP-04: Redundancy
- experiment_id: redundancy_v1
- hypothesis: H2 (partial)
- mechanism: OR-redundant channels
- expected: CEE(A), CEE(B) each < CEE({A,B})
- seeds: [42, 1, 2, 3, 4, 5, 10, 20, 100, 2026]
- metrics: individual CEE, joint CEE, prevention_set_recall
- output: research_results/raw/redundancy_v1/

### EXP-05: Complementarity
- experiment_id: complementarity_v1
- hypothesis: H2 (partial)
- mechanism: AND-complementary channels
- expected: CEE(A)~0, CEE(B)~0, CEE({A,B})>0
- seeds: [42, 1, 2, 3, 4, 5, 10, 20, 100, 2026]
- metrics: individual CEE, joint CEE
- output: research_results/raw/complementarity_v1/

### EXP-06: Cascade Depth
- experiment_id: cascade_depth_v1
- hypothesis: attribution degrades with depth
- mechanism: serial A->B->C->...->Failure, depth 1-10
- seeds: [42, 1, 2, 3, 4, 5]
- metrics: F1, CEE, bottleneck accuracy, cost
- output: research_results/raw/cascade_depth_v1/

### EXP-07: Replay Convergence
- experiment_id: replay_convergence_v1
- hypothesis: more replays => tighter CI, stable ranking
- N values: [1, 5, 10, 25, 50, 100, 200]
- seeds: [42, 1, 2, 3, 4]
- metrics: CEE, CI_width, ranking_stability, top1_stability
- output: research_results/raw/replay_convergence_v1/

### EXP-08: Seed Robustness
- experiment_id: seed_robustness_v1
- hypothesis: results stable across seeds
- seeds: [1, 2, 3, 4, 5, 10, 20, 42, 100, 2026]
- configuration: identical except seed
- metrics: mean, median, sd, 95% CI, rank stability, CV
- output: research_results/raw/seed_robustness_v1/

### EXP-09: Cascade Prevention (H3)
- experiment_id: cascade_prevention_v1
- hypothesis: H3
- methods: [B1, B2, B3, B5, A2, A4, A5, Oracle]
- seeds: [42, 1, 2, 3, 4, 5, 10, 20, 100, 2026]
- families: [BF-A through BF-F]
- metrics: prevention_rate, CEE(S), cost, utility, regret
- output: research_results/raw/cascade_prevention_v1/

### EXP-10: Cost/Utility Analysis (H3)
- experiment_id: cost_utility_v1
- lambda_values: [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
- budget_values: [1, 2, 3, 5, 10, unlimited]
- metrics: cost vs prevention, utility vs cost, Pareto frontier
- output: research_results/raw/cost_utility_v1/

### EXP-11: Ablation Campaign
- experiment_id: ablation_v1
- levels: A1->A2->A3->A4->A5, remove components
- ablations: [-provenance, -screening, -CEE, -joint_CEE, -marginal, -cost, -cascade, channel->step]
- metrics: delta F1, delta prevention, delta cost
- output: research_results/raw/ablation_v1/

### EXP-12: Scalability
- experiment_id: scalability_v1
- candidate_counts: [3, 5, 10, 20, 50]
- lineage_depths: [1, 2, 3, 5, 8, 10]
- methods: [B1, A2, A4, Oracle]
- metrics: runtime, replay_count, memory
- output: research_results/raw/scalability_v1/

### EXP-13: Shared-Source Limitation
- experiment_id: shared_source_v1
- mechanism: multiple channels from same event
- expected: CELA may fall back to event-level
- metrics: isolation_rate, collateral_modification
- output: research_results/raw/shared_source_v1/

### EXP-14: Root vs Symptom
- experiment_id: root_vs_symptom_v1
- mechanism: Root->Intermediate->Symptom->Failure
- expected: identify root vs propagation vs actuator
- metrics: root_attribution_accuracy, propagation_localization
- output: research_results/raw/root_vs_symptom_v1/

### EXP-15: Downstream Repair
- experiment_id: downstream_repair_v1
- mechanism: A->B->Failure and A->B->Repair->Success variants
- expected: earliest cause != strongest CEE in some cases
- metrics: origin attribution, CEE ranking, prevention effectiveness
- output: research_results/raw/downstream_repair_v1/

---

## EXECUTION ORDER

1. EXP-01 (baseline) — validate current system works at scale
2. EXP-03 (negative controls) — validate causal credibility
3. EXP-07 (replay convergence) — determine replay budget
4. EXP-08 (seed robustness) — validate stability
5. EXP-04 (redundancy) — test interaction handling
6. EXP-05 (complementarity) — test interaction handling
7. EXP-02 (step vs channel) — PRIMARY NOVELTY EXPERIMENT
8. EXP-06 (cascade depth) — depth sensitivity
9. EXP-14 (root vs symptom) — localization quality
10. EXP-15 (downstream repair) — non-obvious attribution
11. EXP-09 (cascade prevention) — prevention experiment
12. EXP-10 (cost/utility) — efficiency
13. EXP-11 (ablation) — component contribution
14. EXP-12 (scalability) — computational cost
15. EXP-13 (shared-source) — limitation documentation

---

## PRE-EXECUTION CHECKLIST

- [x] Repository safety audit (REPOSITORY_MANIFEST.md)
- [x] GitHub readiness (GITHUB_READINESS_REPORT.md)
- [x] Code science audit (FULL_CODE_SCIENCE_AUDIT.md)
- [x] Mathematical audit (within FULL_CODE_SCIENCE_AUDIT.md)
- [x] Information leakage audit (within FULL_CODE_SCIENCE_AUDIT.md)
- [x] Competitor analysis (COMPETITOR_EVIDENCE.md)
- [x] Novelty audit (NOVELTY_AUDIT.md)
- [x] Competitor matrix (COMPETITOR_MATRIX.csv)
- [x] Novelty matrix (NOVELTY_MATRIX.csv)
- [ ] Intervention fidelity tests — Phase 4
- [ ] Determinism repair — Phase 5
- [ ] Baseline execution — Phase 6

---

## VALIDITY THREATS

1. **Synthetic-only benchmark**: Results on synthetic scenarios do not
   automatically generalize. This is a known limitation.
2. **Single reference agent**: Only one agent architecture tested.
3. **Keyword evaluator**: Simple keyword matching may not reflect realistic
   failure evaluation.
4. **UUID nondeterminism**: Evidence IDs vary across runs, affecting
   exact metric values.
5. **No real LLM**: MockLLMProvider — controlled but not realistic.
6. **No external benchmark**: No Who&When or external dataset evaluation.
7. **No direct competitor reproduction**: CAR, CausalFlow not implemented.

---

## INTERPRETATION RULES

1. Never claim significance from p-value alone
2. Always report effect size alongside p-value
3. Always report sample size and CI
4. Never generalize beyond synthetic benchmark without qualification
5. Report all primary comparisons, including negative results
6. Separate primary/secondary/exploratory comparisons
7. Use Holm-Bonferroni for multiple comparisons
8. Distinguish statistical significance from practical significance
