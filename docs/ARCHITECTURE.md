# CAPTAIN Architecture

## Architectural Layers

1. **Layer A — Agent Execution (IMPLEMENTED — Stage 1)**: modular reference agent with planner, reasoner, working memory, tool system, LLM provider abstraction, and response generator
2. **Layer B -- Observation (IMPLEMENTED -- Stage 3 + 5)**: execution trace collector, multimodal provenance extractor
3. **Layer C -- Representation (IMPLEMENTED -- Stage 6 + 7)**: execution graph builder, graph validation, graph analysis
4. **Layer D — Counterfactual Analysis (IMPLEMENTED -- Stage 9 + 10)**: intervention model, counterfactual replay engine
5. **Layer E -- Evidence & Failure Analysis (IMPLEMENTED -- Stages 12-15)**: evidence identity/lineage, failure model, causal estimation, cascade prevention
6. **Layer F -- Research Evaluation (IMPLEMENTED -- Stages 16-17)**: benchmarks, baselines, oracle, benchmark runner, statistical validation, experiment runner
7. **Layer G -- Presentation (IMPLEMENTED -- Stages 8 + 18)**: trace explorer, benchmark demo, experiment runner, result visualization, reproducible demo

## Core Architectural Principle
External systems communicate with CAPTAIN through adapters, while CAPTAIN's core research logic operates on canonical internal representations.

## Dependency Direction
```text
External Systems → Adapters → Canonical CAPTAIN Models → Tracing/Provenance → Graph → Counterfactual → Evidence/Failure → Analysis → Experiments
```

## Implementation Status

### Stage 0 — Repository Foundation
- Core infrastructure (config, logging, exceptions)
- Directory structure
- Documentation skeleton

### Stage 1 — Reference Multimodal Agent
- `captain/agent/types.py` — Data types: Modality, Content, TaskInput, PlanStep, ToolCall, AgentResponse
- `captain/agent/memory.py` — Working memory (in-process, dict-backed)
- `captain/agent/tools.py` — Tool interface, ToolRegistry, 3 demo tools
- `captain/agent/planner.py` — LLM-driven task decomposition
- `captain/agent/reasoner.py` — Step executor (tool calls and LLM reasoning)
- `captain/agent/response.py` — Response synthesis from memory
- `captain/agent/agent.py` — Orchestrator (Task → Plan → Execute → Respond)
- `captain/adapters/llm.py` — LLM provider abstraction with MockLLMProvider

### Stage 2 — Canonical Event & Execution Data Model
- `captain/models/ids.py` — Prefixed UUID4 ID generation (run_, evt_, art_)
- `captain/models/enums.py` — EventType (11 categories), RunStatus (5 states), ArtifactType (6 modalities)
- `captain/models/artifacts.py` — Artifact model (value/reference, producer event ID)
- `captain/models/events.py` — Event model (artifact ID refs, sequence numbering, parent events)
- `captain/models/execution.py` — ExecutionRun model (events, artifacts, lifecycle, parent_run_id)

### Stage 3 — Execution Trace Collector
- `captain/tracing/collector.py` — TraceCollector (run lifecycle, monotonic sequences, event/artifact recording)
- `captain/tracing/traced_agent.py` -- TracedAgent (observer wrapper for Stage 1 Agent)

### Stage 4 -- Trace Storage & Query Layer
- `captain/storage/store.py` -- TraceStore (abstract) + FileTraceStore (filesystem JSON, atomic writes)
- `captain/storage/query.py` -- TraceQuery (composable filter: run_id, status, time range, event type)

### Stage 5 -- Multimodal Provenance System
- `captain/provenance/model.py` -- RelationshipType (PRODUCED, CONSUMED, DERIVED) + ProvenanceRecord
- `captain/provenance/extractor.py` -- ProvenanceExtractor (derives lineage from ExecutionRun)
- `captain/provenance/query.py` -- ProvenanceQuery (producer, consumers, multi-hop traversal, ancestry)

### Stage 6 -- Execution Graph Builder
- `captain/graph/model.py` -- NodeType, EdgeType, GraphNode, GraphEdge, ExecutionGraph
- `captain/graph/builder.py` -- ExecutionGraphBuilder (run -> provenance -> graph)

### Stage 7 -- Graph Analysis & Validation Layer
- `captain/graph/validation.py` -- GraphValidator, ValidationResult, ValidationFinding, Severity
- `captain/graph/analysis.py` -- GraphAnalyzer (degree, roots/leaves, reachability, paths, ordering)

### Stage 8 -- Basic Visualization / Trace Explorer
- `captain/explorer/app.py` -- Flask app (JSON API over Stages 1-7)
- `captain/explorer/templates/index.html` -- Single-page UI (vis-network graph)
- `scripts/launch_explorer.py` -- Convenience launcher

**Architecture boundary**: The explorer is a presentation layer ONLY.

