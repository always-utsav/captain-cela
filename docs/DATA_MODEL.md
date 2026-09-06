# Data Model

## Stage 2 — Canonical Event & Execution Data Model

This document describes CAPTAIN's framework-independent canonical representation
of agent executions, implemented in `captain/models/`.

### Overview

The canonical model captures what happened during an agent execution at a level
of detail sufficient for later tracing, provenance, graph construction,
counterfactual replay, and failure analysis -- without implementing any of those
systems.

```text
ExecutionRun
    |
    +-- Event (ordered by sequence_number)
    |     +-- event_type: INPUT, PLANNING, REASONING, MEMORY_*, TOOL_*, MODEL_*, OUTPUT, ERROR
    |     +-- input_artifact_ids  (references by ID)
    |     +-- output_artifact_ids (references by ID)
    |     +-- parent_event_id     (structural relationship by ID)
    |
    +-- Artifact
    |     +-- artifact_type: TEXT, IMAGE, STRUCTURED_DATA, FILE, TOOL_OUTPUT, MODEL_OUTPUT
    |     +-- value / reference
    |     +-- producer_event_id   (provenance link by ID)
    |
    +-- Causal/structural relationships via stable IDs
```

---

### ExecutionRun (`captain/models/execution.py`)

Represents one complete agent execution.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Globally unique ID (`run_` prefix) |
| `status` | `RunStatus` | Lifecycle: CREATED → RUNNING → COMPLETED/FAILED/CANCELLED |
| `started_at` | `datetime` (UTC) | When the run began |
| `ended_at` | `datetime?` (UTC) | When the run ended (None while running) |
| `task_input` | `str` | The task/prompt that initiated the run |
| `events` | `list[Event]` | Ordered events recorded during execution |
| `artifacts` | `list[Artifact]` | Data produced/consumed during execution |
| `metadata` | `dict[str, Any]` | Additional context |
| `parent_run_id` | `str?` | Parent run for counterfactual/replay (future) |

**Invariants**: `ended_at` must not precede `started_at`. `run_id` must not be empty.

---

### Event (`captain/models/events.py`)

