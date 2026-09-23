# CAPTAIN — Stage 0: Repository Foundation & Architecture Contract

## 1. Purpose of This Stage

This is Stage 0 of the CAPTAIN project.

CAPTAIN stands for:

**Counterfactual Analysis Platform for Trace-based Investigation of Autonomous Agent Cascades**

CAPTAIN is a research-oriented engineering platform for studying how failures propagate through autonomous multimodal AI-agent executions.

This stage DOES NOT implement the research algorithms, autonomous agent, tracing engine, provenance system, execution graph, replay engine, failure propagation algorithm, benchmark system, or dashboard.

Stage 0 exists solely to establish a stable, extensible, testable repository foundation that all later CAPTAIN modules will inherit.

The implementation must therefore prioritize:

* architectural stability;
* modularity;
* explicit interfaces;
* reproducibility;
* testability;
* configuration management;
* documentation;
* strict separation between research logic and infrastructure;
* minimal unnecessary dependencies.

Do not prematurely implement future CAPTAIN functionality.

---

# 2. Project Research Context

CAPTAIN supports research into:

**Counterfactual Failure Propagation Modeling in Autonomous Multimodal Agents**

The central research question is:

> How can counterfactual reasoning model and explain the propagation of multimodal evidence through recurrent execution graphs in autonomous multimodal agents, enabling more accurate diagnosis of cascading failures than existing root-cause attribution methods?

CAPTAIN is the engineering platform used to implement, evaluate, and demonstrate this research.

The project should eventually answer questions such as:

* Where did erroneous information originate?
* Through which reasoning and execution events did it propagate?
* Which downstream events were causally affected?
* What happens if an earlier event is removed, replaced, or corrected?
* Which nodes amplify failures most strongly?
* How deep is a failure cascade?
* How severe is a cascade?
* Which intervention could have prevented the final failure?

Do NOT attempt to answer these questions in Stage 0.

They are provided only so that the architecture does not accidentally prevent later research implementation.

---

# 3. Long-Term CAPTAIN Architecture

CAPTAIN will eventually contain the following major capabilities.

## Layer A — Agent Execution

A controlled autonomous multimodal reference agent.

Future responsibilities include:

* accepting multimodal tasks;
* reasoning;
* memory;
* planning;
* retrieval;
* tools;
* external environment interaction;
* generating final outputs.

This is NOT implemented in Stage 0.

---

## Layer B — Observation

Future components:

### Execution Trace Collector

Records agent execution events.

### Multimodal Provenance Extractor

Tracks the origin and transformation of information across modalities.

Neither is implemented in Stage 0.

---

## Layer C — Representation

Future components:

### Execution Graph Builder

Transforms traces and provenance into typed execution graphs.

### Graph Query Layer

Provides traversal and dependency analysis.

Neither is implemented in Stage 0.

---

## Layer D — Counterfactual Analysis

Future components:

### Intervention Model

Defines counterfactual modifications.

### Replay Infrastructure

Restores execution state and re-executes selected portions.

### Counterfactual Replay Engine

Produces factual/counterfactual execution pairs.

None is implemented in Stage 0.

---

## Layer E — Failure Analysis

Future components:

### Failure Representation

Formalizes failure types.

### Failure Propagation Model

Models how failures propagate.

### Cascade Analyzer

Computes propagation and cascade metrics.

### Bottleneck Detector

Identifies high-impact propagation nodes.

None is implemented in Stage 0.

---

## Layer F — Research Evaluation

Future components:

* benchmark adapters;
* attack/failure scenarios;
* baseline implementations;
* experiment orchestration;
* ablation experiments;
* statistical analysis;
* result export.

Not implemented in Stage 0.

---

## Layer G — Presentation

Future components:

* backend API;
* interactive dashboard;
* graph visualization;
* trace explorer;
* counterfactual comparison;
* experiment reports.

Not implemented in Stage 0.

---

# 4. Fundamental Architectural Rule

CAPTAIN must NOT become tightly coupled to one:

* LLM;
* multimodal model;
* vector database;
* agent framework;
* graph database;
* benchmark;
* frontend;
* external API.

Future implementations must use adapters/interfaces wherever external systems are involved.

For example:

BAD:

```python
class TraceCollector:
    def collect_langgraph_event(...):
        ...
```

