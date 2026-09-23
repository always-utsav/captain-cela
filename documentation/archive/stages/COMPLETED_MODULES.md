# CAPTAIN — Completed Modules

## Stage 0 — Repository Foundation & Architecture Contract

**Status:** COMPLETE
**Date Completed:** 2026-08-04

### Deliverables

- Repository structure with all required directories
- Python package configuration (`pyproject.toml`)
- Core infrastructure: `captain.core.config`, `captain.core.logging`, `captain.core.exceptions`
- Package stub modules for all future CAPTAIN components
- Documentation: README.md, CLAUDE.md, ARCHITECTURE.md, RESEARCH_SPEC.md, DATA_MODEL.md, ALGORITHMS.md, EXPERIMENTS.md
- Quality tooling: pytest, ruff, mypy — all configured and passing
- Unit tests for configuration, logging, exceptions, and package initialization
- Project state tracking documents
- .gitignore, .env.example, LICENSE

---

## Stage 1 — Reference Multimodal Agent Foundation

**Status:** COMPLETE
**Date Completed:** 2026-08-07

### Deliverables

- Modular reference agent sub-package (`captain/agent/`)
- Agent data types (`captain/agent/types.py`): `Modality`, `Content`, `TaskInput`, `PlanStep`, `ToolCall`, `AgentResponse`
- LLM provider abstraction (`captain/adapters/llm.py`): `LLMProvider` (abstract), `MockLLMProvider` (deterministic)
- Working memory (`captain/agent/memory.py`): in-process dict-backed store
- Tool system (`captain/agent/tools.py`): `Tool` (abstract), `ToolRegistry`, `CalculatorTool`, `TimestampTool`, `EchoTool`
- Planner (`captain/agent/planner.py`): LLM-driven task decomposition with `[TOOL:name]` marker parsing
- Reasoner (`captain/agent/reasoner.py`): executes plan steps via tools or LLM
- Response generator (`captain/agent/response.py`): synthesises final answers from memory
- Agent orchestrator (`captain/agent/agent.py`): full pipeline (Task → Plan → Execute → Respond)
- Updated adapters docstring (`captain/adapters/__init__.py`)
- 65 new unit tests across 6 test files (85 total)

### Acceptance Criteria Met

- [x] Modular agent architecture with separated responsibilities
- [x] Supports multimodal input (text + image interfaces)
- [x] LLM provider abstraction (no vendor lock-in)
- [x] MockLLMProvider requires no paid APIs
- [x] Lightweight working memory (no persistence, no vectors)
- [x] Generic tool interface with 3 demo tools
- [x] Lightweight planner with task decomposition
- [x] Full execution flow: Task → Plan → Reason → Tool → Response
- [x] Deterministic execution with MockLLMProvider
- [x] All tests pass (85/85)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 2+ functionality implemented
- [x] Backward compatible with Stage 0

---

## Stage 2 — Canonical Event & Execution Data Model

**Status:** COMPLETE
**Date Completed:** 2026-08-07

### Deliverables

- Canonical data models in `captain/models/`
- `captain/models/ids.py`: Prefixed UUID4 ID generation (`run_`, `evt_`, `art_`)
- `captain/models/enums.py`: `EventType` (11 members), `RunStatus` (5 states), `ArtifactType` (6 types)
- `captain/models/artifacts.py`: `Artifact` model with value/reference split
- `captain/models/events.py`: `Event` model with artifact ID references and sequence numbering
- `captain/models/execution.py`: `ExecutionRun` model aggregating events and artifacts
- `captain/models/__init__.py`: Re-exports all canonical types
- Updated `docs/DATA_MODEL.md` with full implemented schema documentation
- 71 new unit tests across 6 test files (156 total)

### Acceptance Criteria Met

- [x] ExecutionRun with run ID, status, timestamps, events, artifacts, parent_run_id
- [x] Event with event ID, run ID, type, timestamp, sequence number, parent event, artifact refs, payload
- [x] Artifact with artifact ID, type, value/reference, producer event ID, metadata
- [x] EventType enum with 11 event categories
- [x] RunStatus enum with 5 states (including CANCELLED)
- [x] ArtifactType enum with 6 modalities
- [x] Prefixed UUID4 identifiers with validation
- [x] Timezone-aware UTC timestamps throughout
- [x] Validation: non-negative sequences, timestamp ordering, self-reference prevention, non-empty IDs
- [x] Clean JSON round-trip serialization/deserialization
- [x] No recursive Pydantic structures
- [x] Framework-independent (no vendor dependencies)
- [x] Stage 1 agent unchanged (backward compatible)
- [x] All tests pass (156/156)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 3+ functionality implemented
- [x] No new dependencies added

