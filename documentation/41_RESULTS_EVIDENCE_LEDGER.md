# Results Evidence Ledger

This ledger maps every scientific claim (C1-C7) to its underlying hypothesis, experiment, benchmark, raw file, metric, statistical test, effect size, and corresponding figure.

## Claim C1
- **Hypothesis:** Channel intervention provides more selective localization than source-event intervention.
- **Experiment:** Granularity
- **Benchmark:** BF-G (Shared source)
- **Raw File:** `granularity_experiment.json`
- **Metric:** `preserved_evidence`
- **Statistical Test:** Wilcoxon signed-rank
- **Figure:** `fig_granularity`

## Claim C2
- **Hypothesis:** Channel intervention preserves unrelated evidence.
- **Experiment:** Granularity
- **Benchmark:** BF-G (Shared source)
- **Raw File:** `granularity_experiment.json`
- **Metric:** `collateral_modification`
- **Statistical Test:** Wilcoxon signed-rank
- **Figure:** `fig_collateral`

## Claim C3 (NOT SUPPORTED)
- **Hypothesis:** CELA A5 achieves higher F1 than random baseline B1.
- **Experiment:** Benchmark
- **Benchmark:** All Families
- **Raw File:** `benchmark_seed_42.json`
- **Metric:** `causal_f1`
- **Statistical Test:** Permutation test
- **Figure:** `fig_attribution`

## Claim C4
- **Hypothesis:** Negative controls show CEE=0 for irrelevant channels.
- **Experiment:** Negative controls
- **Benchmark:** N/A (Control scenarios)
- **Raw File:** `negative_controls.json`
- **Metric:** `cee`
- **Statistical Test:** None (deterministic absolute)
- **Figure:** `fig_negative_controls`

## Claim C5
- **Hypothesis:** Results are stable across seeds.
- **Experiment:** Seed robustness
- **Benchmark:** All Families
- **Raw File:** `benchmark_seed_*.json`
- **Metric:** `variance`
- **Statistical Test:** Coefficient of variation (< 0.2)
- **Figure:** N/A

## Claim C6
- **Hypothesis:** CEE converges with replay count.
- **Experiment:** Convergence
- **Benchmark:** N/A
- **Raw File:** `replay_convergence.json`
- **Metric:** `cee`
- **Statistical Test:** Deterministic stability check (Trivially true)
- **Figure:** `fig_convergence`

## Claim C7
- **Hypothesis:** Real-LLM intervention produces non-zero CEE (sanity check).
- **Experiment:** Real-LLM
- **Benchmark:** N/A
- **Raw File:** `real_llm_validation.json`
- **Metric:** `cee`
- **Statistical Test:** None
- **Figure:** `fig_real_llm`
