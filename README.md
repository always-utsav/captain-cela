# CAPTAIN

**C**ounterfactual **A**nalysis **P**latform for **T**race-based **I**nvestigation of **A**utonomous Agent Cascades

## Overview
CAPTAIN is a research-oriented engineering platform designed for studying how failures propagate through autonomous multimodal AI-agent executions.

The research method developed on CAPTAIN is **CELA — Counterfactual Evidence-Lineage Attribution**.

## Status

**IMPLEMENTATION COMPLETE** — All 18 implementation stages complete.

**RESEARCH STAGE 2 COMPLETE** — Full experimental campaign executed.

- 682 tests passing
- Full deterministic demo
- Explorer with benchmark/experiment views + research website
- Reproducible experiment workflow
- Real-LLM sanity validation (Gemini)

## Documentation

The complete research documentation and project maps are available in the `documentation/` directory.

- [📚 Master Documentation Index](documentation/README.md)
- [🗺️ Project Map](documentation/PROJECT_MAP.md)

## Quick Start

### Install
```bash
pip install -e ".[dev]"
```

### One-Command Demo
```bash
python -m captain.demo
```

Exercises the full pipeline: Agent → Tracing → Evidence → Failure Analysis → CEE → Cascade → Benchmark → Experiment → JSON export.

Results are saved to `captain_results/`.

### Launch Explorer
```bash
python -m captain.explorer
```

Open http://127.0.0.1:5000 to inspect runs, evidence graphs, benchmark results, and experiments.

### Run Tests
```bash
pytest
ruff check .
mypy captain
```

## Architecture

| Layer | Description | Status |
|-------|-------------|--------|
| A — Agent Execution | Planner, reasoner, memory, tools, LLM abstraction | ✅ |
| B — Observation | Trace collector, provenance extraction | ✅ |
| C — Representation | Execution graph, validation, analysis | ✅ |
| D — Counterfactual Analysis | Intervention model, replay engine | ✅ |
| E — Evidence & Failure | Evidence identity/lineage, failure model, CEE, cascade | ✅ |
| F — Research Evaluation | Benchmarks, baselines, oracle, statistical validation | ✅ |
| G — Presentation | Explorer, benchmark demo, experiment runner, reproducibility | ✅ |

## Reproducibility Workflow

1. Install dependencies: `pip install -e ".[dev]"`
2. Run deterministic demo: `python -m captain.demo`
3. Launch Explorer: `python -m captain.explorer`
4. Run a small experiment (via Explorer or API):
   ```bash
   curl -X POST http://127.0.0.1:5000/api/experiment \
     -H "Content-Type: application/json" \
     -d '{"master_seed": 42, "instances_per_family": 3, "families": ["BF-A","BF-B","BF-C"], "methods": ["B1","B2","A2","A4"]}'
   ```
5. Export results: `curl -X POST http://127.0.0.1:5000/api/experiment/export`
6. Inspect results in Explorer or in `captain_results/`

All experiments use deterministic seeds. Master seed 42 is the default.

## Repository Organization
- `captain/core/`: Configuration, logging, exception hierarchy.
- `captain/agent/`: Reference multimodal agent (planner, reasoner, memory, tools).
- `captain/adapters/`: External system adapters (LLM provider abstraction).
- `captain/models/`: Canonical event, artifact, and execution data model.
- `captain/tracing/`: Trace collector and traced-agent wrapper.
- `captain/storage/`: Trace persistence and query layer.
- `captain/provenance/`: Provenance extraction and lineage query.
- `captain/graph/`: Execution graph model, builder, validation, and analysis.
- `captain/evidence/`: Evidence identity, lineage, and flow graph.
- `captain/intervention/`: Counterfactual intervention specification.
- `captain/replay/`: Counterfactual replay engine.
- `captain/failures/`: Failure model, analyzer, candidate screening.
- `captain/analysis/`: CEE estimator, cascade estimator, greedy selector.
- `captain/benchmarks/`: Scenarios, baselines, oracle, benchmark runner.
- `captain/experiments/`: Experiment runner, statistics, reproducibility.
- `captain/explorer/`: Local browser-based trace/experiment explorer.
- `captain/demo.py`: One-command reproducible demonstration.
- `docs/`: Architecture, research spec, algorithms, experiments, data model.
- `project_state/`: Project status tracking.
- `tests/`: Unit and integration test suites (682 tests).

## Known Limitations

1. **Deterministic IDs only in benchmarks**: Benchmark scenarios use `deterministic_ids()` context manager. Outside this context, IDs use `uuid.uuid4()`.
2. **Stdlib-only statistics**: No numpy/scipy — Wilcoxon uses normal approximation, bootstrap is percentile-only.
3. **MockLLM for benchmarks**: Benchmark campaign uses deterministic `MockLLMProvider`. Real-LLM sanity validation (Gemini 3.6-flash) exists but is a controlled prompt-level check, not full end-to-end agent replay.
4. **Controlled simulation**: All experiments run in a controlled synthetic environment, not production agent deployments.

## License
MIT