---

## Stage 3 — Execution Trace Collector

**Status:** COMPLETE
**Date Completed:** 2026-08-08

### Deliverables

- `captain/tracing/collector.py`: TraceCollector — run lifecycle, event/artifact recording, monotonic sequence numbers
- `captain/tracing/traced_agent.py`: TracedAgent — observer wrapper for Stage 1 Agent
- `captain/tracing/__init__.py`: Re-exports TraceCollector and TracedAgent
- 45 new unit tests across 2 test files (201 total)

### Acceptance Criteria Met

- [x] TraceCollector manages ExecutionRun lifecycle (CREATED → RUNNING → COMPLETED/FAILED)
- [x] Monotonically increasing sequence numbers on events
- [x] TracedAgent wraps Agent without modifying Agent.run()
- [x] Tracing is optional — untraced Agent works unchanged
- [x] Tracing does not alter deterministic AgentResponse
- [x] Events captured: INPUT, PLANNING, REASONING, TOOL_CALL, TOOL_RESULT, MEMORY_WRITE, OUTPUT, ERROR
- [x] Artifacts created: TEXT, IMAGE (by reference), STRUCTURED_DATA, TOOL_OUTPUT, MODEL_OUTPUT
- [x] TOOL_RESULT has parent_event_id → TOOL_CALL
- [x] Multimodal input tracing (text as value, image as reference)
- [x] Failure handling: FAILED status, ERROR event, exception re-raised
- [x] Events/artifacts preserved before failure
- [x] JSON serialization of resulting ExecutionRun
- [x] Full integration test with tool execution
- [x] All tests pass (201/201)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 4+ functionality implemented
- [x] No new dependencies added
- [x] Stage 0-2 backward compatible

---

## Stage 4 -- Trace Storage & Query Layer

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/storage/store.py`: TraceStore (abstract) + FileTraceStore (filesystem JSON persistence)
- `captain/storage/query.py`: TraceQuery (composable query builder)
- `captain/storage/__init__.py`: Re-exports FileTraceStore, TraceStore, TraceQuery
- 40 new unit tests across 3 test files (241 total)

### Acceptance Criteria Met

- [x] TraceStore abstraction: save, load, exists, delete, list_runs, count
- [x] FileTraceStore stores each run as `<run_id>.json`
- [x] Atomic writes via temp file + rename
- [x] Auto-creates storage directory
- [x] Round-trip: ExecutionRun -> JSON -> ExecutionRun without data loss
- [x] Corrupt/invalid JSON returns None (no crash)
- [x] Overwrite/update support
- [x] TraceQuery: filter by run_id, status, time range, event type
- [x] Composable chaining with AND semantics
- [x] Results sorted by started_at ascending
- [x] Integration test: TracedAgent -> save -> load verified
- [x] No global mutable state
- [x] No database, no new dependencies
- [x] All tests pass (241/241)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 5+ functionality implemented
- [x] No new dependencies added
- [x] Stage 0-3 backward compatible
- [x] Temporary demo script removed

---

## Stage 5 -- Multimodal Provenance System

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/provenance/model.py`: RelationshipType enum + ProvenanceRecord model
- `captain/provenance/extractor.py`: ProvenanceExtractor (derives relationships from ExecutionRun)
- `captain/provenance/query.py`: ProvenanceQuery (lineage traversal API)
- `captain/provenance/__init__.py`: Re-exports all provenance types
- 31 new unit tests in test_provenance.py (272 total)

### Acceptance Criteria Met

- [x] RelationshipType: PRODUCED, CONSUMED, DERIVED
- [x] ProvenanceExtractor derives relationships from canonical references
- [x] ProvenanceQuery: get_producer, get_consumers, upstream/downstream artifacts
- [x] Multi-hop traversal: trace_upstream, trace_downstream
- [x] Ancestor/descendant queries: is_ancestor, is_descendant
- [x] Uniform for all artifact types (TEXT, IMAGE, STRUCTURED_DATA, FILE, TOOL_OUTPUT, MODEL_OUTPUT)
- [x] Cycle-safe traversal (visited-set tracking)
- [x] Deterministic ordering
- [x] Works with in-memory and stored (Stage 4) ExecutionRuns
- [x] Integration test with Stage 3 traced run
- [x] Integration test with Stage 4 stored run
- [x] Missing references handled cleanly
- [x] No execution graph / NetworkX / Neo4j
- [x] No causal inference / failure propagation
- [x] All tests pass (272/272)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 6+ functionality implemented
- [x] No new dependencies added
- [x] Stage 0-4 backward compatible