### Stage 9 -- Counterfactual Intervention Model
- `captain/intervention/model.py` -- InterventionType, Intervention, InterventionSet
- `captain/intervention/validation.py` -- InterventionValidator, InterventionValidationResult

**Architectural boundary**: Intervention describes WHAT to change, not the effect.

### Stage 10 -- Counterfactual Replay Engine
- `captain/replay/engine.py` -- CounterfactualReplayEngine, CounterfactualResult, ReplayStatus

**Replay architecture**: Full re-execution with intervention injection.

### Stage 11 -- CELA Research Lock & CAPTAIN Bridge

Stage 11 is a specification and architecture stage (no runtime code).
It locks the CELA research direction and bridges CAPTAIN infrastructure
to the CELA research method.

### Stage 12 -- Evidence Layer
- `captain/evidence/model.py` -- Evidence, EvidenceType, EvidenceTransformation, TransformationType, ProvenanceMethod
- `captain/evidence/lineage.py` -- EvidenceLineageBuilder (hard-provenance lineage extraction)
- `captain/evidence/graph.py` -- EvidenceFlowGraph (lightweight evidence-flow analysis view)

**Evidence layer architecture**: Additive layer ON TOP of existing CAPTAIN infrastructure.
Evidence wraps/references Artifacts. EvidenceFlowGraph does NOT replace ExecutionGraph.
Hard provenance only (no semantic provenance). Evidence-flow edges are NOT causal claims.

### Stage 13 -- Failure & Intervention Layer
- `captain/failures/model.py` -- Failure, FailureType, Candidate, ChannelIntervention, ChannelInterventionType
- `captain/failures/analyzer.py` -- FailureAnalyzer (target resolution, region, candidates, interventions)

**Failure layer architecture**: Connects evidence layer to research problem.
Failure-relevant region ≠ causal ancestor set. Screening score ≠ CEE.
Channel interventions target edges (A→B), not nodes. BLOCK is primary intervention.
No replay execution. No CEE estimation. No cascade optimization.

### Stage 14 -- Controlled Paired Replay + CEE + Bottleneck Analysis
- `captain/analysis/estimator.py` -- CEEEstimator, BottleneckAnalyzer, PairedTrial, CEEResult, PropagationProfile, BottleneckResult, channel_to_intervention

**CEE architecture**: Paired factual/counterfactual replay via existing CounterfactualReplayEngine.
CEE(e) = P(Y=1) − P(Y=1|do(C_e=∅)). Paired bootstrap CI. Bottleneck = argmax CEE.
No cascade optimization. No semantic provenance. No external LLMs.

### Stage 14.1 -- True Evidence-Channel Intervention Fidelity Correction
- `captain/analysis/estimator.py` -- `channel_to_intervention()` corrected, `CEEEstimator` extended
- `captain/tracing/traced_agent.py` -- provenance chain for multi-channel evidence flow

**Channel-level semantics**: `channel_to_intervention()` now resolves the SOURCE
evidence's producing event. For tool-produced channels, uses TOOL_RESULT_OVERRIDE
targeting the specific TOOL_RESULT event. BLOCK(A→B) preserves C→B when both
channels share the same mediating event. TracedAgent extended: TOOL_RESULT events
declare output_artifact_ids; REASONING/OUTPUT events consume tool result artifacts.
Backward compatible: without evidence_graph, falls back to event-level.

### Stage 15 -- Cascade Intervention + Utility/Cost Optimization
- `captain/analysis/cascade.py` -- InterventionSetSpec, CostModel, CascadeResult, SelectionResult, CascadeEstimator, GreedyCascadeSelector

**Set-level CEE**: CEE(S) estimated via real joint counterfactual replay. All channels
in the set are blocked in ONE counterfactual execution. CEE(S) != Sum CEE(e).
Greedy marginal-gain selection: D(e|S) = CEE(S U {e}) - CEE(S). Cost model with
configurable per-channel costs. Budget constraint: max CEE(S) s.t. Cost(S) <= B.
Utility: U(S) = CEE(S) - lambda*Cost(S). Prevention is evaluator-confirmed, not
structural. Global optimality is NOT claimed. max_evaluations budget prevents
unbounded computation.

---

## CAPTAIN → CELA Bridge Mapping

This mapping defines how existing CAPTAIN components will be reused,
extended, or wrapped by future CELA research stages.