Represents one observable execution event.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` | Globally unique ID (`evt_` prefix) |
| `run_id` | `str` | ID of the containing ExecutionRun |
| `event_type` | `EventType` | Category of the event |
| `timestamp` | `datetime` (UTC) | When the event occurred |
| `sequence_number` | `int` | Zero-based ordinal for deterministic ordering |
| `parent_event_id` | `str?` | ID of a parent event (structural relationship) |
| `component` | `str` | Source component (e.g. `"planner"`, `"tool:calculator"`) |
| `input_artifact_ids` | `list[str]` | IDs of artifacts consumed |
| `output_artifact_ids` | `list[str]` | IDs of artifacts produced |
| `payload` | `dict[str, Any]` | Structured event-specific data |
| `metadata` | `dict[str, Any]` | Additional context |

**Invariants**: `sequence_number >= 0`. `parent_event_id != event_id`. IDs must not be empty.

---

### Artifact (`captain/models/artifacts.py`)

Represents data produced, consumed, or transformed during execution.

| Field | Type | Description |
|-------|------|-------------|
| `artifact_id` | `str` | Globally unique ID (`art_` prefix) |
| `artifact_type` | `ArtifactType` | Kind/modality of data |
| `value` | `str | dict | list | None` | Inline data (small payloads) |
| `reference` | `str?` | URI/path for external/large content |
| `producer_event_id` | `str?` | ID of the event that created this artifact |
| `metadata` | `dict[str, Any]` | Additional context |
| `created_at` | `datetime` (UTC) | When the artifact was created |

**Design**: Large binary content (images, files) is stored by reference, not inline.

---

### EventType (`captain/models/enums.py`)

| Member | Value | Description |
|--------|-------|-------------|
| `INPUT` | `"input"` | Task/input received |
| `PLANNING` | `"planning"` | Plan generation |
| `REASONING` | `"reasoning"` | LLM reasoning step |
| `MEMORY_READ` | `"memory_read"` | Memory retrieval |
| `MEMORY_WRITE` | `"memory_write"` | Memory storage |
| `TOOL_CALL` | `"tool_call"` | Tool invocation |
| `TOOL_RESULT` | `"tool_result"` | Tool response |
| `MODEL_CALL` | `"model_call"` | LLM API call |
| `MODEL_RESULT` | `"model_result"` | LLM API response |
| `OUTPUT` | `"output"` | Final output |
| `ERROR` | `"error"` | Error occurrence |

New event types can be added without redesigning the model.

---

### RunStatus (`captain/models/enums.py`)

`CREATED` → `RUNNING` → `COMPLETED` / `FAILED` / `CANCELLED`

`CANCELLED` is included for runs aborted by user or timeout.

---

### ArtifactType (`captain/models/enums.py`)

`TEXT`, `IMAGE`, `STRUCTURED_DATA`, `FILE`, `TOOL_OUTPUT`, `MODEL_OUTPUT`

---

### Identifier Strategy

- Prefixed UUID4 strings: `run_<hex>`, `evt_<hex>`, `art_<hex>`
- Globally unique across independent executions
- No database-generated sequences
- Ordering determinism via `sequence_number` + `timestamp`, not UUID order
- Helper functions in `captain/models/ids.py`

### Relationship / Reference Strategy

- Events reference artifacts by ID (`input_artifact_ids`, `output_artifact_ids`)
- Artifacts reference their producer event by ID (`producer_event_id`)
- Events reference parent events by ID (`parent_event_id`)
- Runs reference parent runs by ID (`parent_run_id`)
- No recursive embedding -- all references are flat string IDs
- Future graph builder reconstructs edges from these ID references

### Serialization Guarantees

All models support clean Pydantic JSON round-trips:

```
model → model_dump_json() → JSON string → model_validate_json() → equivalent model
```

Timestamps serialize as ISO 8601 strings with timezone info.

### Intentionally Deferred

- Execution graph construction (Stage 6)
- Cross-event graph validation (belongs to graph layer)
- Counterfactual replay behavior (future)
- Failure propagation analysis (future)
- Causal inference (not information lineage)

---

## Stage 5 -- Provenance Model

The provenance system (`captain/provenance/`) provides information-lineage
analysis over canonical execution data.  It answers "where did this information
come from?" without performing causal inference.

### RelationshipType (`captain/provenance/model.py`)

| Member | Value | Description |
|--------|-------|-------------|
| `PRODUCED` | `"produced"` | An event created/produced an artifact |
| `CONSUMED` | `"consumed"` | An event consumed/read an artifact as input |
| `DERIVED` | `"derived"` | An artifact was derived from another through an event |

### ProvenanceRecord (`captain/provenance/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `artifact_id` | `str` | The artifact involved |
| `event_id` | `str` | The event involved (producer or consumer) |
| `relationship` | `RelationshipType` | Type of lineage link |
| `source_artifact_id` | `str?` | Upstream artifact (for DERIVED relationships) |
| `metadata` | `dict[str, Any]` | Optional context |

### Provenance Extraction

`ProvenanceExtractor(run).extract()` derives relationships from:

- `Event.output_artifact_ids` -> PRODUCED
- `Event.input_artifact_ids` -> CONSUMED
- `Artifact.producer_event_id` -> PRODUCED (deduplicated)

### Provenance Query API

