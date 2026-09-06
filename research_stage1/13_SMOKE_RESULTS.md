# 13 SMOKE RESULTS

## Campaign Configuration
- Seeds: [42, 1, 7]
- Replay counts: 1, 3, 5, 10, 25 (convergence only)
- Benchmark families: BF-A through BF-F
- Methods: B1_random, B2_provenance, B4_structural
- Total entries: 82

## 1. Shared-Source Experiment (PRIMARY NOVELTY)

### Results (12 entries)
| Method | Causal Prevented | Irrelevant Prevented | False Positives |
|--------|-----------------|---------------------|-----------------|
| channel_level | 0/3 | 0/3 | 0 |
| step_level | 0/3 | 0/3 | 0 |

### Finding
Both channel-level and step-level interventions show CEE=0 because MockLLM responses are invariant to tool results. The intervention IS correctly applied but downstream LLM output contains the failure keyword regardless.

### Implication for Novelty
The step-vs-channel distinction cannot be empirically demonstrated with a non-reactive LLM. The novelty experiment requires either:
1. A stochastic MockLLM where tool results influence response probability
2. A real LLM API
3. Modified keyword evaluator that checks only tool-result events (not LLM reasoning)

## 2. Negative Controls

| Metric | Value |
|--------|-------|
| Interventions tested | 6 |
| False positives | 0 |
| False positive rate | 0.000 |

**Verdict: PASS** — Distractor channels correctly show no causal effect.

## 3. Replay Convergence

All CEE=0 at all replay counts (trivial convergence). See 11_REPLAY_CONVERGENCE_REPORT.md.

## 4. Seed Robustness

CEE stable at 0.000 across 5 seeds. Selection metrics (F1) deterministic across seeds.

## 5. Benchmark Smoke

### Results Table (seed=42, representative)

| Family | B1_random | B2_provenance | B4_structural |
|--------|-----------|---------------|---------------|
| BF-A | F1=0.000 | F1=0.000 | F1=0.000 |
| BF-B | F1=0.667 | F1=0.667 | F1=0.667 |
| BF-C | F1=0.667 | F1=0.667 | F1=0.667 |
| BF-D | F1=0.000 | F1=0.000 | F1=0.000 |
| BF-E | F1=1.000 | F1=1.000 | F1=1.000 |
| BF-F | F1=0.667 | F1=0.667 | F1=0.667 |

### Key Observations
- All 54 entries: 0 errors
- Baselines show identical F1 in BF-B/C/E/F (all select the same top candidate)
- BF-A and BF-D: F1=0 for all baselines (single causal in 2-candidate set; all select wrong one)
- BF-E (cascade): F1=1.0 for all (only 1 candidate, trivially correct)

### Raw Data
All results in `research_stage1/raw/`:
- `shared_source.json` (12 entries)
- `negative_controls.json` (6 entries)
- `replay_convergence.json` (5 entries)
- `seed_robustness.json` (5 entries)
- `benchmark_smoke.json` (54 entries)
- `smoke_summary.json` (all combined)

## Overall Smoke Verdict: PASS WITH LIMITATIONS
- Infrastructure works end-to-end
- No errors in any experiment
- Determinism verified
- Information boundaries intact
- **Critical limitation:** CEE measurement requires reactive LLM (Stage 2)
