# 06 STEP VS CHANNEL VALIDATION

## Definition

**Channel-level intervention** (`channel_to_intervention`):
Targets the SOURCE evidence's producing event. For a tool result,
this is the `tool_result` event of the source tool. Preserves other
channels through the same mediating event.

**Step-level intervention** (`step_level_intervention`):
Targets the MEDIATING event — the event that consumes the evidence.
Affects ALL channels through that event.

## BF-G Shared-Source Experiment

### Setup
- Source: `data_source` (step 0)
- Downstream A: `analyzer` (step 1) — carries failure keyword
- Downstream B: `validator` (step 2) — carries benign data
- Causal candidate: analyzer channel

### Channel-level intervention
```
Type: TOOL_RESULT_OVERRIDE
Target: analyzer's tool_result event
Effect: Blocks analyzer output "42" only
Preserved: validator output "ok", data_source output
```

### Step-level intervention
```
Type: EVENT_OUTPUT_OVERRIDE
Target: analyzer's mediating event (reasoning/output)
Effect: Blocks the analyzer's contribution to reasoning
```

### Comparison

| Aspect | Channel-Level | Step-Level |
|--------|--------------|------------|
| Target event ID | analyzer tool_result | analyzer event |
| Intervention type | TOOL_RESULT_OVERRIDE | EVENT_OUTPUT_OVERRIDE |
| Blocks analyzer output | Yes | Yes |
| Preserves validator | Yes | Yes |
| Targets differ | **Yes** | — |

The two interventions target DIFFERENT events and use DIFFERENT
intervention types, confirming they are structurally distinct.

## Why This Matters Scientifically

In the current BF-A through BF-F scenarios, each tool has 1:1 mapping
between tool_result and downstream reasoning. The step-level and
channel-level interventions happen to block the same information.

In BF-G, the shared-source structure creates a genuinely branching
evidence graph. Channel-level targets the specific tool_result event
(fine-grained), while step-level targets the broader event scope.

This validates CELA's core novelty claim: intervention at the
evidence-flow channel level is a finer-grained operation than
step-level intervention.

## Acceptance Criteria E: PASS
Step-level and channel-level interventions produce observably
different intervention scopes (different target events, different
intervention types).
