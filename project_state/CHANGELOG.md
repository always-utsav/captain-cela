# CAPTAIN -- Changelog

## 2026-09-01 -- Stage 18: Final Integrated CELA Demonstration + Reproducibility

### Added

- Created `captain/demo.py` -- one-command reproducible demo exercising full
  pipeline: Agent → TracedAgent → EvidenceFlowGraph → FailureAnalyzer →
  CEEEstimator → CascadeSelector → ExperimentRunner → JSON serialization
- Extended `captain/explorer/app.py` with 8 new API endpoints:
  `/api/demo/benchmark`, `/api/evidence/<run_id>`, `/api/failure/<run_id>`,
  `/api/counterfactual/<scenario_id>`, `/api/cascade/<scenario_id>`,
  `/api/experiment`, `/api/experiment/summary`, `/api/experiment/export`
- Created `tests/unit/test_stage18.py` -- 22 tests covering all acceptance criteria
- Result export to `captain_results/` directory (JSON experiment results + summary)
- Reproducibility: deterministic seed, full config serialization, documented workflow

### Modified

- Updated `docs/ARCHITECTURE.md` -- Layer F complete, roadmap Stage 18 COMPLETE
- Updated `docs/EXPERIMENTS.md` -- complete rewrite reflecting implementation
- Updated `docs/ALGORITHMS.md` -- ablation + statistical validation sections
- Updated `project_state/` files (CURRENT_STATE, COMPLETED_MODULES, CHANGELOG, NEXT_TASK)

### Verification

- 644 tests passed (622 existing + 22 new)
- ruff check: all passed
- mypy captain: success (63 source files)
- ruff format: all formatted
- Demo: `python -m captain.demo` completes in ~1s

---

## 2026-08-30 -- Stage 17: Statistical Validation + Robustness + Experimental Analysis

### Added

- Created `captain/experiments/statistics.py` -- AggregateSummary, ConfidenceInterval,
  ComparisonResult, bootstrap_ci, paired_comparison (Wilcoxon/permutation),
  holm_bonferroni, compute_sensitivity, compute_ablation_ladder, FailureAccount
- Created `captain/experiments/runner.py` -- ExperimentConfig, ExperimentRunner,
  ExperimentResult, ReproducibilityMetadata, multi-instance execution,
  aggregate metrics, statistical comparisons, ablation analysis
- Updated `captain/experiments/__init__.py` -- full re-exports
- Created 34 new unit tests in test_experiments.py (622 total)

### Key Design Decisions

- Scenario instance is the independent experimental unit (NOT individual replays)
- Bootstrap percentile CI with deterministic seed (default: 2000 resamples, 95% CI)
- Insufficient-sample cases return explicit insufficient status (no invented CIs)
- Paired Wilcoxon signed-rank (continuous) and permutation test (binary/bounded)
- Automatic test selection based on metric cardinality
- Holm-Bonferroni correction for all simultaneous comparisons
- Paired Cohen's d effect size alongside p-values
- A1-A5 ablation ladder with per-step statistical comparison
- Sensitivity analysis via coefficient of variation
- Failure classification: never conflates infrastructure failure with causal outcomes
- All stdlib (math, random) -- no numpy/scipy dependencies
- Results do NOT claim CELA superiority; they report evidence
- Stage 18 boundary preserved

---

## 2026-08-30 -- Stage 16: Benchmark + Baseline + Comparative Evaluation

### Added

- Created `captain/benchmarks/scenarios.py` -- CausalMechanism, CausalMechanismSpec,
  ScenarioGroundTruth, BenchmarkScenario, 6 parameterized generators (BF-A through BF-F)
- Created `captain/benchmarks/baselines.py` -- BaselineMethod ABC, B1-B5 baselines,
  CELAMethod (A1-A5), ExhaustiveOracle, OracleResult
- Created `captain/benchmarks/runner.py` -- MetricEvaluator, BenchmarkRunner, 7 metric
  models (Attribution/Localization/Prevention/Discrimination/Interaction/Efficiency/Optimality)
- Updated `captain/benchmarks/__init__.py` -- full re-exports
- Created 33 new unit tests in test_benchmarks.py (588 total)

### Key Design Decisions