| CAPTAIN Component | Location | CELA Requirement | Strategy | Reason |
|-------------------|----------|-----------------|----------|--------|
| `ExecutionRun` | `captain/models/execution.py` | Baseline/counterfactual execution container | **REUSE** | Already supports parent_run_id, events, artifacts |
| `Event` | `captain/models/events.py` | Execution-event identity for evidence linkage | **REUSE** | Has event_id, type, payload, artifact refs |
| `Artifact` | `captain/models/artifacts.py` | Maps to evidence objects | **WRAP** | Add evidence-type classification layer on top |
| `ArtifactType` | `captain/models/enums.py` | Maps to evidence ontology | **EXTEND** | Evidence ontology classifies artifacts by role |
| `TraceCollector` | `captain/tracing/collector.py` | Trace production | **REUSE** | No changes needed |
| `TracedAgent` | `captain/tracing/traced_agent.py` | Baseline + replay execution | **REUSE** | Already used by replay engine |
| `ProvenanceExtractor` | `captain/provenance/extractor.py` | Hard-provenance lineage (PRIMARY) | **REUSE** | Provides PRODUCED/CONSUMED/DERIVED |
| `ProvenanceQuery` | `captain/provenance/query.py` | Lineage traversal for evidence paths | **REUSE** | Multi-hop upstream/downstream already works |
| `ProvenanceRecord` | `captain/provenance/model.py` | Evidence-flow edge source | **WRAP** | Map to evidence-flow edges with channel type |
| `ExecutionGraph` | `captain/graph/model.py` | Structural graph layer | **REUSE** | Evidence layer is ON TOP, not a replacement |
| `ExecutionGraphBuilder` | `captain/graph/builder.py` | Graph construction | **REUSE** | Evidence-flow view extends, does not replace |
| `GraphValidator` | `captain/graph/validation.py` | Structural validation | **REUSE** | Evidence layer adds its own validation |
| `GraphAnalyzer` | `captain/graph/analysis.py` | Structural analysis | **EXTEND** | Add evidence-aware traversal methods |
| `FileTraceStore` | `captain/storage/store.py` | Persistence for baseline + CF runs | **REUSE** | No changes needed |
| `TraceQuery` | `captain/storage/query.py` | Run filtering | **REUSE** | No changes needed |
| `Intervention` | `captain/intervention/model.py` | Channel-level intervention spec | **WRAP** | Map evidence-channel targets to existing types |
| `InterventionValidator` | `captain/intervention/validation.py` | Validation | **REUSE** | No changes needed |
| `CounterfactualReplayEngine` | `captain/replay/engine.py` | Paired replay | **REUSE** | Drives counterfactual re-execution |

**Key architectural constraint**: Do NOT create a separate graph
implementation that duplicates `captain.graph`. The intended
relationship:

```
Existing Execution Graph (captain/graph/)
    +
Evidence Identity / Lineage Layer (captain/evidence/ — Stage 12)
    =
CELA Evidence-Flow Analysis View
```

The execution graph answers: "What execution entities are
structurally connected?"

The evidence layer answers: "What information/evidence moved
or transformed between them?"

CELA combines these views.

---

## Temporal / Cyclic Execution Support

Future CELA must support recurrent agent behavior:

```
Observation_t → Reason_t → Action_t → Observation_(t+1) → ...
```

The raw execution graph is NOT assumed to be a DAG.

Existing data structures support this:
- `Event.sequence_number` provides temporal ordering
- `Event.parent_event_id` supports hierarchical structure
- `ExecutionGraph` does not enforce acyclicity

The future causal analysis layer (Stage 14) should use temporal
unrolling/indexing where needed. No schema changes are required
in Stage 11.

---

## Future Stage Roadmap (Stages 12-18)

| Stage | Name | Package | Status |
|-------|------|---------|--------|
| 12 | Evidence Layer | `captain/evidence/` | COMPLETE |
| 13 | Failure & Intervention | `captain/failures/` | COMPLETE |
| 14 | Causal Estimation | `captain/analysis/` | COMPLETE |
| 15 | Cascade Prevention | `captain/analysis/` | COMPLETE |
| 16 | Benchmark & Evaluation | `captain/benchmarks/` | COMPLETE |
| 17 | Scientific Validation | `captain/experiments/` | COMPLETE |
| 18 | Final Integration | `captain/explorer/` | COMPLETE |

---

## Stage 16 -- Benchmark Architecture (IMPLEMENTED)

### Modules

- `captain/benchmarks/scenarios.py` -- Parameterized benchmark generators
- `captain/benchmarks/baselines.py` -- Baseline methods + oracle
- `captain/benchmarks/runner.py` -- Metric evaluator + runner

### Information Flow

```text
CausalMechanismSpec (hidden)
  -> scenario generator -> Agent + Evaluator
  -> TracedAgent -> ExecutionRun (observable)
  -> EvidenceFlowGraph, Failure, ChannelInterventions
  -> Methods receive: run, graph, failure, candidates (NO ground truth)
  -> MetricEvaluator compares method output vs ScenarioGroundTruth
```

### Evaluation Dimensions

1. **Attribution**: Causal precision, recall, F1, Recall@1, Recall@K
2. **Localization**: Origin, propagation, actuator recall
3. **Prevention**: Failure prevention rate, prevention set recall, CEE(S)

Never collapsed into a single score.
