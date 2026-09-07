# 01 BLOCKER A AUDIT — MockLLM CEE Ceiling

## Problem Statement
CEE = 0 for ALL interventions because the MockLLMProvider replays
pre-scripted responses regardless of tool result changes.

## Root Cause (traced through code)

### Causal chain (BEFORE fix)

```
1. Scenario generator (scenarios.py:289-293)
   → Creates pre-scripted LLM responses containing failure keyword "42"
   → Calculator tool returns "Error: no expression provided" (NOT "42")
   → LLM response text does NOT match actual tool result

2. Replay engine _extract_baseline (engine.py:137-230)
   → Extracts LLM responses from baseline into `llm` list
   → llm = [plan_text, *reasoning_results, final_output]

3. Intervention applied _apply (engine.py:295-384)
   → TOOL_RESULT_OVERRIDE correctly puts new value in `ovr` dict
   → But `llm` list remains UNCHANGED (original pre-scripted responses)

4. Replay execution _run_replay (engine.py:482-512)
   → Creates MockLLMProvider with UNMODIFIED llm responses
   → MockLLMProvider.generate() (llm.py:71-75) IGNORES prompt input
   → Returns pre-scripted response containing "42" regardless of tool result

5. Evaluator _build_keyword_evaluator (scenarios.py:178-195)
   → Scans ALL event payloads + artifact values
   → Finds "42" in unchanged LLM reasoning/output events
   → Returns True (failure detected) for BOTH factual and counterfactual

6. CEE = P(Y=1) - P(Y=1|do) = 1 - 1 = 0
```

### Two independent failures

1. **Tool result mismatch**: Calculator tool receives no proper expression
   argument and returns "Error: no expression provided", but the LLM's
   scripted response claims "The calculator says 42". The tool result
   and LLM response are disconnected.

2. **MockLLM input-blindness**: MockLLMProvider.generate() ignores its
   prompt entirely (llm.py:71-75). Even if tool results changed, the
   LLM would produce the same output.

### Key code locations

| File | Line | Issue |
|------|------|-------|
| captain/adapters/llm.py | 71-75 | MockLLM ignores prompt |
| captain/replay/engine.py | 302 | `llm = list(data["llm"])` — copies baseline verbatim |
| captain/replay/engine.py | 339 | Tool override applied to `ovr`, NOT to `llm` |
| captain/replay/engine.py | 489 | MockLLM created with unmodified `llm` |
| captain/benchmarks/scenarios.py | 289-295 | Tool results don't match LLM responses |

## Conclusion
Two repairs required:
1. Make tool results match LLM responses (FixedValueTool)
2. Propagate tool result changes to downstream LLM responses