- Hidden CausalMechanismSpec never exposed to methods (evaluation-only)
- Independent keyword-based failure evaluator checks observable output only
- Six benchmark families: single-cause, redundant (OR), complementary (AND),
  distractor, cascade, cost-asymmetric
- BF-C formally defined: Y = has(kw1) AND has(kw2); blocking either prevents failure
- Separate Attribution / Localization / Prevention metric dimensions (never collapsed)
- Exhaustive oracle for regret computation (evaluation-only, not a baseline)
- Regret = Objective(S*) - Objective(S) as diagnostic metric
- A3 evaluates restricted subsets, A4 uses greedy marginal-gain, oracle is exhaustive
- A1 = B2 (provenance-only), documented as identical
- Deterministic random baseline: seed = scenario_seed * 1000 + 100 + d, 5 draws
- DFSR = |selected intersect irrelevant| / |irrelevant|, None when |irrelevant| = 0
- Recall@1 and Recall@K attribution metrics
- Information parity: all methods receive identical candidates from FailureAnalyzer
- No ground-truth leakage: methods never receive ScenarioGroundTruth
- Real joint counterfactual replay for set evaluation
- Stage 17 boundary preserved: no statistical significance testing

---

## 2026-08-20 -- Stage 15: Cascade Intervention + Utility/Cost Optimization

### Added

- Created `captain/analysis/cascade.py` -- InterventionSetSpec, CostModel,
  CascadeResult, SelectionResult, SelectionStatus, MarginalGainStep,
  CascadeEstimator, GreedyCascadeSelector
- Updated `captain/analysis/__init__.py` -- package re-exports for Stage 15
- Created 33 new unit tests in test_cascade.py (555 total)

### Key Design Decisions

- CEE(S) measured via REAL joint counterfactual replay, NOT by summing individual CEE
- All channels blocked in ONE counterfactual execution (InterventionSet already supports this)
- Greedy marginal-gain selection with configurable max_evaluations budget
- Cost model: configurable per-channel costs, additive Cost(S) = Sum cost(e)
- Utility: U(S) = CEE(S) - lambda * Cost(S)
- Budget constraint: maximize CEE(S) s.t. Cost(S) <= B
- Deterministic tie-breaking: lower cost, then lexicographic intervention ID
- Global optimality is NOT claimed; selection is "best supported set found under
  the configured search procedure"
- Prevention is evaluator-confirmed (Y_baseline=1, Y_cf=0), not structural
- Structural graph disconnection != observed causal failure prevention
- Redundancy: CEE({e1,e2}) == CEE({e1}) when channels are redundant (exact equality)
- Stage 14.1 true channel-level intervention semantics preserved
- No new dependencies, no external LLMs, no semantic provenance

---

## 2026-08-19 -- Stage 14.1: True Evidence-Channel Intervention Fidelity Correction

### Changed

- `captain/analysis/estimator.py` -- `channel_to_intervention()` now accepts an
  optional `EvidenceFlowGraph`. When provided, targets the SOURCE evidence's
  producing event (via TOOL_RESULT_OVERRIDE for tool-produced channels) instead
  of the mediating event. BLOCK(A→B) now preserves C→B when both channels share
  the same mediating event.
- `captain/analysis/estimator.py` -- `CEEEstimator` accepts `evidence_graph`
  parameter and passes it through to the bridge function.
- `captain/tracing/traced_agent.py` -- TOOL_RESULT events now declare
  `output_artifact_ids`; downstream REASONING and OUTPUT events now declare
  `input_artifact_ids` from tool result artifacts. This creates the provenance
  chain required for multi-channel evidence flow.

### Added

- 14 new unit tests in `TestMultiChannelFidelity` (522 total)
  - `test_two_tool_results_exist`: multi-channel scenario has two distinct tool results
  - `test_two_tool_channels_in_graph`: evidence graph has edges from both tool sources
  - `test_channel_targets_source_not_mediator`: intervention targets source TOOL_RESULT, not mediating event
  - `test_block_a_preserves_c`: BLOCK(A→B) preserves C→B — demonstrated through actual replay
  - `test_blocked_channel_has_empty_result`: blocked channel's tool result is empty in counterfactual
  - `test_baseline_immutability_multi_channel`: baseline unchanged after multi-channel replay
  - `test_fresh_counterfactual_ids`: counterfactual run has fresh IDs
  - `test_serialization_roundtrip`: channel intervention and CEE result serialize correctly
  - `test_existing_stage9_still_works`: Stage 9 event-level interventions still work
  - `test_existing_evidence_lineage_still_works`: Stage 12 evidence lineage works on multi-channel runs
  - `test_existing_stage13_candidates_still_work`: Stage 13 candidates work with multi-channel runs
  - `test_cee_with_evidence_graph`: CEE estimation works with evidence_graph parameter
  - `test_end_to_end_multi_channel_pipeline`: full pipeline with true channel-level intervention