`ProvenanceQuery(run)` provides:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_producer(art_id)` | `str?` | Event ID that produced the artifact |
| `get_consumers(art_id)` | `list[str]` | Event IDs that consumed the artifact |
| `get_upstream_artifacts(evt_id)` | `list[str]` | Input artifact IDs of the event |
| `get_downstream_artifacts(evt_id)` | `list[str]` | Output artifact IDs of the event |
| `trace_upstream(art_id)` | `list[str]` | Multi-hop upstream artifact chain |
| `trace_downstream(art_id)` | `list[str]` | Multi-hop downstream artifact chain |
| `is_ancestor(a, b)` | `bool` | Whether a is upstream ancestor of b |
| `is_descendant(a, b)` | `bool` | Whether a is downstream descendant of b |

All traversals are cycle-safe (visited-set tracking) and deterministically ordered.

---

## Stage 6 -- Execution Graph Model

The execution graph (`captain/graph/`) provides a structural representation of
agent executions.  It is built from provenance relationships and represents
data flow, NOT proven causation.

### Node Types (`captain/graph/model.py`)

| Type | Description |
|------|-------------|
| `EVENT` | Represents a canonical Event (identified by event_id) |
| `ARTIFACT` | Represents a canonical Artifact (identified by artifact_id) |

Event nodes retain `sequence_number` for execution ordering.
Nodes reference canonical sources by ID -- they do NOT embed full objects.

### Edge Types and Direction (`captain/graph/model.py`)

| Type | Direction | Description |
|------|-----------|-------------|
| `PRODUCED` | Event -> Artifact | The event created the artifact |
| `CONSUMED` | Artifact -> Event | The event consumed the artifact |
| `DERIVED` | Artifact -> Artifact | Lineage through an intermediary event |

**Important**: adjacency represents provenance relationships, not causal links.
Execution order (sequence numbers) != causal relationship.

### Graph API (`captain/graph/model.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `get_event_node(id)` | `GraphNode?` | Lookup event node by ID |
| `get_artifact_node(id)` | `GraphNode?` | Lookup artifact node by ID |
| `get_successors(id)` | `list[str]` | Sorted successor node IDs |
| `get_predecessors(id)` | `list[str]` | Sorted predecessor node IDs |
| `get_event_artifacts(id)` | `list[str]` | Artifacts connected to event |
| `get_artifact_events(id)` | `list[str]` | Events connected to artifact |
| `get_event_events(id)` | `list[str]` | Events connected through shared artifacts |
| `traverse_downstream(id)` | `list[str]` | BFS downstream, cycle-safe |
| `traverse_upstream(id)` | `list[str]` | BFS upstream, cycle-safe |
| `to_dict()` | `dict` | JSON-compatible export |

### Builder (`captain/graph/builder.py`)

`ExecutionGraphBuilder.build(run)` converts an ExecutionRun into an ExecutionGraph
via the Stage 5 ProvenanceExtractor.

### Malformed-Reference Behavior

Edges referencing unknown node IDs are silently dropped.  No fabricated/ghost
nodes are created.  This ensures the graph only contains verified structure.

### Serialization

`to_dict()` exports nodes (sorted: events by sequence_number, then artifacts
by ID) and edges as JSON-compatible dictionaries.

---

## Stage 7 -- Graph Validation & Analysis

### Validation (`captain/graph/validation.py`)

`GraphValidator.validate(graph)` returns a `ValidationResult`:

| Field | Type | Description |
|-------|------|-------------|
| `is_valid` | `bool` | True if zero errors |
| `errors` | `list[ValidationFinding]` | ERROR severity findings |
| `warnings` | `list[ValidationFinding]` | WARNING severity findings |

**Validation checks**:

| Code | Severity | Description |
|------|----------|-------------|
| `ADJACENCY_MISMATCH_*` | ERROR | Successor/predecessor indexes don't match edges |
| `EDGE_MISSING_SOURCE` | ERROR | Edge references non-existent source node |
| `EDGE_MISSING_TARGET` | ERROR | Edge references non-existent target node |
| `INVALID_EDGE_COMBINATION` | ERROR | Edge type invalid for source/target node types |
| `SELF_LOOP` | ERROR | Edge source == target |
| `EVENT_MISSING_SEQUENCE` | WARNING | Event node has no sequence_number |
| `ISOLATED_NODE` | WARNING | Node has no edges |

### Analysis (`captain/graph/analysis.py`)

`GraphAnalyzer(graph)` provides:

| Method | Returns | Description |
|--------|---------|-------------|
| `in_degree(id)` | `int` | Incoming edge count |
| `out_degree(id)` | `int` | Outgoing edge count |
| `degree(id)` | `int` | Total edges (in + out) |
| `roots()` | `list[str]` | Nodes with in_degree 0 |
| `leaves()` | `list[str]` | Nodes with out_degree 0 |
| `isolated_nodes()` | `list[str]` | Nodes with degree 0 |
| `reachable_downstream(id)` | `list[str]` | BFS downstream, cycle-safe |
| `reachable_upstream(id)` | `list[str]` | BFS upstream, cycle-safe |
| `event_execution_order()` | `list[str]` | Events sorted by sequence_number |
| `structural_event_path(a, b)` | `list[str]?` | Shortest structural path (events + artifacts) |
| `all_event_paths()` | `list[list[str]]` | Root-to-leaf event paths |
| `summary()` | `dict` | Metric summary |

