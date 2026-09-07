# 11 Shared-Source Correction

## What Was Wrong With The Original BF-G

The original BF-G (Stage 1.1-A) used three SEPARATE tools:

```
data_source("ANSWER=42;STATUS=ok")  → tool_result event 1
analyzer("42")                       → tool_result event 2
validator("ok")                      → tool_result event 3
```

Each tool produced its own TOOL_RESULT event with its own single
output artifact. While conceptually the analyzer and validator
"consumed" the data_source output, the trace structure showed:

- 3 independent TOOL_RESULT events
- 3 independent artifacts
- 3 independent producing events

**This is NOT a shared source.** The three tools had independent
source events. Calling them "channels from one source" was structurally
incorrect — they were channels from three different sources.

The Stage 1.1-A "step vs channel distinction" test verified only that
`target_id` or `intervention_type` differed. This is a structural
property, not an empirical demonstration of scope difference.

## What The New Source-Event Structure Is

The corrected BF-G uses ONE tool (`data_source`) that returns a
multi-output result via `MULTI_OUTPUT_SEPARATOR` (`"|||"`):

```python
data_source.execute() → "42|||ok"
```

The `TracedAgent` splits this into TWO artifacts from ONE event:

```
data_source TOOL_CALL event (step 0)
    ↓ (parent)
data_source TOOL_RESULT event
    ├── artifact_A (value="42", producer=TOOL_CALL)
    └── artifact_B (value="ok", producer=TOOL_CALL)
    output_artifact_ids = [artifact_A.id, artifact_B.id]
```

Both artifacts:
- Share the same `producer_event_id` (TOOL_CALL event)
- Appear in the same `TOOL_RESULT.output_artifact_ids` list
- Are genuinely produced by ONE source event

## How Multiple Artifacts Originate From One Event

1. `FixedValueTool("data_source", "42|||ok")` returns `"42|||ok"`
2. `TracedAgent` detects `MULTI_OUTPUT_SEPARATOR` in the result
3. Splits into parts: `["42", "ok"]`
4. Creates separate `Artifact(ArtifactType.TOOL_OUTPUT)` for each part
5. Each artifact gets `producer_event_id = tool_call_event.event_id`
6. The `TOOL_RESULT` event gets `output_artifact_ids = [art_A.id, art_B.id]`

## How Provenance Distinguishes A and B

`ProvenanceExtractor.extract()` (line 53):
```python
for art_id in sorted(event.output_artifact_ids):
    records.append(ProvenanceRecord(
        artifact_id=art_id,
        event_id=event.event_id,
        relationship=RelationshipType.PRODUCED,
    ))
```

This creates TWO PRODUCED records from the same event — one per artifact.

`EvidenceLineageBuilder.build()` creates separate `EvidenceNode` objects
for each artifact. Each has:
- Its own `evidence_id`
- Its own `artifact_id`
- The same `creation_event_id`

The transformation edges in the evidence-flow graph are:
- `evidence_A → reasoning_evidence` (from artifact A's consumption)
- `evidence_B → reasoning_evidence` (from artifact B's consumption)

These are independently addressable channels through the same mediating
event (reasoning).

## How Channel Intervention Targets A Only

`channel_to_intervention()` now detects multi-artifact source events:

```python
if len(source_event.output_artifact_ids) > 1 and source_evi.artifact_id:
    return Intervention(
        intervention_type=InterventionType.ARTIFACT_REPLACEMENT,
        target_id=source_evi.artifact_id,  # targets specific artifact
        ...
    )
```

This uses `ARTIFACT_REPLACEMENT` targeting the specific artifact ID,
NOT the whole event. The replay engine's `_do_art` handles this by
replacing only that artifact's value and propagating only that text
substitution to downstream LLM responses.

## How Source-Step Intervention Affects Broader Scope

`TOOL_RESULT_OVERRIDE` targets the entire TOOL_RESULT event.
The event payload contains `result: "42|||ok"`.

When this is overridden to `""`, the propagation substitutes BOTH
individual parts (`"42"` and `"ok"`) in downstream LLM responses,
because the engine detects `MULTI_OUTPUT_SEPARATOR` and propagates
each part independently.

Result: BOTH artifact A's text and artifact B's text are removed.
