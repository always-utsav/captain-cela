# Final Scientific Freeze — CAPTAIN/CELA

**Date**: 2026-09-22
**Status**: FROZEN FOR PAPER WRITING

---

## 1. Final Research Question

Can causal attribution in autonomous AI-agent failure analysis be made more
selective by intervening at the evidence-flow channel level rather than at
the source-event level?

## 2. Final Hypotheses

**H1 (Primary)**: Channel-level intervention (ARTIFACT_REPLACEMENT) provides
more selective causal localization than source-event-level intervention
(TOOL_RESULT_OVERRIDE), as measured by preserved evidence count and
collateral modification rate.

**H2 (Supporting)**: CELA's evidence-flow attribution framework
(methods A3–A5) can correctly distinguish causal from non-causal evidence
channels in controlled benchmark scenarios.

**H3 (Sanity)**: A real LLM's output genuinely depends on the content of
its evidence, validating the core premise underlying CELA's intervention
mechanism.

## 3. Final Benchmark Families

| Family | Mechanism | Topology | Status |
|--------|-----------|----------|--------|
| BF-A | Single channel | Single cause + distractor | Correct |
| BF-B | Redundant OR | Both cause failure independently | Correct |
| BF-C | Complementary AND | Both required for failure | Correct |
| BF-D | Distractor | One cause + two distractors | Correct |
| BF-E | Cascade | Multi-hop propagation | Correct |
| BF-F | Cost-asymmetric | AND logic with budget constraint | Corrected (keyword_logic: any→all) |
| BF-G | Shared source | Multi-artifact from single tool | Correct (primary experiment) |
| BF-H | Convergent mixed | Mixed causal+benign inputs | Relabeled (was "branching") |
| BF-I | Convergent | Single causal among converging paths | Correct |
| BF-J | Parallel sources | Independent causal sources | Relabeled (was "root vs symptom") |
| BF-K | Downstream persistence | Ineffective repair attempt | Relabeled (was "downstream repair") |

## 4. Final Primary Experiment

**Granularity Comparison on BF-G** (5 instances, seed 42):
- Same factual execution, same evaluator, same seed, same task
- Channel intervention: ARTIFACT_REPLACEMENT targeting causal artifact
- Source-event intervention: TOOL_RESULT_OVERRIDE on producing tool event

## 5. Final Baselines

| Code | Name | Description |
|------|------|-------------|
| B1 | Random | Random candidate selection |
| B2 | Provenance-only | Select by provenance connectivity |
| B3 | CEE-rank | Rank by individual CEE |
| B4 | Cost-only | Select cheapest intervention |
| B5 | Oracle | Ground-truth selection (upper bound) |
| A1 | CELA-provenance | ≡ B2 (documented equivalence) |
| A2 | CELA-CEE | ≡ B3 (documented equivalence) |
| A3 | CELA-cascade | Cascade estimation |
| A4 | CELA-greedy | Greedy cascade selection |
| A5 | CELA-full | Full CELA pipeline |

## 6. Final Metrics

- causal_precision, causal_recall, causal_f1
- recall_at_1
- failure_prevention_rate
- prevention_set_recall
- cee_set
- preserved_evidence (granularity)
- collateral_modification (granularity)
- affected_evidence (granularity)

## 7. Final Statistical Protocol

- **Unit of analysis**: Scenario instance
- **Bootstrap CI**: 2000 resamples, percentile method, α=0.05
- **Paired comparison**: Permutation test (≤3 unique values) or
  Wilcoxon signed-rank (>3 unique values)
- **Multiple comparison**: Holm-Bonferroni correction
- **Effect size**: Paired Cohen's d
- **Sensitivity**: Coefficient of variation (CV < 0.2)
- **No t-tests are performed** (stdlib-only implementation)

## 8. Final Real-LLM Scope

**Classification**: Controlled real-LLM intervention sanity check

- Provider: Google Gemini API
- Model: gemini-3.6-flash
- Temperature: 0.0
- Trials: 5
- Prompts: Handcrafted (factual / channel-blocked / source-blocked)
- Evaluator: Keyword presence ("42")
- This does NOT run CAPTAIN's agent, evidence graph, or replay engine
- This validates the PREMISE, not the full system
- One model, one scenario, handcrafted prompts

## 9. Final Literature/Competitor Scope

12 systems audited. Safe positioning:

> CELA operationalizes causal analysis at the provenance-defined
> evidence-flow channel level, rather than treating the execution
> step/source event as the only intervention unit.

No "first" claims. No "universally superior" claims.
Competitor matrix in research_stage2/21_COMPETITOR_CAPABILITY_MATRIX.csv.

## 10. Supported Claims

