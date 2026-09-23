# Comparison Protocol: CAPTAIN/CELA vs Competitor Systems

## Classification of Competitors

### DIRECTLY REPRODUCIBLE
*None* — No competitor system provides a publicly available codebase
with compatible interfaces, data models, and evaluation protocols
that would allow running on CAPTAIN's benchmark scenarios.

### PARTIALLY REPRODUCIBLE
- **CAR (Causal Agent Replay)**: If code becomes available, step-level
  do() interventions could be compared on identical scenarios by
  mapping CAPTAIN scenarios to CAR's input format.

### CONCEPTUALLY COMPARABLE
- **Who&When Pro**: Different evaluation philosophy (trajectory-scale
  coverage vs controlled mechanism coverage). Attribution accuracy
  metrics are comparable if same failure annotation scheme is used.
- **CausalFlow**: Step-level CRS could be compared if scenarios are
  adapted to CausalFlow's input format.
- **From Spark to Fire**: Cascade modeling is conceptually similar but
  operates on text-only multi-agent systems.
- **AgenticRAG-FP**: Hop-level propagation is comparable for RAG-like
  scenarios only.

### NOT REPRODUCIBLE
- **AgenTracer**: Requires fine-tuned 8B tracer model.
- **RAFFLES**: Requires LLM-as-judge infrastructure.
- **SAFARI**: Requires specific tool-augmented search setup.
- **Oat**: Requires Neural CDE training on normal dynamics.
- **AgentProcessBench**: Human-verified labels not transferable.
- **DoVer**: Task-specific segment replay.

## Why Direct Comparison is Limited

1. **Different evaluation units**: CAPTAIN evaluates evidence-channel
   interventions; most competitors evaluate step-level attributions.
2. **Different ground truth**: CAPTAIN uses machine-readable
   CausalMechanismSpec; competitors use human annotations or
   task completion signals.
3. **Different replay**: CAPTAIN uses paired factual/counterfactual
   replay; most competitors use single-pass evaluation.
4. **No public code**: Most competitor systems do not release code
   compatible with external benchmarks.

## Fair Internal Comparison

Within CAPTAIN, the following fair comparisons are executed:

| Comparison | Methods | Fair? | Reason |
|-----------|---------|-------|--------|
| Random vs CELA | B1 vs A5 | Yes | Same scenarios, same evaluator, same info |
| Provenance vs CEE | B2 vs B3 | Yes | Same scenarios, no hidden info |
| Channel vs Source-event | ARTIFACT_REPLACEMENT vs TOOL_RESULT_OVERRIDE | Yes | Same factual execution, same evaluator |
| Individual vs Cascade | A3 vs A4 | Yes | Same candidate set, same budget |
| Any method vs Oracle | Any vs B5 | Yes | Oracle uses POST-HOC ground truth only |

## Comparison Dimensions

| Dimension | CAPTAIN/CELA | Who&When Pro | CAR | CausalFlow |
|-----------|-------------|-------------|-----|-----------|
| Evaluation unit | Evidence channel | Trajectory step | Decision step | Failure step |
| Scale | 275 controlled | 12K+ trajectories | Varies | Varies |
| Scale purpose | Mechanism coverage | Trajectory coverage | Task coverage | Task coverage |
| Ground truth | Machine-readable spec | Human annotation | Environment reset | Task completion |
| Intervention | Channel-level | None | Step-level do() | Step-level |
| Replay | Paired counterfactual | None | Stochastic forward | Deterministic |
| Causal estimator | CEE | None | Shapley | CRS |
| Cascade | Yes | No | No | No |
| Multimodal | Yes | Text only | Limited | Limited |

> **Note**: Counts across systems are not directly comparable because
> evaluation units and objectives differ. 275 controlled mechanism
> instances serve a fundamentally different scientific purpose than
> 12,326 trajectory-scale annotations.
