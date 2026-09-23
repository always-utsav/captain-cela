# CAPTAIN Architecture Details

## Packages and Responsibilities
- `captain/models/`: Canonical data model (ExecutionRun, Event, Artifact, etc.).
- `captain/agent/`: Stage 1 reference multimodal agent.
- `captain/adapters/`: Interfaces for LLMs and tools.
- `captain/tracing/`: Collects execution traces into the canonical data model.
- `captain/storage/`: Stores and queries trace data.
- `captain/provenance/`: Extracts hard provenance (produced, consumed, derived).
- `captain/graph/`: Structural graph representations and validation.
- `captain/intervention/`: Intervention spec definitions (WHAT to change).
- `captain/replay/`: Re-executes runs with injected interventions.
- `captain/evidence/`: Information units over artifacts and flow graphs.
- `captain/failures/`: Identification of failures and candidate channels.
- `captain/analysis/`: CEE Estimation, Cascade Analysis, Bottleneck resolution.
- `captain/benchmarks/`: Scenario generators, baselines, and evaluation metrics.
- `captain/experiments/`: Multi-instance experimental runs and statistical validation.
- `captain/explorer/`: Presentation and visualization (Flask app).

## Interfaces and Dependencies
The architecture strictly enforces that external dependencies interface through adapters. The CELA layers (12-17) operate purely as an additive layer over the CAPTAIN core (1-10) without mutating observed data.