---

## Stage 6 -- Execution Graph Builder

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/graph/model.py`: NodeType, EdgeType, GraphNode, GraphEdge, ExecutionGraph
- `captain/graph/builder.py`: ExecutionGraphBuilder (ExecutionRun -> provenance -> graph)
- `captain/graph/__init__.py`: Re-exports all graph types
- 30 new unit tests in test_graph.py (302 total)

### Acceptance Criteria Met

- [x] NodeType: EVENT, ARTIFACT
- [x] EdgeType: PRODUCED (Event->Artifact), CONSUMED (Artifact->Event), DERIVED (Artifact->Artifact)
- [x] GraphNode retains canonical source ID + sequence_number for event ordering
- [x] No full Event/Artifact objects duplicated in nodes
- [x] ExecutionGraphBuilder uses Stage 5 ProvenanceExtractor
- [x] Deterministic graph construction
- [x] Missing references handled safely (no ghost nodes)
- [x] Node/edge lookup, predecessor/successor, event-event/event-artifact traversal
- [x] BFS upstream/downstream traversal, cycle-safe
- [x] JSON-compatible export via to_dict()
- [x] Integration test: TracedAgent -> graph
- [x] Integration test: stored run -> graph
- [x] All tests pass (302/302)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 7+ functionality implemented
- [x] No NetworkX / Neo4j / graph database
- [x] No causal inference / failure propagation
- [x] No new dependencies added
- [x] Stage 0-5 backward compatible

---

## Stage 7 -- Graph Analysis & Validation Layer

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/graph/validation.py`: GraphValidator, ValidationResult, ValidationFinding, Severity
- `captain/graph/analysis.py`: GraphAnalyzer (degree, roots/leaves, reachability, paths, ordering)
- Updated `captain/graph/__init__.py`: re-exports Stage 7 types
- 29 new unit tests in test_graph_analysis.py (331 total)

### Acceptance Criteria Met

- [x] GraphValidator returns structured ValidationResult (errors + warnings)
- [x] Checks: adjacency consistency, edge references, type combinations, self-loops, sequence numbers, isolated nodes
- [x] Valid graph = zero errors
- [x] GraphAnalyzer: in_degree, out_degree, degree
- [x] Roots, leaves, isolated nodes
- [x] Upstream/downstream reachability (cycle-safe)
- [x] Event execution ordering (by sequence_number)
- [x] Structural event-to-event paths (through artifacts)
- [x] All results deterministic
- [x] Structural paths documented as NOT causal
- [x] Integration test: traced run -> graph -> validate + analyze
- [x] Integration test: stored run -> graph -> validate + analyze
- [x] All tests pass (331/331)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 8+ functionality implemented
- [x] No causal inference / failure propagation / research metrics
- [x] No visualization / dashboard
- [x] No new dependencies added
- [x] Stage 0-6 backward compatible

---

## Stage 8 -- Basic Visualization / Trace Explorer

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/explorer/app.py`: Flask application with JSON API endpoints
- `captain/explorer/__init__.py`: Package init with create_app
- `captain/explorer/__main__.py`: Module entry point
- `captain/explorer/templates/index.html`: Single-page UI (vis-network graph + detail panels)
- `scripts/launch_explorer.py`: Convenience launcher with CLI
- 15 new unit tests in test_explorer.py (346 total)

### Acceptance Criteria Met

- [x] Flask-based local browser UI
- [x] Demo execution with MockLLMProvider (no API key needed)
- [x] Run selection: list stored runs, run demo
- [x] Run summary: ID, status, start/end time, event/artifact counts
- [x] Interactive execution graph (vis-network)
- [x] EVENT and ARTIFACT nodes visually distinguished
- [x] PRODUCED/CONSUMED edge types visually distinguished
- [x] Graph from real ExecutionGraph (not static/fake)
- [x] Event inspection: all canonical fields
- [x] Artifact inspection: type, value, producer, consumers
- [x] Provenance display: producer, consumers, upstream, downstream
- [x] Graph validation badge and analysis summary
- [x] Smoke test passed (index page, demo, graph, events, artifacts, provenance)
- [x] All tests pass (346/346)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No Stage 9+ functionality implemented
- [x] No counterfactual/replay/causal inference
- [x] Flask added as optional [explorer] dependency only
- [x] Stage 0-7 backward compatible

---

## Stage 9 -- Counterfactual Intervention Model

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/intervention/model.py`: InterventionType, Intervention, InterventionSet
- `captain/intervention/validation.py`: InterventionValidator, InterventionValidationResult
- `captain/intervention/__init__.py`: Package init with re-exports
- 33 new unit tests in test_intervention.py (379 total)

