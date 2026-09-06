# Algorithms

**Stage 11 Research Lock: Algorithm specifications frozen.**

No novel CAPTAIN/CELA research algorithm has been implemented.
This document specifies the planned algorithms for future stages.

---

## Implemented Infrastructure Algorithms (Stages 0–10)

### Graph Construction (Stage 6)

`ExecutionGraphBuilder.build(run)` constructs an `ExecutionGraph`
from an `ExecutionRun` by:

1. Extracting provenance relationships via `ProvenanceExtractor`
2. Creating EVENT nodes (one per `Event`)
3. Creating ARTIFACT nodes (one per `Artifact`)
4. Creating edges: PRODUCED (event→artifact), CONSUMED
   (artifact→event), DERIVED (artifact→artifact)
5. Deterministic ordering by sequence number

### Graph Analysis (Stage 7)

`GraphAnalyzer` provides structural analysis:

- Degree computation (in, out, total)
- Root/leaf/isolated node identification
- Upstream/downstream reachability (BFS, cycle-safe)
- Event execution ordering (by sequence number)
- Structural event-to-event paths (through artifacts)

`GraphValidator` checks structural integrity:

- Adjacency consistency
- Edge reference validity
- Type combination validity
- Self-loop detection
- Sequence number ordering
- Isolated node detection

### Intervention Validation (Stage 9)

`InterventionValidator.validate(intervention, run)` checks:

- Target ID format (art_/evt_ prefix)
- Target existence in baseline run
- Type-specific constraints (e.g., TOOL_RESULT_OVERRIDE
  requires TOOL_RESULT event type)
- Replacement value presence
- InterventionSet consistency (duplicate targets, baseline
  mismatch)

### Counterfactual Replay (Stage 10)

`CounterfactualReplayEngine.replay(run, intervention)`:

1. Validate intervention against baseline
2. Extract baseline execution data (LLM responses, tool
   results, plan structure)
3. Apply interventions (modify LLM responses, wrap tools,
   change task text)
4. Re-execute via fresh TracedAgent
5. Link counterfactual to baseline via parent_run_id

---

## Planned CELA Research Algorithms (Stages 12–17)

### Evidence-Flow Graph Construction (Stage 12)

*PLANNED — not implemented.*

Build an evidence-flow graph from:
- Existing `ExecutionGraph` (structural connections)
- `ProvenanceExtractor` relationships (PRODUCED, CONSUMED,
  DERIVED)
- Evidence ontology classification

Algorithm:
1. Map each `Artifact` to an evidence type (ontology)
2. Map each provenance relationship to an evidence-flow edge
3. Annotate edges with producing event and channel type
4. Support temporal indexing for recurrent execution
5. Preserve hard provenance as primary lineage mechanism

### Candidate Screening (Stage 13)

*PLANNED — not implemented.*

Identify failure-relevant evidence-flow edges:
1. Trace upstream from failure-manifesting events
2. Identify all evidence channels on upstream paths
3. Filter by relevance heuristics (configurable)
4. Produce candidate set `E_F`

### CEE Estimation (Stage 14)

*PLANNED — not implemented.*

For each candidate channel `e`:
1. Construct channel-specific intervention
2. Execute paired counterfactual replay (N times)
3. Compute paired estimator:
   `CEE_hat(e) = (1/N) Σ_r [Y_r − Y_r^cf]`
4. Compute confidence interval
5. Apply multiple-testing correction

### Propagation Profile (Stage 14)

*PLANNED — not implemented.*

For a lineage path `L = (e_1, ..., e_k)`:
1. Compute `CEE(e_i)` for each edge
2. Construct profile vector `Π(L) = [CEE(e_1), ..., CEE(e_k)]`
3. Identify bottleneck: `e* = argmax CEE(e)`

This is a diagnostic representation, not a novel causal
estimand.

### Greedy Cascade Intervention (Stage 15)

*IMPLEMENTED — `captain.analysis.cascade.GreedyCascadeSelector`*

```
S <- {}
evaluations <- 0
while |S| < max_set_size and candidates remaining and evaluations < max_evaluations:
    for each candidate e not in S:
        if budget is set and Cost(S) + cost(e) > budget: skip
        estimate CEE(S U {e}) via REAL joint replay
        D(e|S) = CEE(S U {e}) - CEE(S)
    if lambda_cost > 0:
        e* <- argmax_{e} [D(e|S) - lambda * cost(e)]  (utility mode)
    else:
        e* <- argmax_{e} D(e|S)  (budget/CEE mode)
    if no e* with positive gain: break
    S <- S U {e*}
    if failure prevented (evaluator-confirmed): return S
return S
```

**Tie-breaking**: lower cost, then lexicographic intervention ID.

**CEE(S) is NOT Sum CEE(e)**: Each set-level estimate requires a real
joint counterfactual replay with all channels blocked simultaneously.

Result is a GREEDY approximation. Global optimality is NOT claimed.

### Baseline Comparison (Stage 16)

*PLANNED — not implemented.*

For each baseline method (B1–B7):
1. Apply baseline attribution to same failure scenarios
2. Compare localization accuracy against ground truth
3. Compare intervention effectiveness
4. Statistical significance testing

### Ablation Analysis (Stage 17 -- IMPLEMENTED)

A1→A5 ladder analysis via `compute_ablation_ladder()`:

1. A1 (provenance structure) → A2 (individual counterfactual attribution)
2. A2 → A3 (joint CEE / restricted subset)
3. A3 → A4 (greedy cascade optimization)
4. A4 → A5 (cost/utility optimization)

Per-step: delta, paired statistical comparison (Wilcoxon/permutation).

---

### Statistical Validation (Stage 17 -- IMPLEMENTED)

**Bootstrap CI**: `bootstrap_ci(metric, values, n_bootstrap=2000, seed=42)`
- Percentile method, deterministic seed
- Returns `sufficient=False` when n < min_samples

**Paired Comparisons**: `paired_comparison(method_a, method_b, metric, vals_a, vals_b)`
- Auto-selects: Wilcoxon (continuous), permutation (binary/bounded)
- Normal approximation for Wilcoxon signed-rank

**Multiple Comparison Correction**: `holm_bonferroni(results, alpha=0.05)`
- Monotonic adjusted p-values

**Effect Size**: Paired Cohen's d = mean(diffs) / std(diffs)

**Sensitivity**: Coefficient of variation across parameter values
