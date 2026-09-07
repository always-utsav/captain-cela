# 05 SHARED-SOURCE VALIDATION

## Scenario Structure (BF-G)

```
data_source("ANSWER=42;STATUS=ok")
    ├── analyzer("42")     → channel A (CAUSAL — carries failure keyword)
    └── validator("ok")    → channel B (NON-CAUSAL — carries benign data)
```

## Evidence Flow Graph

| Evidence | Type | Source Event | Value |
|----------|------|-------------|-------|
| E1 | TOOL_OUTPUT | data_source result | ANSWER=42;STATUS=ok |
| E2 | TOOL_OUTPUT | analyzer result | 42 |
| E3 | TOOL_OUTPUT | validator result | ok |
| E4 | MODEL_OUTPUT | reasoning | The analyzer found 42... |
| E5 | TEXT | output | Result: 42, status ok. |

## Channel-Level Intervention Results

### Intervention on analyzer channel (causal)

| Metric | Value |
|--------|-------|
| CEE | **1.0** |
| Factual failed | True |
| CF failed | False |
| Validator "ok" in CF | **Yes** (preserved) |

The analyzer's tool result "42" is blocked → propagated to reasoning
and output → "42" removed → evaluator returns False → CEE = 1.0.

Validator's "ok" output SURVIVES because only the analyzer channel
was blocked.

### Intervention on validator channel (non-causal)

| Metric | Value |
|--------|-------|
| CEE | **0.0** |
| Factual failed | True |
| CF failed | True |

Blocking "ok" does not remove "42" → evaluator still finds keyword →
failure persists → CEE = 0.0.

### Intervention on data_source channel (non-causal)

| Metric | Value |
|--------|-------|
| CEE | **0.0** |
| Factual failed | True |
| CF failed | True |

The data_source result "ANSWER=42;STATUS=ok" is a composite string.
Blocking it removes "ANSWER=42;STATUS=ok" from LLM responses, but the
analyzer's own result "42" is a separate tool call that still provides
the failure keyword independently.

## Channel Isolation Verification

**Test:** After channel-level intervention on analyzer, does
validator output survive in the counterfactual?

**Result:** YES — "ok" found in counterfactual execution text.

## Acceptance Criteria D: PASS
Channel A intervention changes A's availability while preserving B.