BETTER:

```python
class TraceCollector:
    def record_event(...):
        ...
```

with framework-specific adapters elsewhere.

The core research system must operate on CAPTAIN's own canonical internal representations.

---

# 5. Repository Structure

Create the following initial repository structure.

```text
CAPTAIN/
│
├── README.md
├── CLAUDE.md
├── LICENSE
├── .gitignore
├── .env.example
├── pyproject.toml
│
├── captain/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   ├── tracing/
│   │   └── __init__.py
│   │
│   ├── provenance/
│   │   └── __init__.py
│   │
│   ├── graph/
│   │   └── __init__.py
│   │
│   ├── counterfactual/
│   │   └── __init__.py
│   │
│   ├── failures/
│   │   └── __init__.py
│   │
│   ├── analysis/
│   │   └── __init__.py
│   │
│   ├── benchmarks/
│   │   └── __init__.py
│   │
│   ├── experiments/
│   │   └── __init__.py
│   │
│   └── adapters/
│       └── __init__.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   ├── integration/
│   │   └── __init__.py
│   └── fixtures/
│       └── .gitkeep
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RESEARCH_SPEC.md
│   ├── DATA_MODEL.md
│   ├── ALGORITHMS.md
│   ├── EXPERIMENTS.md
│   └── decisions/
│       └── README.md
│
├── project_state/
│   ├── CURRENT_STATE.md
│   ├── COMPLETED_MODULES.md
│   ├── NEXT_TASK.md
│   └── CHANGELOG.md
│
├── scripts/
│   └── .gitkeep
│
├── benchmarks/
│   └── .gitkeep
│
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   ├── processed/
│   │   └── .gitkeep
│   └── artifacts/
│       └── .gitkeep
│
└── docker/
    └── .gitkeep
```

Do not add major directories without a concrete Stage 0 reason.

Do not create the frontend yet.

Do not create databases yet.

Do not create agent implementations yet.

---

# 6. Python Requirements

Use modern Python.

Target:

**Python >= 3.11**

Use `pyproject.toml` as the Python project configuration.

Do not use both `requirements.txt` and `pyproject.toml` as competing dependency sources.

Keep runtime dependencies minimal.

Stage 0 should preferably need only infrastructure-oriented dependencies.

Appropriate dependencies may include:

* pydantic
* pydantic-settings

Development dependencies may include:

* pytest
* pytest-cov
* ruff
* mypy

Do NOT install future dependencies merely because they may eventually be useful.

Specifically do NOT add unless Stage 0 truly requires them:

* langgraph;
* langchain;
* llama-index;
* transformers;
* torch;
* chromadb;
* faiss;
* neo4j;
* networkx;
* fastapi;
* streamlit;
* React-related tooling;
* OpenTelemetry;
* ML experiment frameworks.

Those belong to later stages.

---

# 7. Core Configuration

Implement:

```text
captain/core/config.py
```

using `pydantic-settings`.

Create a central settings object.

At minimum support:

* application name;
* environment;
* log level;
* data directory;
* artifacts directory;
* debug mode.

Use environment-variable configuration.

Use a prefix such as:

```text
CAPTAIN_
```

Example:

```text
CAPTAIN_LOG_LEVEL=INFO
```

Paths should use `pathlib.Path`.

Configuration must NOT silently create large side effects during import.

Provide sensible local defaults.

Secrets must never be committed.

---

# 8. Environment Example

Create:

```text
.env.example
```

containing only non-secret example configuration.

Example categories:

```text
CAPTAIN_ENVIRONMENT=
CAPTAIN_LOG_LEVEL=
CAPTAIN_DEBUG=
CAPTAIN_DATA_DIR=
CAPTAIN_ARTIFACTS_DIR=
```

No API keys are needed in Stage 0.

---

# 9. Logging

Implement:

```text
captain/core/logging.py
```

CAPTAIN must use Python's standard `logging` package as its foundational logging abstraction.

Provide a function similar to:

```python
configure_logging(...)
```

and/or:

```python
get_logger(name)
```

Requirements:

* log level configurable;
* predictable formatting;
* no duplicate handlers;
* library modules must not configure logging repeatedly;
* no print statements for infrastructure logging;
* logging setup must remain extensible for future structured tracing.