**Important**: structural paths represent provenance connectivity, NOT causal chains.
Execution order (sequence_number) != causal relationship.

---

## Stage 9 -- Counterfactual Intervention Model

### Concepts

| Concept | Meaning | Stage |
|---------|---------|-------|
| **Observation** | What actually happened | Stage 2-3 |
| **Intervention** | What we hypothetically change | Stage 9 |
| **Replay** | What happens when the change is rerun | Stage 10 |
| **Causal Effect** | Difference replay shows vs baseline | Future |

### Intervention Types (`captain/intervention/model.py`)

| Type | Target | Replacement Required | Description |
|------|--------|---------------------|-------------|
| `ARTIFACT_REPLACEMENT` | Artifact | Yes | Replace artifact value |
| `TOOL_RESULT_OVERRIDE` | Event (TOOL_RESULT) | Yes | Replace tool output |
| `EVENT_DISABLE` | Event | No | Remove event from replay |
| `EVENT_OUTPUT_OVERRIDE` | Event | Yes | Replace event output |

### Intervention Model

| Field | Type | Description |
|-------|------|-------------|
| `intervention_id` | `str` | Unique ID (intv_ prefix) |
| `intervention_type` | `InterventionType` | Type of modification |
| `baseline_run_id` | `str` | Observed run targeted |
| `target_id` | `str` | Canonical ID of target |
| `replacement_value` | `str/dict/list/None` | Replacement data |
| `description` | `str` | Human explanation |

### Validation Rules (`captain/intervention/validation.py`)

| Code | Severity | Description |
|------|----------|-------------|
| `BASELINE_MISMATCH` | ERROR | Intervention targets wrong run |
| `INVALID_TARGET_FORMAT` | ERROR | Wrong ID prefix for type |
| `TARGET_NOT_FOUND` | ERROR | Target doesn't exist in run |
| `WRONG_EVENT_TYPE` | ERROR | TOOL_RESULT_OVERRIDE on non-tool event |
| `MISSING_REPLACEMENT` | ERROR | Required replacement value absent |
| `SET_BASELINE_MISMATCH` | ERROR | Set targets wrong run |
| `MIXED_BASELINE` | ERROR | Intervention in set targets different run |
| `DUPLICATE_TARGET` | ERROR | Multiple interventions on same target |

### Immutability Guarantee

Interventions NEVER mutate the original `ExecutionRun`.
The observed run is the immutable baseline.
`Intervention` describes a hypothetical change, not the effect.

---

## Stage 10 -- Counterfactual Replay Engine

### Replay Lifecycle (`captain/replay/engine.py`)

| Step | Action | Output |
|------|--------|--------|
| 1 | Validate intervention against baseline | Accept or REJECTED |
| 2 | Extract baseline execution data | LLM responses, tool results, plan structure |
| 3 | Apply interventions | Modified LLM responses, tool wrappers, task text |
| 4 | Re-execute via TracedAgent | Genuine new ExecutionRun |
| 5 | Link to baseline | parent_run_id set |

### CounterfactualResult (`captain/replay/engine.py`)

| Field | Type | Description |
|-------|------|-------------|
| `status` | `ReplayStatus` | SUCCESS, REJECTED, or FAILED |
| `counterfactual_run` | `ExecutionRun \| None` | New run (None on reject/fail) |
| `baseline_run_id` | `str` | ID of baseline run |
| `intervention_ids` | `list[str]` | Applied intervention IDs |
| `rejection_reason` | `str \| None` | Why rejected/failed |
| `metadata` | `dict` | Replay context |

### Intervention Execution Semantics

| Type | Replay Behaviour |
|------|-----------------|
| `ARTIFACT_REPLACEMENT` | Replaces at producing boundary (tool/LLM/input) |
| `TOOL_RESULT_OVERRIDE` | Wraps tool via `_OverrideTool` to return override |
| `EVENT_DISABLE` | Removes step from plan; rejects essential events |
| `EVENT_OUTPUT_OVERRIDE` | Replaces LLM/tool output at event boundary |

### Identity Rules

