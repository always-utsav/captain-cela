# 08 EXPERIMENT MANIFEST SCHEMA

## Machine-Readable Manifest Fields

```json
{
  "experiment_id": "string — unique experiment identifier",
  "scenario_id": "string — benchmark scenario ID",
  "benchmark_family": "string — BF-A through BF-F",
  "method": "string — method name (B1-B5, A1-A5, step_level, channel_level)",
  "intervention_granularity": "string — 'channel' or 'step'",
  "seed": "int — master random seed",
  "replay_count": "int — number of paired replay trials",
  "candidate_count": "int — number of candidate interventions",
  "pathway_count": "int — number of evidence-flow pathways",
  "budget": "float | null — intervention budget constraint",
  "lambda": "float — cost penalty weight",
  "code_version": "string — git commit SHA",
  "benchmark_version": "string — scenario generator version",
  "timestamp": "string — ISO 8601 execution timestamp",
  "environment": {
    "python": "string",
    "os": "string",
    "pydantic": "string"
  },
  "outcome": {
    "factual_failed": "bool",
    "counterfactual_failed": "bool | null",
    "cee": "float",
    "ci_lower": "float",
    "ci_upper": "float",
    "prevented": "bool",
    "f1": "float | null",
    "recall_at_1": "float | null",
    "precision": "float | null"
  },
  "failure_status": "string — success | expected_failure | unexpected_failure | invalid_intervention | replay_divergence | timeout | evaluator_error",
  "error": "string | null"
}
```

## Critical Constraint

Hidden causal labels (causal_channel_ids, required_prevention_sets) MUST NOT appear in method-visible inputs. They exist ONLY in ground_truth, used by MetricEvaluator post-hoc.

## Raw Result Location

All raw results stored in `research_stage1/raw/` as JSON files, one per experiment type.