### Key Design Decisions

- Source TOOL_CALL events have child TOOL_RESULT events; bridge function resolves the
  TOOL_RESULT child for TOOL_RESULT_OVERRIDE (required by replay engine validator)
- Backward compatible: without `evidence_graph`, falls back to pre-14.1 event-level behavior
- Remaining honest limitation: if two channels originate from the SAME source event,
  both are blocked. In the reference agent, each tool produces exactly one result artifact.

---

## 2026-08-19 -- Stage 14: CEE + Paired Replay + Bottleneck Analysis

### Added

- Created `captain/analysis/estimator.py` -- CEEEstimator, BottleneckAnalyzer, PairedTrial, CEEResult, PropagationProfile, BottleneckResult, channel_to_intervention
- Updated `captain/analysis/__init__.py` -- package re-exports
- Created 31 new unit tests in test_analysis.py (508 total)

### Key Design Decisions

- Channel→event bridge via EVENT_OUTPUT_OVERRIDE (honest limitation documented)
- CEE(e) = P(Y=1) − P(Y=1|do(C_e=∅)) — empirical paired estimator
- Paired bootstrap CI with deterministic seed
- Bottleneck = argmax CEE over supported candidates
- TrialStatus distinguishes replay error from outcome failure
- Baseline immutability enforced; fresh IDs for counterfactual runs
- No external LLMs; deterministic MockLLMProvider for tests

---

## 2026-08-19 -- Stage 13: Failure & Intervention Layer

### Added

- Created `captain/failures/model.py` -- Failure, FailureType, Candidate, ChannelIntervention, ChannelInterventionType
- Created `captain/failures/analyzer.py` -- FailureAnalyzer (target resolution, region, candidates, interventions)
- Created `captain/failures/__init__.py` -- package re-exports
- Created 38 new unit tests in test_failures.py (477 total)

### Key Design Decisions

- Failure labels are evaluator-supplied, not auto-detected
- Failure-relevant region ≠ causal ancestor set (structural search space only)
- Screening score ≠ CEE ≠ causal probability
- Channel interventions target edges (A→B), not nodes
- BLOCK is primary intervention: do(C_e = ∅)
- Intervention is specification only — no replay execution
- Baseline immutability enforced

---

## 2026-08-19 -- Stage 12: Evidence Layer

### Added

- Created `captain/evidence/model.py` -- Evidence, EvidenceType, EvidenceTransformation, TransformationType, ProvenanceMethod
- Created `captain/evidence/lineage.py` -- EvidenceLineageBuilder (hard-provenance lineage extraction from ExecutionRun)
- Created `captain/evidence/graph.py` -- EvidenceFlowGraph (lightweight evidence-flow analysis view)
- Created `captain/evidence/__init__.py` -- package re-exports
- Created 39 new unit tests in test_evidence.py (439 total)

### Key Design Decisions

- Evidence wraps/references Artifacts — no value duplication
- Evidence IDs use `evi_` prefix, distinct from `art_`
- Hard provenance only (no semantic provenance)
- EvidenceFlowGraph is additive to ExecutionGraph, not a replacement
- Cycle-safe BFS traversal for upstream/downstream
- Evidence-flow edges are NOT causal claims
- Temporal identity preserved via sequence numbers

---

## 2026-08-18 -- Stage 11: CELA Research Lock & CAPTAIN Bridge

### Research Lock

- Locked CELA (Counterfactual Evidence-Lineage Attribution) as research method
- Defined primary research object: evidence-flow channels (not steps)
- Defined primary estimand: CEE (Counterfactual Evidence-Flow Effect)
- Frozen evidence ontology (8 types)
- Frozen baselines (B1–B8), metrics, ablations (A1–A10)
- Frozen research hypotheses (H1–H4)
- Documented novelty position (conservative, provisional)
- Distinguished from CAR, CausalFlow, CHIEF