### Acceptance Criteria Met

- [x] ARTIFACT_REPLACEMENT intervention type
- [x] TOOL_RESULT_OVERRIDE intervention type
- [x] EVENT_DISABLE intervention type
- [x] EVENT_OUTPUT_OVERRIDE intervention type
- [x] Intervention targets validated against baseline ExecutionRun
- [x] Target ID format validation (art_/evt_ prefixes)
- [x] Target existence validation
- [x] Tool-result override validates event type = TOOL_RESULT
- [x] Replacement value required for all except EVENT_DISABLE
- [x] InterventionSet: deterministic collection for one baseline
- [x] Duplicate target detection
- [x] Mixed baseline rejection
- [x] Structured validation results (errors/warnings)
- [x] JSON round-trip serialization (Pydantic)
- [x] Dict/list replacement values supported
- [x] Immutability: original ExecutionRun never mutated
- [x] Integration test: real traced run + intervention
- [x] Deterministic ordering of interventions
- [x] All tests pass (379/379)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No replay engine implemented
- [x] No causal inference / failure propagation
- [x] No new dependencies
- [x] Stage 0-8 backward compatible


---

## Stage 10 -- Counterfactual Replay Engine

**Status:** COMPLETE
**Date Completed:** 2026-08-09

### Deliverables

- `captain/replay/engine.py`: CounterfactualReplayEngine, CounterfactualResult, ReplayStatus
- `captain/replay/__init__.py`: Package init with re-exports
- 21 new unit tests in test_replay.py (400 total)

### Acceptance Criteria Met

- [x] Full re-execution replay (not trace editing)
- [x] Genuine TracedAgent.run() re-execution under intervention
- [x] ARTIFACT_REPLACEMENT: replaces at producing boundary
- [x] TOOL_RESULT_OVERRIDE: wraps tool to return override value
- [x] EVENT_DISABLE: removes step from plan, rejects essential events
- [x] EVENT_OUTPUT_OVERRIDE: replaces LLM/tool output at boundary
- [x] Baseline immutability verified (JSON snapshot comparison)
- [x] Fresh run_id, event_ids, artifact_ids in counterfactual
- [x] parent_run_id links counterfactual to baseline
- [x] Replay metadata: is_counterfactual, baseline_run_id, intervention_ids
- [x] ReplayStatus: SUCCESS, REJECTED, FAILED
- [x] Invalid interventions rejected before replay
- [x] Baseline mismatch rejected
- [x] Conflicting intervention sets rejected
- [x] Essential event disable rejected (INPUT, PLANNING, OUTPUT, MEMORY_WRITE)
- [x] Deterministic replay with MockLLMProvider
- [x] Counterfactual run compatible with FileTraceStore (save/load)
- [x] Counterfactual run compatible with ProvenanceExtractor
- [x] Counterfactual run compatible with ExecutionGraphBuilder
- [x] Counterfactual run compatible with Explorer (standard ExecutionRun)
- [x] Downstream observable difference verified (TOOL_RESULT_OVERRIDE changes memory, step descriptions, tool calls)
- [x] End-to-end pipeline test: trace → store → intervene → replay → store → provenance → graph
- [x] All tests pass (400/400)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No baseline/counterfactual comparison implemented
- [x] No causal claims, failure propagation, or statistical analysis
- [x] No new dependencies
- [x] Stage 0-9 backward compatible


---

## Stage 11 -- CELA Research Lock & CAPTAIN Bridge

**Status:** COMPLETE
**Date Completed:** 2026-08-18

### Deliverables

This is a specification/architecture stage with no runtime code changes.

