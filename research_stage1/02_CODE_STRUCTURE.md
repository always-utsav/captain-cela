# 02 CODE STRUCTURE

## Package Layout

```
captain/
  __init__.py              # Package init
  demo.py                  # One-command demo entry point
  adapters/
    llm.py                 # LLMProvider ABC + MockLLMProvider
  agent/
    agent.py               # Agent orchestrator
    memory.py              # WorkingMemory
    planner.py             # Planner (LLM-based)
    reasoner.py            # Reasoner (step execution)
    response.py            # ResponseGenerator
    tools.py               # Tool ABC + ToolRegistry + builtins
    types.py               # Pydantic: Content, TaskInput, PlanStep, ToolCall, AgentResponse
  analysis/
    __init__.py
    estimator.py           # CEEEstimator, BottleneckAnalyzer, channel_to_intervention
    cascade.py             # CascadeEstimator, GreedyCascadeSelector, CostModel
  benchmarks/
    __init__.py
    baselines.py           # B1-B5 baselines, A1-A5 CELA methods, ExhaustiveOracle
    runner.py              # BenchmarkRunner, MetricEvaluator, all metric models
    scenarios.py           # BF-A through BF-F generators, ground truth
  core/
    config.py              # CaptainConfig
    exceptions.py          # Custom exceptions
    logging.py             # Logging setup
  evidence/
    model.py               # Evidence, EvidenceTransformation, EvidenceType
    lineage.py             # EvidenceLineageBuilder
    graph.py               # EvidenceFlowGraph
  experiments/
    __init__.py
    runner.py              # ExperimentRunner
    statistics.py          # bootstrap_ci, paired_comparison, holm_bonferroni, etc.
  explorer/
    __init__.py
    app.py                 # Flask Explorer app + API endpoints
    templates/index.html   # Research analysis console UI
  failures/
    model.py               # Failure, Candidate, ChannelIntervention
    analyzer.py            # FailureAnalyzer
  graph/
    model.py               # GraphNode, GraphEdge, ExecutionGraph
    builder.py             # ExecutionGraphBuilder
    validation.py          # Graph validation
    analysis.py            # Graph analysis utilities
  intervention/
    model.py               # Intervention, InterventionSet, InterventionType
    validation.py          # InterventionValidator
  models/
    ids.py                 # ID generation (deterministic_ids context manager)
    artifacts.py           # Artifact model
    enums.py               # EventType, RunStatus, Modality
    events.py              # Event model
    execution.py           # ExecutionRun model
  provenance/
    extractor.py           # ProvenanceExtractor
    model.py               # ProvenanceRecord, ProvenanceType
    query.py               # ProvenanceQuery
  replay/
    engine.py              # CounterfactualReplayEngine
  storage/
    store.py               # RunStore
    query.py               # RunQuery
  tracing/
    collector.py           # TraceCollector
    traced_agent.py        # TracedAgent
```

## Key Pydantic Models

### Evidence Layer
- `Evidence`: evidence_id, evidence_type, artifact_id, creation_event_id, parent_evidence_ids, sequence_number
- `EvidenceTransformation`: source_evidence_id, target_evidence_id, transformation_type, event_id, provenance_method, confidence

### Failure Layer
- `Failure`: failure_id, run_id, failure_type, failure_event_id, description
- `Candidate`: candidate_id, source_evidence_id, target_evidence_id, screening_score
- `ChannelIntervention`: intervention_id, intervention_type, baseline_run_id, source_evidence_id, target_evidence_id, event_id

### Analysis Layer
- `CEEResult`: result_id, candidate_id, cee, ci_lower, ci_upper, num_trials, trials
- `CascadeResult`: result_id, set_id, cee, prevention_rate, total_cost, utility
- `SelectionResult`: selection_id, selected_set, cascade_result, total_cost, utility

### Benchmark Layer
- `BenchmarkScenario`: scenario_id, family, seed, run, evidence_graph, failure, candidates, ground_truth
- `ScenarioGroundTruth`: causal_channel_ids, required_prevention_sets, redundancy_groups
- `MethodSelection`: method_name, selected_interventions, selection_method

## Lines of Code (approximate)

| Module | LOC |
|--------|-----|
| analysis/ | ~1400 |
| benchmarks/ | ~2000 |
| replay/engine.py | 618 |
| evidence/ | ~500 |
| failures/ | ~400 |
| experiments/ | ~800 |
| models/ | ~350 |
| agent/ | ~600 |
| explorer/ | ~600 |
| **Total captain/** | **~7500** |
| **Total tests/** | **~5000** |