| Property | Baseline | Counterfactual |
|----------|----------|----------------|
| `run_id` | Original | Fresh `run_` ID |
| `event_id` | Original | Fresh `evt_` IDs |
| `artifact_id` | Original | Fresh `art_` IDs |
| `parent_run_id` | None | baseline.run_id |
| `metadata` | Original | Includes `is_counterfactual: true` |

### Unsupported Disables

Events that CANNOT be disabled (essential pipeline):
INPUT, PLANNING, OUTPUT, MEMORY_WRITE.
Attempting to disable these returns REJECTED.

---

## Stage 11 -- CELA Research Lock (Specification Only)

Stage 11 freezes data model specifications for the CELA research
method. No runtime data models are implemented in Stage 11.

### Evidence Ontology (Frozen for Stage 12)

The following evidence types classify `Artifact` instances by their
role in agent execution:

| Evidence Type | Description | CAPTAIN Mapping |
|---------------|-------------|-----------------|
| `OBSERVATION` | Original input/sensory evidence | TEXT/IMAGE artifact from INPUT event |
| `INTERPRETATION` | Model-derived understanding | MODEL_OUTPUT from REASONING event |
| `MEMORY_EVIDENCE` | Stored working memory content | Value from MEMORY_WRITE event |
| `RETRIEVED_CONTEXT` | Recalled/retrieved memory | Value from MEMORY_READ event |
| `PLANNING_PREMISE` | Basis for plan decisions | STRUCTURED_DATA from PLANNING event |
| `TOOL_INPUT` | Arguments/evidence sent to tool | Payload from TOOL_CALL event |
| `TOOL_OUTPUT` | Results returned from tool | TOOL_OUTPUT from TOOL_RESULT event |
| `DERIVED` | Transformed/synthesized evidence | Any artifact with DERIVED provenance |

Extensible — new types added only when required by experiments.

### Evidence-Flow Edge (Frozen for Stage 12)

```
edge = (source_evidence, target_evidence, channel_type, producing_event)
```

Maps to combinations of:
- `ProvenanceRecord` (PRODUCED, CONSUMED, DERIVED)
- `GraphEdge` (structural graph connections)
- Event→Artifact and Artifact→Event relationships

### Primary Estimand: CEE (Frozen for Stage 14)

```
CEE(e) = P(Y=1) − P(Y=1 | do(C_e = c_cf))
```

Empirical paired estimator:

```
CEE_hat(e) = (1/N) Σ_r [Y_r − Y_r^cf]
```

### Propagation Profile (Frozen for Stage 14)

For lineage `L = (e_1, ..., e_k)`:

```
Π(L) = [CEE(e_1), ..., CEE(e_k)]
```

Diagnostic representation, not a novel causal estimand.

### Compatibility Assessment

No existing data model requires modification for CELA:

| Model | Compatible? | Notes |
|-------|------------|-------|
| `ExecutionRun` | ✅ | parent_run_id supports lineage |
| `Event` | ✅ | sequence_number supports temporal ordering |
| `Artifact` | ✅ | Evidence wraps artifacts, does not replace |
| `ProvenanceRecord` | ✅ | Hard provenance is primary lineage |
| `ExecutionGraph` | ✅ | Evidence layer is additive, not replacement |
| `Intervention` | ✅ | Channel interventions map to existing types |
| `CounterfactualResult` | ✅ | Supports paired replay outcomes |

---

## Stage 12 -- Evidence Layer (Implemented)

### Evidence (`captain/evidence/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `evidence_id` | `str` | Unique `evi_`-prefixed identifier |
| `evidence_type` | `EvidenceType` | Classification by role |
| `artifact_id` | `str \| None` | Reference to CAPTAIN Artifact |
| `creation_event_id` | `str` | Producing execution event |
| `parent_evidence_ids` | `list[str]` | Upstream evidence |
| `sequence_number` | `int` | Temporal position |
| `metadata` | `dict` | Additional context |

### EvidenceType

| Value | Description |
|-------|-------------|
| `text` | Textual content |
| `image` | Image data |
| `structured` | Structured data (plans, configs) |
| `memory` | Working memory content |
| `tool_input` | Tool dispatch arguments |
| `tool_output` | Tool return values |
| `model_output` | LLM-generated content |