- Updated `docs/RESEARCH_SPEC.md` -- 25-section CELA research specification
- Updated `docs/ALGORITHMS.md` -- implemented + planned algorithm specifications
- Updated `docs/EXPERIMENTS.md` -- baselines, metrics, ablations, protocol
- Updated `docs/ARCHITECTURE.md` -- CAPTAIN→CELA bridge mapping, future roadmap
- Updated `docs/DATA_MODEL.md` -- evidence ontology, compatibility assessment
- Updated `README.md` -- current status, CELA introduction, repository organization
- Updated all project_state files

### Acceptance Criteria Met

- [x] CELA research direction locked
- [x] Primary research object defined (evidence-flow channels)
- [x] Primary estimand defined (CEE)
- [x] Evidence ontology frozen (8 types)
- [x] Hard provenance defined as primary lineage mechanism
- [x] Semantic provenance documented as future optional extension
- [x] Research hypotheses documented (H1–H4)
- [x] Baselines frozen (B1–B8)
- [x] Metrics frozen (5 categories, 16+ individual metrics)
- [x] Ablations frozen (A1–A10)
- [x] Benchmark strategy documented
- [x] Experimental protocol documented
- [x] Novelty position documented conservatively
- [x] Distinguished from CAR, CausalFlow, CHIEF
- [x] Explicit non-claims documented
- [x] CAPTAIN→CELA bridge mapping created
- [x] All existing components assessed for CELA compatibility
- [x] No compatibility blockers found (zero code changes)
- [x] Temporal/cyclic execution support documented
- [x] Future stage roadmap defined (Stages 12–18)
- [x] All existing tests still pass (400/400)
- [x] Linting passes (ruff)
- [x] Type checking passes (mypy strict)
- [x] Formatting passes (ruff format)
- [x] No runtime code changes made
- [x] No Stage 12+ functionality implemented
- [x] No new dependencies
- [x] Stage 0-10 unchanged


---

## Stage 12 -- Evidence Layer

**Status:** COMPLETE
**Date Completed:** 2026-08-19

### Deliverables

- `captain/evidence/model.py` -- Evidence, EvidenceType, EvidenceTransformation, TransformationType, ProvenanceMethod, generate_evidence_id
- `captain/evidence/lineage.py` -- EvidenceLineageBuilder
- `captain/evidence/graph.py` -- EvidenceFlowGraph
- `captain/evidence/__init__.py` -- package re-exports
- `tests/unit/test_evidence.py` -- 39 tests

### Acceptance Criteria Met

- [x] Evidence model with evi_ prefixed IDs
- [x] Evidence type ontology (7 types)
- [x] Artifact-to-evidence references (no value duplication)
- [x] Transformation model with 7 transformation types
- [x] Hard provenance only (ProvenanceMethod.HARD)
- [x] Lineage extraction from ExecutionRun via ProvenanceExtractor
- [x] Evidence-flow graph with lookup/adjacency
- [x] Cycle-safe upstream/downstream traversal
- [x] Temporal identity preservation (sequence numbers)
- [x] Deterministic reconstruction from same run
- [x] JSON serialization/deserialization
- [x] End-to-end pipeline test (Agent→Trace→Evidence→Graph)
- [x] All 439 tests pass (400 existing + 39 new)
- [x] ruff check passes
- [x] mypy passes (53 source files)
- [x] ruff format passes
- [x] No semantic provenance implemented
- [x] No Stage 13+ functionality implemented
- [x] No new dependencies
- [x] Stages 0–11 unchanged


---

## Stage 13 -- Failure & Intervention Layer

**Status:** COMPLETE
**Date Completed:** 2026-08-19

### Deliverables

- `captain/failures/model.py` -- Failure, FailureType, Candidate, ChannelIntervention, ChannelInterventionType
- `captain/failures/analyzer.py` -- FailureAnalyzer
- `captain/failures/__init__.py` -- package re-exports
- `tests/unit/test_failures.py` -- 38 tests

### Acceptance Criteria Met

