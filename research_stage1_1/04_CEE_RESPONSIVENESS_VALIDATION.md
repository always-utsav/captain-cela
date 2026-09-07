# 04 CEE RESPONSIVENESS VALIDATION

## BEFORE (Stage 1)

| Candidate | Type | CEE | CF Failed |
|-----------|------|-----|-----------|
| calculator (causal) | channel | 0.0 | True |
| echo (distractor) | channel | 0.0 | True |

**Problem:** CEE = 0 for ALL candidates because tool result override
did not propagate to LLM responses.

## AFTER (Stage 1.1)

### BF-A Single Cause (seed=42)

| Candidate | Type | CEE | CF Failed | Factual Failed |
|-----------|------|-----|-----------|----------------|
| calculator (causal) | channel | **1.0** | **False** | True |
| echo (distractor) | channel | **0.0** | True | True |

### Causal Chain Verification

**Factual execution:**
```
calculator → tool_result = "42"
echo → tool_result = "hello world"
reasoning = "The calculator says 42 and the echo says hello world"
output = "The answer is 42 and hello world."
evaluator("42" in output) → True (FAILURE)
```

**Counterfactual (calculator blocked):**
```
calculator → tool_result = "" (overridden)
echo → tool_result = "hello world" (preserved)
reasoning = "The calculator says  and the echo says hello world"  ← propagated
output = "The answer is  and hello world."  ← propagated
evaluator("42" in output) → False (SUCCESS)
```

**Counterfactual (echo blocked):**
```
calculator → tool_result = "42" (preserved)
echo → tool_result = "" (overridden)
reasoning = "The calculator says 42 and the echo says "  ← propagated
output = "The answer is 42 and ."  ← propagated
evaluator("42" in output) → True (FAILURE still — "42" remains)
```

### CEEEstimator Integration

```
CEEEstimator(num_trials=3)
  causal candidate: CEE = 1.0, CI = [1.0, 1.0]
```

### Acceptance Criteria A: PASS

Y_f (True) ≠ Y_cf (False) for causal intervention → CEE = 1.0 > 0
