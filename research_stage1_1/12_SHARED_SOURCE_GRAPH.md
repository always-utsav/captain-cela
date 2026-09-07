# 12 Shared-Source Evidence-Flow Graph

## Source Event Structure

```
data_source TOOL_CALL (evt_fd39b20c...)
    |
    v
data_source TOOL_RESULT (evt_c87340c4...)
    |
    +-- output_artifact_ids:
    |       artifact_A (art_a792..., value="42")
    |       artifact_B (art_0869..., value="ok")
    |
    +-- Both artifacts have:
            producer_event_id = evt_fd39b20c... (TOOL_CALL)
```

## Provenance Records

| Artifact | Event | Relationship |
|----------|-------|-------------|
| artifact_A | data_source TOOL_RESULT | PRODUCED |
| artifact_B | data_source TOOL_RESULT | PRODUCED |
| artifact_A | data_source TOOL_CALL | PRODUCED (via producer_event_id) |
| artifact_B | data_source TOOL_CALL | PRODUCED (via producer_event_id) |
| artifact_A | reasoning event | CONSUMED |
| artifact_B | reasoning event | CONSUMED |

## Evidence Nodes

| Evidence ID | Artifact ID | Value | Creation Event |
|------------|------------|-------|---------------|
| evi_cb7eaf... | art_a792... | "42" | TOOL_RESULT |
| evi_16e192... | art_0869... | "ok" | TOOL_RESULT |
| evi_xxxxx... | art_reason... | (reasoning text) | REASONING |
| evi_yyyyy... | art_output... | (output text) | OUTPUT |

## Evidence Transformations (Channels)

```
evi_A ("42")  --[consumed_by]--> evi_reasoning
evi_B ("ok")  --[consumed_by]--> evi_reasoning
evi_reasoning --[consumed_by]--> evi_output
```

## Channel-Level Intervention Target

```
Channel A intervention:
    type: ARTIFACT_REPLACEMENT
    target: artifact_A (art_a792...)
    replacement: ""
    
    Effect on evidence graph:
    evi_A ("42")  --> BLOCKED (value replaced with "")
    evi_B ("ok")  --> PRESERVED (not targeted)
```

## Source-Step Intervention Target

```
Source-step intervention:
    type: TOOL_RESULT_OVERRIDE
    target: TOOL_RESULT event (evt_c87340c4...)
    replacement: ""
    
    Effect on evidence graph:
    evi_A ("42")  --> BLOCKED (part of overridden event)
    evi_B ("ok")  --> BLOCKED (part of overridden event)
```

## Scope Comparison

```
Scope(channel_A) = {evi_A}
Scope(source_step) = {evi_A, evi_B}

Scope(channel_A) < Scope(source_step)
```

Channel-level intervention has strictly narrower scope than
source-step intervention. This is the defining operational
distinction between channel-level and step-level causal analysis.
