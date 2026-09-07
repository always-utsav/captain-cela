# 07 LEAKAGE RECHECK

## Evaluator Independence

The evaluator function `_build_keyword_evaluator` (scenarios.py:168-197)
takes ONLY an `ExecutionRun` and checks for keyword presence in the
concatenated output text. It does NOT access:

| Information | Accessed? | Evidence |
|-------------|-----------|----------|
| Intervention identity | NO | Source inspection confirms no `intervention` param |
| Hidden causal mechanism | NO | No `ground_truth` or `mechanism` access |
| Expected answer | NO | No `expected_outcome` or similar |
| CELA candidate ranking | NO | No `candidates` param |
| Factual/counterfactual label | NO | No `is_counterfactual` check |

## Causal Propagation Independence

The `_propagate_tool_overrides` function (engine.py) performs string
substitution based ONLY on:
- Original tool result text (from the baseline event payload)
- Replacement text (from the intervention)

It does NOT use:
- Causal ground truth
- Which interventions are "supposed to" work
- Evaluator logic or keyword lists
- Candidate classifications

## FixedValueTool Independence

`FixedValueTool.execute()` returns a pre-configured value. It does NOT:
- Know whether it's in a factual or counterfactual run
- Access ground truth
- Check intervention identity
- Communicate with the evaluator

## Negative Control Confirmation

Distractor interventions produce CEE = 0.0, confirming the propagation
does NOT make every intervention causally effective.

| Scenario | Distractor | CEE |
|----------|-----------|-----|
| BF-A | echo | 0.0 |
| BF-D | echo, timestamp | 0.0 |
| BF-G | validator, data_source | 0.0 |

## Acceptance Criteria C: PASS
No evaluator leakage detected.