| ID | Claim | Status | Evidence |
|----|-------|--------|----------|
| C1 | Channel more selective than source-event | **Supported** | Granularity data: channel preserves 1, source-event preserves 0 |
| C2 | Channel preserves unrelated evidence | **Supported** | Channel collateral=0, source-event collateral=1 |
| C4 | Negative controls CEE=0 | **Supported** | All 4 controls: observed_cee=0.0, passed=true |
| C5 | Seed stability | **Supported** | CV < 0.2 across 5 seeds |
| C6 | Replay stability | **Supported** | CEE=1.0 at all replay counts (deterministic, trivially true) |
| C7 | Real-LLM CEE > 0 | **Supported** | channel_cee=0.40, source_event_cee=0.40 |

## 11. Unsupported Claims

| ID | Claim | Status | Reason |
|----|-------|--------|--------|
| C3 | A5 > B1 on causal_f1 | **Not supported** | p=0.1156, not significant after Holm-Bonferroni |

## 12. Negative Results

1. **C3**: CELA A5 does not achieve statistically significantly higher
   causal F1 than random baseline B1 (p=0.1156). This may reflect that
   the controlled synthetic scenarios are too simple for the full CELA
   pipeline to differentiate from random selection.

2. **Replay convergence is trivially true**: With deterministic MockLLM,
   CEE=1.0 at all replay counts with CI width=0.0. This is expected
   behavior, not evidence of stochastic convergence.

## 13. Known Limitations

1. All benchmark experiments use MockLLM (deterministic, scripted)
2. Real-LLM validation is a sanity check, not end-to-end replay
3. BF-H topology is convergent despite BRANCHING enum name
4. BF-J tests parallel sources, not true root-vs-symptom
5. BF-K tests persistence, not genuine repair
6. A1 ≡ B2 and A2 ≡ B3 (documented method equivalences)
7. Pathway stress, cascade/joint intervention, and cost/utility sweep
   experiments are NOT IMPLEMENTED and NOT EXECUTED
8. No external LLM agent was run through the CAPTAIN pipeline
9. Statistics are stdlib-only (no scipy)
10. One real LLM model tested (gemini-3.6-flash)

## 14. Reproducibility Commands

```bash
# Deterministic results (no API key needed)
python research/run_campaign.py
python captain/experiments/figures.py
python captain/experiments/claims.py

# Real-LLM sanity check (requires GEMINI_API_KEY in .env)
python research/run_real_llm.py

# Verification
python -m pytest tests/ -q
python -m ruff check captain/ tests/
python -m mypy captain
```

## 15. Exact Commit SHA

```
d5b4a2462f5ad95e9f132006a8fd870dc098ebe3   (Stage 2 campaign)
98e6366c6e47                                  (Stage 1.1-B baseline)
```

Final closure commit will follow this document.

## 16. Final Result Files

| File | Type | Committed |
|------|------|-----------|
| research/raw/benchmark_seed_{42,123,456,789,1024}.json | Deterministic | Yes (after .gitignore fix) |
| research/raw/campaign_full.json | Summary | Yes |
| research/raw/granularity_experiment.json | Primary | Yes |
| research/raw/negative_controls.json | Control | Yes |
| research/raw/replay_convergence.json | Stability | Yes |
| research/raw/scalability.json | Performance | Yes |
| research/raw/real_llm_validation.json | Sanity | Yes |
| research/raw/claim_registry.json | Registry | Yes |
| research/raw/experiment_manifest.json | Manifest | Yes |
| research/figures/*.svg | Figures | Yes |
| research/figures/*.png | Figures | Yes |

## 17. Final Figure/Table Mapping

| Figure | Data Source | Claims Supported |
|--------|------------|-----------------|
| fig_attribution | benchmark_seed_42.json | — (descriptive) |
| fig_granularity | granularity_experiment.json | C1, C2 |
| fig_collateral | granularity_experiment.json | C2 |
| fig_convergence | replay_convergence.json | C6 (trivially) |
| fig_scalability | scalability.json | — (descriptive) |
| fig_negative_controls | negative_controls.json | C4 |
| fig_real_llm | real_llm_validation.json | C7 |

## 18. Integrity Statement

- No result was fabricated
- No result was selectively hidden
- Negative result C3 (A5 not significantly better than B1) is reported
- Replay convergence is correctly labeled as deterministic trivial result
- Real-LLM validation is correctly labeled as sanity check
- BF-F ground truth contradiction was corrected
- BF-H, BF-J, BF-K were relabeled to match actual implementation
- "t-test" references replaced with actual tests (permutation/Wilcoxon)
- claims.py validate() was rewritten to correctly parse actual data
- run_real_llm.py unused imports removed, accurately described
- Manifest commit SHA corrected from 98e6366 to d5b4a24
- Raw data un-gitignored for reproducibility
- CELA is NOT claimed to be universally superior
- No "first" claims are made without independent verification
- Real-LLM validation does NOT prove universal effectiveness