### Documentation Updated

- Rewrote `docs/RESEARCH_SPEC.md` -- 25-section CELA specification
- Rewrote `docs/ALGORITHMS.md` -- implemented + planned algorithms
- Rewrote `docs/EXPERIMENTS.md` -- baselines, metrics, ablations, protocol
- Updated `docs/ARCHITECTURE.md` -- CAPTAIN→CELA bridge mapping, roadmap
- Updated `docs/DATA_MODEL.md` -- evidence ontology, compatibility assessment
- Updated `README.md` -- current status, CELA introduction
- Updated all project_state files

### Architecture Bridge

- Created CAPTAIN→CELA component mapping (REUSE/EXTEND/WRAP)
- Verified all existing data models compatible with CELA
- Documented temporal/cyclic execution support
- Defined future stage roadmap (Stages 12–18)
- No runtime code changes required

---

## 2026-08-09 -- Stage 10: Counterfactual Replay Engine

### Added

- Created `captain/replay/engine.py` -- CounterfactualReplayEngine, CounterfactualResult, ReplayStatus
- Created `captain/replay/__init__.py` -- package re-exports
- Created 21 new unit tests in test_replay.py (400 total)

### Architecture

- Full re-execution replay via TracedAgent pipeline
- Baseline LLM responses reconstructed from trace artifacts
- Intervention-aware tool wrapping (_OverrideTool)
- Fresh IDs for all counterfactual events/artifacts
- parent_run_id links counterfactual to baseline

---

## 2026-08-09 -- Stage 9: Counterfactual Intervention Model

### Added

- Created `captain/intervention/model.py` -- InterventionType, Intervention, InterventionSet
- Created `captain/intervention/validation.py` -- InterventionValidator, InterventionValidationResult
- Created `captain/intervention/__init__.py` -- package re-exports
- Created 33 new unit tests in test_intervention.py

---

## 2026-08-09 -- Stage 8: Basic Visualization / Trace Explorer

### Added

- Created `captain/explorer/app.py` -- Flask app with API endpoints
- Created `captain/explorer/__init__.py` -- package init
- Created `captain/explorer/__main__.py` -- module entry point
- Created `captain/explorer/templates/index.html` -- single-page UI with vis-network graph
- Created `scripts/launch_explorer.py` -- convenience launcher
- Created 15 new unit tests in test_explorer.py
- Added `flask>=3.0` as optional `[explorer]` dependency

---

## 2026-08-09 -- Stage 7: Graph Analysis & Validation Layer

### Added

- Created `captain/graph/validation.py` -- GraphValidator, ValidationResult, ValidationFinding, Severity
- Created `captain/graph/analysis.py` -- GraphAnalyzer (degree, roots/leaves, reachability, paths, ordering)
- Updated `captain/graph/__init__.py` -- re-exports Stage 7 types
- Created 29 new unit tests in test_graph_analysis.py

---

## 2026-08-09 -- Stage 6: Execution Graph Builder

### Added

- Created `captain/graph/model.py` -- NodeType, EdgeType, GraphNode, GraphEdge, ExecutionGraph
- Created `captain/graph/builder.py` -- ExecutionGraphBuilder (run -> provenance -> graph)
- Created `captain/graph/__init__.py` -- re-exports all graph types
- Created 30 new unit tests in test_graph.py

---

## 2026-08-09 -- Stage 5: Multimodal Provenance System

### Added

- Created `captain/provenance/model.py` -- RelationshipType (PRODUCED, CONSUMED, DERIVED) + ProvenanceRecord
- Created `captain/provenance/extractor.py` -- ProvenanceExtractor (derives lineage from ExecutionRun)
- Created `captain/provenance/query.py` -- ProvenanceQuery (producer, consumers, multi-hop traversal, ancestry)
- Created `captain/provenance/__init__.py` -- re-exports all provenance types
- Created 31 new unit tests in test_provenance.py

---

## 2026-08-09 -- Stage 4: Trace Storage & Query Layer

### Added