- [x] Failure model with fail_ prefixed IDs
- [x] Failure type taxonomy (4 types)
- [x] Failure serialization/deserialization
- [x] Failure target resolution (by evidence, by event, fallback)
- [x] Failure-relevant region extraction (upstream BFS)
- [x] Correct exclusion of unrelated evidence
- [x] Cycle-safe region traversal
- [x] Deterministic region generation
- [x] Candidate generation from region
- [x] Candidate IDs unique (cand_ prefix)
- [x] Source/target evidence references valid
- [x] No self-loop candidates
- [x] Modality preserved in candidates
- [x] Non-causal screening score (proximity-based)
- [x] Score sorted descending
- [x] max_candidates support
- [x] ChannelIntervention BLOCK construction
- [x] Intervention targets edge (A→B), not node
- [x] Intervention serialization
- [x] Baseline immutability verified
- [x] End-to-end pipeline: Agent→Trace→Evidence→Failure→Candidates→Interventions
- [x] All 477 tests pass (439 existing + 38 new)
- [x] ruff check passes
- [x] mypy passes (55 source files)
- [x] ruff format passes
- [x] No CEE estimation implemented
- [x] No replay executed
- [x] No cascade optimization implemented
- [x] No semantic provenance
- [x] No new dependencies
- [x] Stages 0–12 unchanged


---

## Stage 14 -- CEE + Paired Replay + Bottleneck Analysis

**Status:** COMPLETE
**Date Completed:** 2026-08-19

### Deliverables

- `captain/analysis/estimator.py` -- CEEEstimator, BottleneckAnalyzer, PairedTrial, CEEResult, PropagationProfile, BottleneckResult, Outcome, TrialStatus, channel_to_intervention
- `captain/analysis/__init__.py` -- package re-exports (updated)
- `tests/unit/test_analysis.py` -- 31 tests

### Acceptance Criteria Met

- [x] Channel-to-event bridge (channel_to_intervention)
- [x] Honest limitation documented (event-level granularity)
- [x] Fresh counterfactual run IDs
- [x] Baseline immutability verified
- [x] Parent run linkage
- [x] Deterministic replay
- [x] Outcome model (binary Y)
- [x] PairedTrial model with TrialStatus
- [x] TrialStatus: SUCCESS / REPLAY_ERROR / INVALID_INTERVENTION
- [x] CEE estimator: empirical paired estimator
- [x] Positive CEE test
- [x] Zero CEE test
- [x] Negative CEE test
- [x] Small-N handling (CI = point for N=1)
- [x] Paired bootstrap CI (deterministic seed)
- [x] Bottleneck: highest supported CEE
- [x] Bottleneck: unsupported excluded
- [x] Bottleneck: ties deterministic (lexicographic)
- [x] Bottleneck: min_trials threshold
- [x] Propagation profile construction
- [x] Profile ordering
- [x] Serialization for all models
- [x] End-to-end: Agent→Trace→Evidence→Failure→Candidate→Replay→CEE→Bottleneck
- [x] Downstream effect demonstration
- [x] Stage 13 candidate compatibility
- [x] All 508 tests pass (477 existing + 31 new)
- [x] ruff check passes
- [x] mypy passes (56 source files)
- [x] ruff format passes
- [x] No cascade optimization implemented
- [x] No semantic provenance
- [x] No external LLMs
- [x] No new dependencies
- [x] Stages 0–13 unchanged

---

## Stage 14.1 — True Evidence-Channel Intervention Fidelity Correction

**Status:** COMPLETE
**Date Completed:** 2026-08-19

### Deliverables

- `channel_to_intervention()` corrected: targets SOURCE evidence's producing event
  (TOOL_RESULT_OVERRIDE for tool channels) instead of mediating event
- `CEEEstimator` accepts `evidence_graph` parameter for true channel-level semantics
- `TracedAgent` extended: TOOL_RESULT events declare output_artifact_ids;
  REASONING/OUTPUT events declare input_artifact_ids from tool artifacts
- Multi-channel provenance chain: tool result artifacts flow to downstream events
- 14 new unit tests in TestMultiChannelFidelity

### Acceptance Criteria

- [x] BLOCK(A→B) preserves C→B (demonstrated via actual replay)
- [x] Blocked channel produces empty result in counterfactual
- [x] Baseline immutability maintained
- [x] Fresh IDs for counterfactual runs
- [x] Serialization roundtrip for all models
- [x] Backward compatible: falls back to event-level without evidence_graph
- [x] Existing Stage 9 event-level interventions still work
- [x] Stage 12 evidence lineage works on multi-channel runs
- [x] Stage 13 candidate generation works with multi-channel runs
- [x] CEE estimation works with evidence_graph parameter
- [x] End-to-end multi-channel pipeline passes
- [x] All 522 tests pass (508 existing + 14 new)
- [x] ruff check passes
- [x] mypy passes (56 source files)
- [x] ruff format passes (103 files)
- [x] Honest remaining limitation documented: same-source multi-channel blocking