Do NOT confuse normal application logging with CAPTAIN's future execution trace system.

They are different concepts.

---

# 10. Exceptions

Create:

```text
captain/core/exceptions.py
```

Define a small exception hierarchy.

At minimum:

```text
CaptainError
ConfigurationError
ValidationError
StorageError
AdapterError
```

Do not create dozens of speculative exceptions.

All custom exceptions should inherit from:

```text
CaptainError
```

where appropriate.

---

# 11. Package Metadata

`captain/__init__.py` should expose only minimal package metadata.

For example:

```python
__version__
```

Avoid importing large internal modules from package initialization.

---

# 12. README.md

Create a professional root README.

It must explain:

## CAPTAIN

Counterfactual Analysis Platform for Trace-based Investigation of Autonomous Agent Cascades.

Include:

* project overview;
* research motivation;
* distinction between research contribution and engineering platform;
* high-level future architecture;
* current implementation status;
* installation instructions;
* test instructions;
* repository organization;
* research disclaimer.

The README must explicitly say that Stage 0 is infrastructure only.

Do not claim that counterfactual failure propagation has already been implemented.

Do not fabricate experimental results.

Do not claim publication or benchmark superiority.

---

# 13. CLAUDE.md — Persistent Coding-Agent Contract

Create:

```text
CLAUDE.md
```

This is one of the most important files in the repository.

It must instruct future coding agents to follow these rules.

## Mandatory Startup Procedure

Before modifying code, read:

1. `CLAUDE.md`
2. `README.md`
3. `docs/ARCHITECTURE.md`
4. `docs/RESEARCH_SPEC.md`
5. `project_state/CURRENT_STATE.md`
6. `project_state/COMPLETED_MODULES.md`
7. `project_state/NEXT_TASK.md`

Then inspect the relevant existing source code and tests.

Never assume the repository matches an earlier prompt.

The repository itself is the source of truth.

## Scope Discipline

Implement only the requested stage.

Do not implement future modules prematurely.

Do not redesign completed modules simply because another design is preferred.

## Interface Stability

Existing public interfaces should remain stable unless the task explicitly requires modification.

If an interface must change:

* document why;
* update affected tests;
* update architecture documentation;
* record the change in `CHANGELOG.md`.

## Research Integrity

Never fabricate:

* research results;
* benchmark scores;
* citations;
* algorithm performance;
* statistical significance;
* novelty claims.

Do not silently turn speculative ideas into established research claims.

## Dependency Discipline

Do not introduce dependencies without necessity.

When introducing one:

* explain why the standard library/current dependencies are insufficient;
* add it through the canonical project dependency configuration;
* document significant architectural dependencies.

## Testing

Every implemented behavior must have appropriate tests.

Before declaring completion:

* run relevant tests;
* run the complete test suite where practical;
* run linting;
* run static type checks.

Never claim tests passed unless they were actually executed.

## Documentation

After completing a stage, update:

* `project_state/CURRENT_STATE.md`
* `project_state/COMPLETED_MODULES.md`
* `project_state/NEXT_TASK.md`
* `project_state/CHANGELOG.md`

when applicable.

## No Hidden Failure

If something cannot be completed:

* state exactly what remains;
* explain why;
* do not mark the module complete.

## Research-Code Separation

Generic engineering infrastructure must remain separate from research algorithms.

Future research algorithms should live in clearly identifiable modules and must correspond to documented specifications.

## Determinism

Research-related functionality should be deterministic wherever possible.

Random behavior must eventually support explicit seeds.

## External Systems

External model/framework/database integrations must eventually be implemented through adapters.

CAPTAIN core logic must not depend directly on vendor-specific response objects.

---

# 14. ARCHITECTURE.md

Create:

```text
docs/ARCHITECTURE.md
```

Document the intended layered architecture.

At minimum discuss:

1. reference agent layer;
2. observation layer;
3. canonical data model;
4. provenance layer;
5. graph layer;
6. counterfactual layer;
7. failure-analysis layer;
8. experiment layer;
9. API/presentation layer.

Explicitly mark unimplemented layers.

Include the architectural principle:

> External systems communicate with CAPTAIN through adapters, while CAPTAIN's core research logic operates on canonical internal representations.

Also document the intended dependency direction.

Higher-level components may depend on lower-level abstractions.

