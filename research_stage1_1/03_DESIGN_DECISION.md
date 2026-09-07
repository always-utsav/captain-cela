# 03 DESIGN DECISION

## Changes Made

### Change 1: FixedValueTool (Blocker A, part 1)

**File:** `captain/agent/tools.py`

**What:** Added `FixedValueTool` class — a Tool that always returns a
pre-configured value.

**Why:** The existing benchmark scenarios used `CalculatorTool` and
`EchoTool`, which return values that DON'T match the MockLLM's scripted
responses. Calculator returns "Error: no expression provided" while the
LLM says "The calculator says 42". This disconnect breaks the causal
chain: tool result → LLM reasoning → evaluator outcome.

**Alternative considered:** Fixing the Planner to pass correct arguments
to the calculator. Rejected because it would require complex changes to
the argument parsing system and wouldn't generalize to arbitrary
benchmark scenarios.

**Scientific justification:** The FixedValueTool establishes the genuine
causal dependency that a real LLM agent would have: the tool's output IS
the data that flows through reasoning to the final output. This is not
manufacturing results — it's making the synthetic agent behave like a
real agent where tool outputs matter.

---

### Change 2: Causal Propagation in Replay Engine (Blocker A, part 2)

**File:** `captain/replay/engine.py`

**What:** Added `_propagate_tool_overrides()` function and integrated it
into `_apply()`. When a TOOL_RESULT_OVERRIDE intervention changes a tool
result from `original` to `replacement`, the same substitution is applied
to all downstream LLM responses (reasoning and final output).

**Why:** MockLLMProvider ignores its input prompt. Without propagation,
the pre-scripted responses retain the original tool result text even
after intervention. A real LLM would incorporate tool results into its
reasoning — propagation simulates this dependency.

**What it does NOT change:**
- Does NOT change the CEE formula
- Does NOT change the evaluator
- Does NOT change the intervention model
- Does NOT inspect causal ground truth
- Does NOT know which interventions are "supposed to" work

**Mechanism:**
1. `_apply()` records `(original_text, replacement_text)` for each
   tool result override
2. After all interventions are processed, `_propagate_tool_overrides()`
   performs string substitution in `llm[1:]` (reasoning + final output)
3. The plan response `llm[0]` is NOT modified (generated before tools)

**Alternative considered:** Creating a new `ToolResultAwareMockLLM`
subclass. Rejected as unnecessarily complex — string substitution in
the replay engine achieves the same effect with less code.

---

### Change 3: Scenario Generator Updates (Blocker A, part 1 applied)

**File:** `captain/benchmarks/scenarios.py`

**What:** All 6 existing scenario generators (BF-A through BF-F) updated
to use `FixedValueTool` registries so tool results match the LLM's
scripted responses.

**Changes per scenario:**
| Family | Tool | Returns |
|--------|------|---------|
| BF-A | calculator → "42", echo → "hello world" |
| BF-B | calculator → "42", echo → "hello world" |
| BF-C | calculator → "42", echo → "hello world" |
| BF-D | calculator → "42", echo → "greeting", timestamp → "now" |
| BF-E | calculator → "42" |
| BF-F | calculator → "42", echo → "hello world" |

---

### Change 4: Shared-Source Scenario BF-G (Blocker B)

**File:** `captain/benchmarks/scenarios.py`

**What:** Added `generate_shared_source()` — a new benchmark scenario
where ONE source tool produces composite data consumed by TWO downstream
tools via distinct channels.

**Structure:**
```
data_source("ANSWER=42;STATUS=ok")
    ├── analyzer("42")     → channel A (CAUSAL)
    └── validator("ok")    → channel B (NON-CAUSAL)
```

**How it creates distinct channels:**
- `data_source` returns composite result
- `analyzer` returns the failure keyword (channel A)
- `validator` returns benign status (channel B)
- Channel-level intervention on analyzer blocks A, preserves B
- Step-level intervention on data_source blocks both A and B

**Hidden causal truth:** analyzer channels are causal; validator and
data_source channels are non-causal. Truth is used ONLY by the post-hoc
metric evaluator, never by CELA.

## What Was NOT Changed

- CEE formula: CEE(e) = P(Y=1) - P(Y=1 | do(C_e = empty))
- Evaluator logic: still checks keyword presence in run output text
- Evidence flow graph semantics
- Intervention model
- Counterfactual replay semantics
- Joint intervention semantics
- Existing baseline definitions (B1-B4)
- Statistical methodology
- Any existing test