---

## Stage 15 -- Cascade Intervention + Utility/Cost Optimization

**Status:** COMPLETE
**Date Completed:** 2026-08-20

### Deliverables

- `captain/analysis/cascade.py` -- InterventionSetSpec, CostModel, CascadeResult,
  SelectionResult, SelectionStatus, MarginalGainStep, CascadeEstimator,
  GreedyCascadeSelector
- Updated `captain/analysis/__init__.py` -- Stage 15 re-exports
- 33 new unit tests in test_cascade.py

### Acceptance Criteria

- [x] Individual CEE remains functional
- [x] Joint intervention sets are representable (InterventionSetSpec)
- [x] Joint sets executed in ONE actual counterfactual replay
- [x] CEE(S) estimated from paired joint outcomes
- [x] CEE(S) is NOT calculated by summing individual CEE
- [x] Marginal gain can be evaluated: D(e|S) = CEE(S U {e}) - CEE(S)
- [x] Cost model exists (CostModel with default/per-channel costs)
- [x] Budget constraint exists (budget parameter on selector)
- [x] Utility objective exists: U(S) = CEE(S) - lambda*Cost(S)
- [x] Greedy selection exists (GreedyCascadeSelector)
- [x] Selection does NOT claim global optimality
- [x] Failure prevention is evaluator-confirmed (not structural)
- [x] Redundancy scenario tested (exact equality: CEE({e1,e2}) == CEE({e1}))
- [x] Complementarity scenario tested (real joint replay)
- [x] Budget scenario tested (Cost(e1)=3, budget=2 -> e1 excluded)
- [x] Utility scenario tested
- [x] Channel-level fidelity from Stage 14.1 preserved
- [x] Baseline remains immutable
- [x] Evaluation budget (max_evaluations) with exhaustion status
- [x] Marginal-gain audit trail preserves CEE(S), CEE(S U {e}), D(e|S)
- [x] Deterministic tie-breaking (lower cost, then lexicographic ID)
- [x] End-to-end CELA cascade pipeline test
- [x] All 555 tests pass (522 existing + 33 new)
- [x] ruff check passes
- [x] mypy passes (57 source files)
- [x] ruff format passes (105 files)


## Stage 16 -- Benchmark + Baseline + Comparative Evaluation

**Status:** COMPLETE
**Date Completed:** 2026-08-30

### Deliverables

- `captain/benchmarks/scenarios.py` -- CausalMechanism enum, CausalMechanismSpec,
  ScenarioGroundTruth, BenchmarkScenario, 6 parameterized generators
- `captain/benchmarks/baselines.py` -- BaselineMethod ABC, RandomBaseline (B1),
  ProvenanceOnlyBaseline (B2), CEERankBaseline (B3), GraphStructuralBaseline (B4),
  CostAwareBaseline (B5), CELAMethod (A1-A5), ExhaustiveOracle, OracleResult
- `captain/benchmarks/runner.py` -- 7 metric models, MetricEvaluator, BenchmarkRunner
- `captain/benchmarks/__init__.py` -- re-exports
- `tests/unit/test_benchmarks.py` -- 33 new tests

### Acceptance Criteria

- [x] Hidden causal mechanism represented (CausalMechanism + CausalMechanismSpec)
- [x] Mechanism never passed to methods
- [x] 6 benchmark families with parameterized generators
- [x] BF-C formal AND semantics with expected single/joint outcomes
- [x] BF-E origin/propagation/actuator ground truth
- [x] BF-F explicit cost/budget/feasible-set parameters
- [x] Exhaustive oracle implemented (evaluation-only)
- [x] Regret metric computed
- [x] A3/A4/Oracle operationally distinct
- [x] A1=B2 documented and verified
- [x] Deterministic random baseline protocol
- [x] DFSR correctly defined (denominator=|irrelevant|, None when 0)
- [x] Attribution / localization / prevention separately reported
- [x] Recall@K metric implemented
- [x] Information-access parity verified
- [x] No ground-truth leakage
- [x] Evaluator independence verified
- [x] All results serializable
- [x] All 588 tests pass (555 existing + 33 new)
- [x] ruff check passes
- [x] mypy passes (60 source files)
- [x] ruff format passes (109 files)