Avoid circular dependencies.

A rough intended direction is:

```text
External Systems
       │
       ▼
    Adapters
       │
       ▼
Canonical CAPTAIN Models
       │
       ├───────────────┐
       ▼               ▼
    Tracing        Provenance
       │               │
       └───────┬───────┘
               ▼
             Graph
               │
               ▼
        Counterfactual
               │
               ▼
            Failure
               │
               ▼
            Analysis
               │
               ▼
          Experiments
```

This diagram is conceptual and may evolve through documented architectural decisions.

---

# 15. RESEARCH_SPEC.md

Create:

```text
docs/RESEARCH_SPEC.md
```

Record the research problem without pretending the final algorithm has already been designed.

Include:

## Research Area

Autonomous multimodal agents, causal/counterfactual analysis, failure diagnosis, AI-agent reliability.

## Research Question

Use the research question specified earlier.

## Current Hypothesis

State cautiously that execution-level counterfactual reasoning over multimodal provenance graphs may enable richer diagnosis of cascading failures than isolated root-cause attribution.

This is a hypothesis to test, not a proven result.

## Intended Research Outputs

Potential outputs include:

* formal failure propagation representation;
* counterfactual propagation algorithm;
* cascade metrics;
* bottleneck identification method;
* evaluation methodology.

Explicitly label them as planned.

## Research vs Engineering

Explain that:

CAPTAIN = engineering artifact.

Counterfactual failure propagation methodology = research contribution.

The two must not be treated as identical.

---

# 16. DATA_MODEL.md

Create:

```text
docs/DATA_MODEL.md
```

Do NOT finalize the canonical event schema yet.

Instead explain that Stage 2/3 will formally define entities such as:

* Run;
* Event;
* Evidence;
* Artifact;
* Memory operation;
* Tool interaction;
* Reasoning event;
* provenance relationship;
* graph node;
* graph edge;
* intervention;
* failure annotation.

State that schemas remain intentionally unspecified in Stage 0.

This prevents premature schema decisions.

---

# 17. ALGORITHMS.md

Create:

```text
docs/ALGORITHMS.md
```

It should explicitly state:

**No novel CAPTAIN research algorithm has been finalized at Stage 0.**

Create placeholders for future documented algorithms:

* graph construction;
* factual/counterfactual alignment;
* failure propagation;
* cascade severity;
* bottleneck detection;
* intervention analysis.

Do not invent equations.

Do not generate arbitrary scoring formulas.

These algorithms will be specified deliberately in later research-design stages.

---

# 18. EXPERIMENTS.md

Create:

```text
docs/EXPERIMENTS.md
```

Document only the intended evaluation categories.

Potential benchmark families may eventually include:

* multimodal agent tasks;
* browser/web agent tasks;
* retrieval-based tasks;
* adversarial multimodal scenarios;
* prompt injection;
* poisoned retrieval;
* corrupted evidence;
* tool-result corruption.

Potential future metrics include:

* root-cause accuracy;
* propagation-path accuracy;
* propagation-depth error;
* counterfactual consistency;
* cascade severity;
* bottleneck-detection precision;
* minimal-intervention success.

All proposed CAPTAIN-specific metrics must be labeled as provisional until mathematically defined.

No experiments are performed in Stage 0.

---

# 19. Architecture Decision Records

Create:

```text
docs/decisions/README.md
```

Explain the future ADR process.

Significant architecture changes should eventually be recorded as:

```text
ADR-0001-title.md
ADR-0002-title.md
```

Each ADR should contain:

* context;
* decision;
* alternatives;
* consequences.

Do not create unnecessary ADRs in Stage 0 unless an actual architectural decision needs detailed justification.

---

# 20. Project State Files

## CURRENT_STATE.md

After Stage 0 completion it should clearly say:

* Stage 0 completed;
* repository foundation exists;
* configuration exists;
* logging exists;
* base exception hierarchy exists;
* documentation skeleton exists;
* test/tooling infrastructure exists;
* no CAPTAIN research functionality exists yet.

It should list what is NOT implemented.

---

## COMPLETED_MODULES.md

Record:

```text
Stage 0 — Repository Foundation & Architecture Contract
Status: COMPLETE
```

but only after all acceptance criteria pass.

---

## NEXT_TASK.md