### EvidenceTransformation (`captain/evidence/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `source_evidence_id` | `str` | Upstream evidence |
| `target_evidence_id` | `str` | Downstream evidence |
| `transformation_type` | `TransformationType` | How information transformed |
| `event_id` | `str` | Mediating execution event |
| `provenance_method` | `ProvenanceMethod` | How edge was established |
| `confidence` | `float` | Certainty (1.0 = hard) |
| `sequence_number` | `int` | Temporal position |
| `metadata` | `dict` | Additional context |

### TransformationType

| Value | Description |
|-------|-------------|
| `observation` | Input/sensory evidence |
| `interpretation` | Model-derived understanding |
| `memory_store` | Memory write operation |
| `planning_derivation` | Plan construction |
| `tool_dispatch` | Tool call with arguments |
| `tool_return` | Tool result |
| `response_derivation` | Final response synthesis |

### ProvenanceMethod

| Value | Description |
|-------|-------------|
| `hard` | Deterministic, ID-based (Stage 12) |
| `semantic` | Similarity-based (future) |
| `hybrid` | Combined (future) |

### Evidence vs Artifact

| Property | Artifact | Evidence |
|----------|----------|----------|
| Identity | `art_` prefix | `evi_` prefix |
| Purpose | Stored execution data | Information unit for analysis |
| Value | Contains value/reference | References artifact, no duplication |
| Provenance | producer_event_id | parent_evidence_ids + transformation edges |
| Layer | CAPTAIN infrastructure | CELA research |

---

## Stage 13 -- Failure & Intervention Layer (Implemented)

### Failure (`captain/failures/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `failure_id` | `str` | Unique `fail_`-prefixed identifier |
| `run_id` | `str` | ExecutionRun where failure was observed |
| `failure_type` | `FailureType` | Classification |
| `failure_event_id` | `str \| None` | Manifestation event |
| `failure_evidence_ids` | `list[str]` | Associated evidence |
| `sequence_number` | `int` | Temporal position |
| `description` | `str` | Human-readable explanation |
| `metadata` | `dict` | Additional context |

### FailureType

| Value | Description |
|-------|-------------|
| `task_failure` | Task not completed correctly |
| `wrong_tool_use` | Incorrect tool selection/invocation |
| `hallucinated_claim` | Unsupported assertion |
| `unsafe_action` | Safety-violating action |

### Candidate (`captain/failures/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | `str` | Unique `cand_`-prefixed identifier |
| `run_id` | `str` | Baseline run identity |
| `source_evidence_id` | `str` | Upstream evidence |
| `target_evidence_id` | `str` | Downstream evidence |
| `transformation_type` | `str` | Transformation classification |
| `event_id` | `str` | Mediating event |
| `source_evidence_type` | `str` | Source modality |
| `target_evidence_type` | `str` | Target modality |
| `sequence_number` | `int` | Temporal position |
| `graph_distance` | `int` | Hops to failure target |
| `screening_score` | `float` | Non-causal relevance (NOT CEE) |
| `provenance_method` | `str` | How edge was established |

### ChannelIntervention (`captain/failures/model.py`)

| Field | Type | Description |
|-------|------|-------------|
| `intervention_id` | `str` | Unique `cintv_`-prefixed identifier |
| `intervention_type` | `ChannelInterventionType` | BLOCK (primary) |
| `baseline_run_id` | `str` | Baseline run |
| `source_evidence_id` | `str` | Upstream evidence in channel |
| `target_evidence_id` | `str` | Downstream evidence in channel |
| `event_id` | `str` | Mediating event |
| `candidate_id` | `str` | Originating candidate |

### Channel Intervention vs Node Intervention

| Property | Channel Intervention | Node Intervention |
|----------|---------------------|-------------------|
| Target | Edge A→B | Node A |
| Block A→B | ✅ leaves C→B intact | ❌ blocks all from A |
| Granularity | Evidence-flow channel | Evidence object |
| CELA primary | ✅ | ❌ |

---

## Stage 14 -- CEE + Paired Replay + Bottleneck (Implemented)

### PairedTrial (`captain/analysis/estimator.py`)

| Field | Type | Description |
|-------|------|-------------|
| `trial_id` | `str` | Unique `trial_`-prefixed identifier |
| `baseline_run_id` | `str` | Factual run |
| `counterfactual_run_id` | `str` | Counterfactual run |
| `candidate_id` | `str` | Tested candidate |
| `intervention_id` | `str` | Applied intervention |
| `baseline_outcome` | `bool` | Y (factual) |
| `counterfactual_outcome` | `bool` | Y_cf |
| `status` | `TrialStatus` | SUCCESS/REPLAY_ERROR/INVALID_INTERVENTION |

