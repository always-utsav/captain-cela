# FINAL CLOSURE AUDIT — CAPTAIN/CELA Stage 2

**Date**: 2026-09-22
**Auditor**: Systematic code+data+document audit

---

## 1. Current Repository HEAD

```
d5b4a2462f5ad95e9f132006a8fd870dc098ebe3
```

## 2. Stage 1.1-B Commit

```
98e6366c6e47
```

## 3. Stage 2 Commit

```
d5b4a2462f5ad95e9f132006a8fd870dc098ebe3
```

## 4. Experiments Actually Executable

| Experiment | Method in campaign.py | Executable? |
|---|---|---|
| Benchmark campaign (5 seeds x 11 families) | `run_benchmark_campaign()` | YES |
| Granularity (channel vs source-event) | `run_granularity_experiment()` | YES |
| Negative controls | `run_negative_controls()` | YES |
| Replay convergence | `run_replay_convergence()` | YES |
| Scalability | `run_scalability()` | YES |
| Pathway stress | NO METHOD EXISTS | NO |
| Cascade/joint intervention | NO METHOD EXISTS | NO |
| Cost/utility sweep | NO METHOD EXISTS | NO |
| Real-LLM validation | `run_real_llm.py` (separate) | YES |

## 5. Experiments Actually Executed

| Experiment | Status | Result File |
|---|---|---|
| Benchmark campaign (5 seeds) | EXECUTED | benchmark_seed_{42,123,456,789,1024}.json |
| Granularity (5 instances, BF-G) | EXECUTED | granularity_experiment.json |
| Negative controls (4 controls) | EXECUTED | negative_controls.json |
| Replay convergence (6 points) | EXECUTED | replay_convergence.json |
| Scalability (4 families) | EXECUTED | scalability.json |
| Real-LLM validation (Gemini) | EXECUTED | real_llm_validation.json |
| Pathway stress | NOT EXECUTED | no file |
| Cascade/joint intervention | NOT EXECUTED | no file |
| Cost/utility sweep | NOT EXECUTED | no file |

## 6. Result Files Actually Present