## Stage 17 -- Statistical Validation + Robustness + Experimental Analysis

**Status:** COMPLETE
**Date Completed:** 2026-08-30

### Deliverables

- `captain/experiments/statistics.py` -- AggregateSummary, ConfidenceInterval,
  ComparisonResult, bootstrap_ci, paired_comparison (Wilcoxon/permutation),
  holm_bonferroni, compute_sensitivity, compute_ablation_ladder, FailureAccount
- `captain/experiments/runner.py` -- ExperimentConfig, ExperimentRunner,
  ExperimentResult, ReproducibilityMetadata, MethodAggregate, FamilyAggregate
- `captain/experiments/__init__.py` -- re-exports
- `tests/unit/test_experiments.py` -- 34 new tests

### Acceptance Criteria

- [x] Multiple independently seeded scenario instances generated
- [x] All locked B1-B5 and A1-A5 methods evaluated
- [x] Scenario treated as independent experimental unit
- [x] Aggregate primary/secondary metrics computed
- [x] Confidence intervals computed correctly (bootstrap percentile)
- [x] Insufficient-sample cases explicitly handled
- [x] Paired statistical comparisons implemented (Wilcoxon + permutation)
- [x] Multiple comparisons use documented correction (Holm-Bonferroni)
- [x] Effect sizes reported (paired Cohen's d)
- [x] Oracle regret aggregated
- [x] Failure/infrastructure outcomes separated from causal outcomes
- [x] Sensitivity analysis configurable
- [x] Results reproducible from recorded seeds/configuration
- [x] Results serialize successfully
- [x] No hidden ground truth exposed to methods
- [x] No benchmark leakage introduced
- [x] All 622 tests pass (588 existing + 34 new)
- [x] ruff check passes
- [x] mypy passes (62 source files)
- [x] ruff format passes (112 files)
- [x] Stage 18 NOT implemented

---

## Stage 18 — Final Integrated CELA Demonstration + Reproducibility

**Status:** COMPLETE
**Date Completed:** 2026-09-01

### Deliverables

- `captain/demo.py` — one-command reproducible demo (full pipeline)
- `captain/explorer/app.py` — extended with 8 new API endpoints
- `tests/unit/test_stage18.py` — 22 integration tests

### New API Endpoints

- `POST /api/demo/benchmark` — run BF-A scenario, BenchmarkRunner, cache results
- `GET /api/evidence/<run_id>` — evidence-flow graph (nodes + transformations)
- `GET /api/failure/<run_id>` — failure analysis (candidates + interventions)
- `GET /api/counterfactual/<scenario_id>` — factual vs counterfactual comparison
- `GET /api/cascade/<scenario_id>` — cascade results + oracle (eval-only)
- `POST /api/experiment` — run configurable experiment via ExperimentRunner
- `GET /api/experiment/summary` — aggregate results summary
- `POST /api/experiment/export` — serialize to JSON

### Demo Pipeline

```
Agent → TracedAgent → ExecutionRun → ExecutionGraph →
EvidenceLineageBuilder → EvidenceFlowGraph → FailureAnalyzer →
CEEEstimator → CascadeEstimator → GreedyCascadeSelector →
BenchmarkRunner → ExperimentRunner → JSON serialization
```

### Acceptance Criteria

- [x] Existing Explorer functionality still works
- [x] Execution graph prominently visible and usable
- [x] Evidence-flow/provenance can be inspected
- [x] Failure candidates can be inspected
- [x] Channel intervention can be demonstrated
- [x] Factual and counterfactual runs can be compared
- [x] Individual CEE can be displayed
- [x] Cascade intervention can be demonstrated
- [x] Cost/utility/budget information is visible
- [x] Stage 16 benchmark experiments can be launched
- [x] Stage 17 statistical results can be inspected/exported
- [x] Oracle information remains evaluation-only
- [x] Hidden causal ground truth never supplied to methods
- [x] Deterministic end-to-end demo exists
- [x] Experiment results are serialized
- [x] Reproducibility instructions work
- [x] Small fresh-run end-to-end smoke test succeeds
- [x] All 644 tests pass (622 existing + 22 new)
- [x] ruff check passes
- [x] mypy passes (63 source files)
- [x] ruff format passes
- [x] Stage 19 NOT implemented