Set the next intended stage to:

**Stage 1 — Reference Multimodal Agent Foundation**

Do NOT describe Stage 1 as already implemented.

Do not implement it.

---

## CHANGELOG.md

Record Stage 0 repository initialization.

Use a simple chronological structure.

---

# 21. Git Ignore

Create an appropriate Python `.gitignore`.

At minimum ignore:

* virtual environments;
* Python cache;
* pytest cache;
* mypy cache;
* ruff cache;
* coverage files;
* `.env`;
* IDE-specific local state where appropriate;
* build outputs;
* local generated data/artifacts where appropriate.

Do not ignore `.env.example`.

Preserve `.gitkeep` files needed for intentionally empty directories.

---

# 22. Data Directory Policy

Generated research artifacts should not accidentally be committed.

Configure `.gitignore` carefully so:

```text
data/raw/
data/processed/
data/artifacts/
```

can exist structurally while generated contents remain ignored.

Retain `.gitkeep`.

---

# 23. Testing Requirements

Create Stage 0 tests.

At minimum test:

### Configuration

* default settings instantiate correctly;
* environment overrides work;
* path configuration uses `Path`;
* invalid configuration produces appropriate behavior.

### Logging

* logger retrieval works;
* configured log level is respected;
* repeated configuration does not create duplicate handlers.

### Exceptions

* custom exception hierarchy behaves correctly.

Do not write meaningless tests simply to increase coverage.

---

# 24. Quality Tooling

Configure:

## pytest

Tests should be discoverable with:

```bash
pytest
```

## Ruff

Configure reasonable lint rules.

Do not enable an enormous rule set that creates unnecessary friction.

## mypy

Use useful but realistic static typing.

The project should begin with reasonably strict typing without making development impossible.

---

# 25. Required Validation

Before Stage 0 can be marked complete, execute the appropriate commands.

At minimum:

```bash
python -m pytest
```

and the configured Ruff command, for example:

```bash
ruff check .
```

and:

```bash
mypy captain
```

If formatting is configured, verify formatting as well.

Do not state that a command passed unless it actually ran successfully.

If the environment prevents execution, report that explicitly.

---

# 26. Acceptance Criteria

Stage 0 is complete only if all of the following are true:

* repository structure exists;
* package installs correctly;
* imports work;
* configuration system works;
* logging infrastructure works;
* exception hierarchy exists;
* root README accurately describes the project;
* persistent coding-agent instructions exist;
* architecture documentation exists;
* research specification exists;
* algorithm document does NOT invent the future algorithm;
* experiment document does NOT fabricate results;
* state tracking exists;
* tests exist;
* tests pass;
* linting passes;
* type checking passes;
* no future CAPTAIN module has been prematurely implemented.

---

# 27. Explicitly Forbidden in Stage 0

Do NOT implement:

* LangGraph agent;
* LLM calls;
* multimodal models;
* OCR;
* browser automation;
* RAG;
* memory system;
* trace collector;
* provenance extraction;
* NetworkX graph;
* Neo4j;
* counterfactual replay;
* failure propagation;
* cascade scoring;
* bottleneck detection;
* FastAPI;
* React;
* Streamlit;
* benchmark integrations;
* attack scenarios;
* experiment execution.

Do NOT add placeholder implementations pretending these capabilities exist.

Empty package boundaries and documentation are sufficient.

---

# 28. Final Completion Procedure

After implementation:

1. inspect the repository;
2. run tests;
3. run linting;
4. run type checking;
5. correct failures;
6. update project-state files;
7. verify no future module was implemented;
8. provide a concise completion report.

The completion report must contain:

### Files Created

List them.

### Files Modified

List them.

### Dependencies Added

List each dependency and why it was necessary.

### Validation

Provide the actual commands executed and whether they passed.

### Architectural Decisions

Mention any deviations from this specification.

### Outstanding Issues

List any remaining issues.

### Next Stage

State:

**Stage 1 — Reference Multimodal Agent Foundation**

Do not begin Stage 1.

---

# 29. Most Important Rule

This repository will be modified by multiple AI coding sessions.

Therefore:

**Do not optimize only for the current prompt. Optimize for continuity of the repository.**

Future agents must be able to understand the system from the repository itself without access to previous conversations.

The repository is the persistent project memory.
