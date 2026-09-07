# 02 BLOCKER B AUDIT — Step-vs-Channel Indistinguishability

## Problem Statement
In the Stage 1 reference agent, each tool call produces exactly ONE
result artifact. Step-level and channel-level interventions target the
same effective object. The two strategies are degenerate.

## Root Cause (traced through code)

### Agent execution structure (BEFORE fix)

```
Plan: [TOOL:calculator, TOOL:echo, Summarise]
      ↓
Step 0: calculator → tool_result (1 artifact) → memory_write
Step 1: echo → tool_result (1 artifact) → memory_write
Step 2: reasoning (reads all memory) → 1 artifact
Output: final output → 1 artifact
```

Each step produces exactly ONE output artifact. The evidence flow
graph has a linear chain:

```
calculator_result → reasoning → output
echo_result → reasoning → output
```

### Why step-level = channel-level

1. `channel_to_intervention` (estimator.py:182-230) targets the SOURCE
   evidence's producing event. For a tool result, this is the
   `tool_result` event.

2. `step_level_intervention` targets the MEDIATING event (the event
   that consumes the evidence). For a tool result consumed by reasoning,
   this is the `reasoning` event.

3. However, in BF-A through BF-F, each tool produces exactly 1 artifact
   consumed by exactly 1 downstream event (reasoning). Blocking the
   tool_result vs blocking the reasoning has the same NET effect on
   the keyword evaluator — "42" is present in BOTH events' output.

### What's needed

A scenario where ONE source event produces evidence feeding TWO
distinct downstream paths. Then:

- Channel-level intervention on path A blocks ONLY path A
- Step-level intervention on the source blocks BOTH paths A and B
- The two interventions produce observably different results

### Evidence flow graph requirement

```
            ┌── channel A → consumer A (carries failure keyword)
Source ────┤
            └── channel B → consumer B (carries benign data)
```

With this structure:
- `do(channel_A = empty)` → failure keyword removed, benign data preserved
- `do(source_step = disabled)` → BOTH channels blocked

## Conclusion
Create a shared-source benchmark scenario (BF-G) with branching
evidence channels from a single source.