- Created `captain/storage/store.py` -- TraceStore (abstract) + FileTraceStore (filesystem JSON, atomic writes)
- Created `captain/storage/query.py` -- TraceQuery (composable query builder: status, time range, event type, run ID)
- Created `captain/storage/__init__.py` -- re-exports FileTraceStore, TraceStore, TraceQuery
- Created 40 new unit tests across 3 test files (test_store, test_query, test_storage_integration)

### Removed

- Deleted `scripts/demo_trace.py` -- temporary Stage 3 demo, no longer needed

---

## 2026-08-08 -- Stage 3: Execution Trace Collector

### Added

- Created `captain/tracing/collector.py` — TraceCollector: run lifecycle, monotonic sequence numbers, event/artifact recording
- Created `captain/tracing/traced_agent.py` — TracedAgent: observer wrapper for Stage 1 Agent
- Updated `captain/tracing/__init__.py` — re-exports TraceCollector and TracedAgent
- Created 45 new unit tests across 2 test files (test_collector, test_traced_agent)

---

## 2026-08-07 — Stage 2: Canonical Event & Execution Data Model

### Added

- Created `captain/models/ids.py` — prefixed UUID4 ID generation (run_, evt_, art_)
- Created `captain/models/enums.py` — EventType (11), RunStatus (5), ArtifactType (6)
- Created `captain/models/artifacts.py` — Artifact model with value/reference split
- Created `captain/models/events.py` — Event model with artifact ID references and sequence numbering
- Created `captain/models/execution.py` — ExecutionRun model aggregating events and artifacts
- Updated `captain/models/__init__.py` — re-exports all canonical types
- Created 71 new unit tests across 6 test files (test_ids, test_enums, test_artifacts, test_events, test_execution, test_serialization)
- Updated `docs/DATA_MODEL.md` with full implemented schema documentation

### Changed

- Replaced deprecated `json_encoders` model_config with Pydantic v2 `field_serializer` in all canonical models

---

## 2026-08-07 — Stage 1: Reference Multimodal Agent Foundation

### Added

- Created `captain/agent/` sub-package with modular agent architecture
- Implemented `captain/agent/types.py` — shared data types (Modality, Content, TaskInput, PlanStep, ToolCall, AgentResponse)
- Implemented `captain/adapters/llm.py` — LLM provider abstraction with deterministic MockLLMProvider
- Implemented `captain/agent/memory.py` — lightweight working memory (dict-backed, in-process)
- Implemented `captain/agent/tools.py` — generic tool interface, ToolRegistry, and 3 demo tools (CalculatorTool, TimestampTool, EchoTool)
- Implemented `captain/agent/planner.py` — LLM-driven task decomposition with [TOOL:name] marker parsing
- Implemented `captain/agent/reasoner.py` — step executor for tool and reasoning steps
- Implemented `captain/agent/response.py` — response generator that synthesises from memory
- Implemented `captain/agent/agent.py` — agent orchestrator (Task → Plan → Execute → Respond)
- Created `captain/agent/__init__.py` — re-exports Agent class
- Created 65 new unit tests across 6 test files (test_agent, test_agent_types, test_memory, test_tools, test_planner, test_reasoner)

### Changed

- Updated `captain/adapters/__init__.py` docstring to reflect LLM adapter
- Removed `TCH` rule from ruff config (false positives with `from __future__ import annotations`)

---

## 2026-08-04 — Stage 0: Repository Foundation & Architecture Contract

### Added

- Initialized repository structure with all required directories
- Created Python package `captain` (v0.1.0) with `pyproject.toml`
- Implemented `captain.core.config` — centralized configuration via pydantic-settings
- Implemented `captain.core.logging` — standardized logging infrastructure
- Implemented `captain.core.exceptions` — base exception hierarchy
- Created stub modules for future CAPTAIN components (models, tracing, provenance, graph, counterfactual, failures, analysis, benchmarks, experiments, adapters)
- Created comprehensive documentation: README.md, CLAUDE.md, ARCHITECTURE.md, RESEARCH_SPEC.md, DATA_MODEL.md, ALGORITHMS.md, EXPERIMENTS.md
- Configured quality tooling: pytest, ruff, mypy
- Created unit tests for all Stage 0 executable behavior
- Created project state tracking system
- Created .gitignore, .env.example, LICENSE (MIT)
