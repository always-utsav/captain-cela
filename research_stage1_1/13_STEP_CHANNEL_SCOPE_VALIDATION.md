# 13 Step-Channel Scope Validation

## Three-Way Experiment Results

### CONDITION 1: Factual

| Property | Value |
|----------|-------|
| A present | Yes |
| B present | Yes |
| Failure | True |
| CEE | - |

Source event executed normally. Both artifacts available.
"42" and "ok" appear in reasoning and output.
Evaluator finds "42" in output text -> failure.

### CONDITION 2: Channel-A Intervention

| Property | Value |
|----------|-------|
| Intervention type | ARTIFACT_REPLACEMENT |
| Target | artifact_A (value="42") |
| Multi-artifact source | True |
| A present | **No** |
| B present | **Yes** |
| Failure | False |
| CEE | **1.0** |
| Affected evidence | [evi_A] |
| Preserved evidence | [evi_B] |

Only artifact_A's value was replaced with "".
Propagation substituted "42" -> "" in LLM responses.
artifact_B's value "ok" was NOT affected.
Evaluator no longer finds "42" -> no failure.

### CONDITION 3: Source-Step Intervention

| Property | Value |
|----------|-------|
| Intervention type | TOOL_RESULT_OVERRIDE |
| Target | TOOL_RESULT event (whole event) |
| A present | **No** |
| B present | **No** |
| Failure | False |
| Affected evidence | [evi_A, evi_B] |
| Preserved evidence | [] |

The entire TOOL_RESULT event was overridden.
Propagation substituted BOTH "42" -> "" AND "ok" -> "" in LLM responses.
Both artifacts' text removed from downstream reasoning and output.

## Summary Table

| Condition | A | B | Failure | CEE |
|-----------|---|---|---------|-----|
| Factual | Y | Y | True | - |
| Channel A block | N | Y | False | 1.0 |
| Source-step block | N | N | False | - |

## Scope Distinction

```
Channel-A affected:   1 evidence node  (evi_A)
Source-step affected: 2 evidence nodes (evi_A + evi_B)

Channel-A preserves B:   YES
Source-step preserves B:  NO

Scope(channel_A) SUBSET_OF Scope(source_step)
```

This is an EMPIRICAL demonstration, not merely structural:
- The actual counterfactual execution text was inspected
- B's value "ok" was verified PRESENT after channel-A intervention
- B's value "ok" was verified ABSENT after source-step intervention
- The scope difference is observable in the execution output

## Leakage Checks

| Property | Clean? |
|----------|--------|
| Evaluator uses intervention_id | No |
| Evaluator uses ground_truth | No |
| Evaluator uses is_counterfactual | No |
| Evaluator uses candidate ranking | No |
| Propagation uses ground truth | No |

## Reproducibility

| Trial | CEE |
|-------|-----|
| 1 | 1.0 |
| 2 | 1.0 |
| 3 | 1.0 |

All identical.

## Remaining Limitations

1. **String substitution scope**: Source-step propagation splits the
   multi-output string by MULTI_OUTPUT_SEPARATOR and substitutes each
   part independently. If a part appears elsewhere in unrelated text,
   it would be substituted there too. Mitigated by using distinct
   failure keywords.

2. **MockLLM still ignores input**: The propagation works around
   MockLLM's input-blindness. A real LLM would naturally incorporate
   only the available tool outputs.

3. **Binary CEE**: With deterministic MockLLM, CEE is always 0.0 or
   1.0. Continuous effects require stochastic replays (Stage 2).