### CEEResult (`captain/analysis/estimator.py`)

| Field | Type | Description |
|-------|------|-------------|
| `result_id` | `str` | Unique `cee_`-prefixed identifier |
| `candidate_id` | `str` | Tested candidate |
| `cee` | `float` | Point estimate |
| `ci_lower` | `float` | CI lower bound |
| `ci_upper` | `float` | CI upper bound |
| `num_trials` | `int` | Total trials |
| `num_valid_trials` | `int` | Successful trials |
| `trials` | `list[PairedTrial]` | Trial details |

### BottleneckResult (`captain/analysis/estimator.py`)

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | `str` | Selected candidate |
| `cee` | `float` | Measured effect |
| `supported` | `bool` | Whether result is supported |
| `num_trials` | `int` | Trial count |

### CEE Definition

CEE(e) = P(Y=1) − P(Y=1 | do(C_e = ∅))

- Positive: blocking reduces failure probability
- Zero: no measured change
- Negative: blocking increases failure probability

Empirical: CEE_hat(e) = (1/N) Sum [Y_r - Y_r_cf]

---

## Stage 14.1 -- Channel Intervention Fidelity Correction (Implemented)

`channel_to_intervention()` now resolves the SOURCE evidence's producing
event. For tool-produced channels, uses TOOL_RESULT_OVERRIDE targeting
the specific TOOL_RESULT event. BLOCK(A->B) preserves C->B.

---

## Stage 15 -- Cascade Intervention + Utility/Cost (Implemented)

### InterventionSetSpec (`captain/analysis/cascade.py`)

| Field | Type | Description |
|-------|------|-------------|
| `set_id` | `str` | Unique `iset_`-prefixed identifier |
| `baseline_run_id` | `str` | The observed run |
| `channel_interventions` | `list[ChannelIntervention]` | Channels in the set |
| `total_cost` | `float` | Sum of intervention costs |
| `validated` | `bool` | Validation status |

### CostModel (`captain/analysis/cascade.py`)

| Field | Type | Description |
|-------|------|-------------|
| `default_cost` | `float` | Per-channel default (1.0) |
| `channel_costs` | `dict[str, float]` | Per-intervention-id overrides |

Experimental cost model. Cost is additive: Cost(S) = Sum cost(e).

### CascadeResult (`captain/analysis/cascade.py`)

| Field | Type | Description |
|-------|------|-------------|
| `result_id` | `str` | Unique `casc_`-prefixed identifier |
| `set_id` | `str` | InterventionSetSpec identity |
| `cee` | `float` | Set-level CEE_hat(S) |
| `ci_lower/ci_upper` | `float` | Confidence bounds |
| `total_cost` | `float` | Sum of costs |
| `utility` | `float` | U(S) = CEE(S) - lambda*Cost(S) |
| `prevented` | `bool` | Evaluator-confirmed prevention |
| `prevention_rate` | `float` | Fraction of trials prevented |
| `supported` | `bool` | Whether estimate is supported |

CEE(S) = P(Y=1) - P(Y=1 | do(C_S)). Measured via real joint replay.
CEE(S) is NOT calculated by summing individual CEE values.

### SelectionResult (`captain/analysis/cascade.py`)

| Field | Type | Description |
|-------|------|-------------|
| `selection_id` | `str` | Unique `sel_`-prefixed identifier |
| `selected_set` | `InterventionSetSpec` | Selected set (or None) |
| `cascade_result` | `CascadeResult` | Set-level CEE for selected |
| `selection_method` | `str` | Always "greedy_marginal_gain" |
| `selection_steps` | `list[MarginalGainStep]` | Audit trail |
| `status` | `SelectionStatus` | SUCCESS/NO_SUPPORTED_SOLUTION/EVALUATION_BUDGET_EXHAUSTED |
| `evaluations_used` | `int` | Total evaluations performed |
| `max_evaluations` | `int` | Evaluation budget |

Global optimality is NOT claimed. The selected set is the best
supported set found under the configured search procedure.