| File | Size | Present in Git? |
|---|---|---|
| research/raw/benchmark_seed_42.json | 2424.8 KB | NO (gitignored) |
| research/raw/benchmark_seed_123.json | 2425.4 KB | NO (gitignored) |
| research/raw/benchmark_seed_456.json | 2424.8 KB | NO (gitignored) |
| research/raw/benchmark_seed_789.json | 2425.6 KB | NO (gitignored) |
| research/raw/benchmark_seed_1024.json | 2425.9 KB | NO (gitignored) |
| research/raw/campaign_full.json | 11.4 KB | NO (gitignored) |
| research/raw/claim_registry.json | 2.7 KB | NO (gitignored) |
| research/raw/experiment_manifest.json | 1.8 KB | NO (gitignored) |
| research/raw/granularity_experiment.json | 5.4 KB | NO (gitignored) |
| research/raw/negative_controls.json | 1.3 KB | NO (gitignored) |
| research/raw/real_llm_validation.json | 7.0 KB | NO (gitignored) |
| research/raw/replay_convergence.json | 0.9 KB | NO (gitignored) |
| research/raw/scalability.json | 0.4 KB | NO (gitignored) |
| research/figures/*.svg | ~14 files | YES (committed) |
| research/figures/*.png | ~7 files | YES (committed) |

**CRITICAL**: All raw research data is gitignored and exists only on local disk.

## 7. Claims Currently Documented

| ID | Statement | Claimed Test | Actual Status |
|---|---|---|---|
| C1 | Channel more selective than source-event | t-test | mixed |
| C2 | Channel preserves unrelated evidence | t-test | mixed |
| C3 | A5 > B1 F1 | t-test | pending |
| C4 | Negative controls CEE=0 | none | mixed |
| C5 | Seed stability | variance_test | supported (WILDCARD BYPASS) |
| C6 | CEE convergence | convergence_test | mixed |
| C7 | Real-LLM CEE > 0 | none | pending |

## 8. Claims Actually Supported by Evidence

| ID | Actually Supported? | Reason |
|---|---|---|
| C1 | YES (data supports) | Granularity data shows channel affects 1, source-event affects 2 |
| C2 | YES (data supports) | Channel collateral=0, source-event collateral=1 |
| C3 | CANNOT VERIFY | validate() crashed on data format mismatch |
| C4 | YES (data supports) | All 4 negative controls have observed_cee=0.0 |
| C5 | UNKNOWN | Marked supported via wildcard bypass without any computation |
| C6 | TRIVIALLY TRUE | Deterministic MockLLM gives CEE=1.0 at all replay counts |
| C7 | YES (data supports) | channel_cee=0.40 in real_llm_validation.json |

## 9. Documentation/Code Mismatches

### CRITICAL

1. **Manifest commit SHA wrong**: `98e6366c6e47` (Stage 1.1-B) instead of `d5b4a24` (Stage 2)
2. **claims.py says "t-test"**: statistics.py implements permutation test + Wilcoxon, NOT t-test
3. **claims.py validate() broken**: Data format assumptions wrong for every claim except C5 (which uses wildcard bypass)
4. **Three campaign experiments documented but not implemented**: pathway_stress, cascade, cost_utility have fields in CampaignConfig and CampaignResult but no methods in CampaignRunner
5. **run_real_llm.py misleading**: Imports CAPTAIN infrastructure (Agent, TracedAgent, CounterfactualReplayEngine, etc.) but uses NONE of it. Sends hardcoded prompts to Gemini API.
6. **BF-H labeled "branching"**: Actual evidence graph topology is convergent (3 tools feeding one summary)
7. **BF-J "root vs symptom"**: Calculator and processor are parallel fixed mocks; intervening on root doesn't prevent failure because processor still emits "42"
8. **BF-K "downstream repair"**: fixer tool performs no actual repair; structurally identical to a distractor
9. **BF-F ground truth contradictory**: OR evaluator + claim that single cheap intervention prevents failure = impossible
10. **Replay convergence called "convergence"**: MockLLM is deterministic, CEE=1.0 at every point, CI width=0.0. This is a tautology, not convergence evidence.
11. **Granularity comparison called "source-event-level" in some docs but not a genuine "step-level" baseline**: The source-event intervention overrides the TOOL_RESULT_OVERRIDE for the data_source tool. This is accurate as "source-event-level" but must NOT be called "step-level".

### MODERATE

12. **Website hardcodes narrative claims** in Story Mode ("proving causality at the channel level") and Simple Mode
13. **Figures committed but raw data not committed**: Figures are in git, but the data they were generated from is gitignored
14. **A1 equiv B2, A2 equiv B3**: documented in code but not prominently in research docs
15. **Granularity experiment hardcodes "42" and "ok"**: appropriate for controlled experiment but should be documented

## 10. Reproducibility Problems

1. All raw result JSON files are gitignored — results exist only on local disk
2. Real-LLM results depend on Gemini API access + specific model availability (gemini-3.6-flash)
3. Manifest references wrong commit
4. No documented exact command to regenerate all results
5. claim_registry.json generated by broken validate() code

## 11. Required Corrections

### MUST FIX (scientific integrity)

1. Fix manifest commit SHA to d5b4a24
2. Replace all "t-test" references with actual test names (permutation/Wilcoxon)
3. Rewrite claims.py validate() to correctly parse actual data formats
4. Remove unused imports from run_real_llm.py; relabel as "controlled real-LLM intervention sanity check"
5. Fix BF-F ground truth (change keyword_logic to "all" OR document the contradiction)
6. Relabel BF-H from "branching" to its actual topology
7. Fix BF-J ground truth or relabel to "parallel causal sources"
8. Relabel BF-K from "downstream repair" to "downstream persistence"
9. Relabel replay convergence as "deterministic replay stability verification"
10. Remove pathway_stress, cascade, cost_utility fields from CampaignResult or clearly mark as "not executed"
11. Commit raw data to git (un-gitignore research/raw/) OR create reproducibility commands
12. Update all 24 research_stage2 documents for consistency

### SHOULD FIX

13. Remove hardcoded claims from website
14. Update README and CURRENT_STATE.md

## 12. Explicit List of Things That Will NOT Be Changed

1. Core CELA mathematical framework (CEE formula, replay engine, evidence graph)
2. Architecture of captain/ package
3. Existing test suite
4. Stage numbering (no Stage 19)
5. BF-A through BF-E and BF-G generators (correct as-is)
6. BF-I generator (correct as-is)
7. Statistical machinery in statistics.py (correct implementation)
8. Actual experiment results (no fabrication)
9. CEEEstimator or CascadeEstimator internals
10. InterventionType enum or Intervention model
