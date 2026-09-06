# Experiments

**Stage 17: Statistical validation implemented.**

---

## Experimental Hierarchy

```
Experiment
  → benchmark family (BF-A..BF-F)
    → scenario instance (independent experimental unit)
      → method/configuration (B1-B5, A1-A5)
        → intervention evaluation
          → replay/trial
```

The scenario instance is the primary independent experimental unit.
Repeated replays within one scenario are NOT independent samples.

---

## Benchmark Families (Stage 16)

| Family | Mechanism | Key Property |
|--------|-----------|--------------|
| BF-A | Single-cause | 1 causal, 1 irrelevant |
| BF-B | Redundant (OR) | Both causal, both needed to prevent |
| BF-C | Complementary (AND) | Either alone prevents |
| BF-D | Distractor | 1 causal, 2 irrelevant |
| BF-E | Cascade | Origin → propagation chain |
| BF-F | Cost-asymmetric | Budget forces cheap selection |

Hidden CausalMechanismSpec never exposed to methods.

---

## Methods Compared

### Baselines (B1-B5)

| # | Method | Uses Replay | Uses Cost |
|---|--------|:-----------:|:---------:|
| B1 | Random (5 deterministic draws) | No | No |
| B2 | Provenance-only (screening score) | No | No |
| B3 | CEE-Rank (individual CEE) | Yes | No |
| B4 | Graph-structural (distance) | No | No |
| B5 | Cost-aware structural | No | Yes |

### CELA Configurations (A1-A5)

| Config | Procedure | Notes |
|--------|-----------|-------|
| A1 | Provenance-only | = B2 by construction |
| A2 | Individual CEE rank | = B3 by construction |
| A3 | Restricted subset evaluation | NOT exhaustive |
| A4 | GreedyCascadeSelector (λ=0) | NOT exhaustive |
| A5 | Full CELA (cost + budget) | Cost-aware |

A1=B2 and A2=B3 documented, not double-counted.

---

## Primary Outcomes (Never Collapsed)

### 1. Attribution
- Causal precision, recall, F1
- Recall@1, Recall@K

### 2. Intervention Effectiveness
- Failure prevention rate
- Prevention-set recovery
- CEE(S)

### 3. Intervention Efficiency
- Intervention cost
- Set size
- Replay/evaluation count

---

## Secondary Outcomes

- Localization recall (origin, propagation, actuator)
- Distractor false-selection rate (DFSR)
- Redundancy group coverage
- Complementary group recovery rate
- Utility
- Budget feasibility
- Oracle regret / optimality gap
- Computational cost

---

## Statistical Protocol (Stage 17)

### Confidence Intervals
- Bootstrap percentile CI across independent scenario instances
- Default: 2000 resamples, deterministic seed, 95% CI
- Insufficient samples (n < 3): explicit `sufficient=False` status

### Paired Comparisons
- Wilcoxon signed-rank for continuous metrics
- Paired permutation test for binary/bounded metrics
- Automatic selection based on metric cardinality
- Minimum 3 paired observations required

### Multiple Comparison Correction
- Holm-Bonferroni applied to all simultaneous tests
- Records: raw p-value, adjusted p-value, correction method, alpha

### Effect Sizes
- Paired Cohen's d = mean(diffs) / std(diffs)
- Reported alongside p-values
- Metrics without meaningful standardized effect size are documented

### Ablation Analysis
- A1→A2→A3→A4→A5 ladder
- Per-step delta with paired statistical comparison
- Identifies where performance changes occur

### Sensitivity Analysis
- Coefficient of variation across parameter values
- Stability threshold: CV < 0.2 considered stable
- Parameters tested: seed, family, candidate count, budget, λ, max-set-size

---

## Failure Accounting

Every experiment classifies outcomes:

| Classification | Meaning |
|---------------|---------|
| successful | Normal execution and evaluation |
| replay_failure | Counterfactual replay error |
| unsupported_intervention | Intervention type not supported |
| evaluator_failure | Failure evaluator error |
| insufficient_candidates | Not enough candidates for method |
| invalid_scenario | Scenario generation error |
| budget_exhausted | Computation budget exceeded |

Infrastructure failure NEVER becomes "causal failure."

---

## Reproducibility

- Deterministic master seed → instance seeds
- Instance seed = master_seed * 10000 + family_offset + i
- All configuration recorded in ExperimentConfig
- ReproducibilityMetadata: experiment_id, timestamps, config, counts
- Results fully JSON-serializable via Pydantic

---

## Scientific Caution

Stage 17 results do NOT automatically claim "CELA is superior."
They report evidence from which conclusions may or may not follow.

If CELA loses on benchmark families, that result is preserved and reported.

Performance figures are local deterministic benchmark targets,
not population-level guarantees.

---

## Stage 18 Boundary

Stage 18 is reserved for:
- Explorer integration with experiment results
- Publication-oriented visualization
- End-to-end reproducibility demo
- Final project documentation
