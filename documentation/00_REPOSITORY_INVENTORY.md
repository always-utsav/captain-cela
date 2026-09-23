# Repository Inventory

## Overview
This document provides a comprehensive inventory of every major file in the CAPTAIN repository, categorized by their current status and purpose.

## Classifications
* **A**: Active and scientifically required
* **B**: Active engineering artifact
* **C**: Historical but valuable
* **D**: Obsolete/duplicate
* **E**: Generated artifact
* **F**: Temporary/unnecessary

## Summary Counts
* **A (Active & Scientifically Required)**: 47+
* **B (Active Engineering Artifact)**: 50+
* **C (Historical)**: 5+
* **D (Obsolete/Duplicate)**: 5+
* **E (Generated Artifact)**: 16+
* **F (Temporary/Unnecessary)**: 5

## File Inventory

### Source Code (Mostly B, except where noted)
* `captain/__init__.py`, `demo.py` (B)
* `captain/adapters/` (`llm.py`, `gemini.py`, `__init__.py`) (B)
* `captain/agent/` (`executor.py`, `memory.py`, `planner.py`, `reasoner.py`, `tools.py`, `__init__.py`) (B)
* `captain/analysis/` (`cascade.py`, `estimator.py`, `__init__.py`) (B)
* `captain/benchmarks/` (`baselines.py`, `oracle.py`, `runner.py`, `scenarios.py` [A], `__init__.py`)
* `captain/core/` (`config.py`, `exceptions.py`, `logging.py`, `__init__.py`) (B)
* `captain/evidence/` (`builder.py`, `model.py`, `__init__.py`) (B)
* `captain/experiments/` (`campaign.py` [A], `claims.py` [A], `figures.py` [A], `runner.py` [A], `statistics.py` [A], `__init__.py` [B])
* `captain/explorer/` (`app.py`, `__init__.py`, `__main__.py`, `templates/*.html`) (B)
* `captain/failures/` (`analyzer.py`, `model.py`, `__init__.py`) (B)
* `captain/graph/` (`analysis.py`, `builder.py`, `model.py`, `validation.py`, `__init__.py`) (B)
* `captain/intervention/` (`model.py`, `__init__.py`) (B)
* `captain/models/` (`artifacts.py`, `events.py`, `ids.py`, `runs.py`, `__init__.py`) (B)
* `captain/provenance/` (`extractor.py`, `query.py`, `__init__.py`) (B)
* `captain/replay/` (`engine.py`, `__init__.py`) (B)
* `captain/storage/` (`file_store.py`, `__init__.py`) (B)
* `captain/tracing/` (`collector.py`, `traced_agent.py`, `__init__.py`) (B)

### Tests (All B)
* `tests/unit/`
* `tests/integration/`
* `tests/fixtures/`

### Documentation
* `docs/ALGORITHMS.md` [A]
* `docs/ARCHITECTURE.md` [B]
* `docs/DATA_MODEL.md` [B]
* `docs/EXPERIMENTS.md` [A]
* `docs/RESEARCH_SPEC.md` [A]
* `docs/decisions/` [C] - Historical ADRs
* `research_stage2/` (26 documents, all [A])

### Research Data
* `research/raw/*.json` [A] - 13 result files
* `research/figures/*.svg`, `*.png` [A/E] - 14 figures
* `research/run_campaign.py` [B]
* `research/run_real_llm.py` [A]
* `research/test_gemini.py` [F] - temporary test (Moved to archive)

### Configuration
* `.env` [B]
* `.env.example` [B]
* `pyproject.toml` [B]
* `.gitignore` [B]

### Project State
* `project_state/CHANGELOG.md` [C]
* `project_state/CURRENT_STATE.md` [B]
* `project_state/COMPLETED_MODULES.md` [D] (Moved to archive)
* `project_state/NEXT_TASK.md` [D] (Moved to archive)

### Other
* `README.md` [B]
* `LICENSE` [B]
* `CLAUDE.md` [C]
* `README_STAGE_0.md` [D] - duplicate/stale (Moved to archive)
* `benchmarks/.gitkeep` [F] (Deleted)
* `data/.gitkeep` [F] (Deleted)
* `docker/.gitkeep` [F] (Deleted)
* `scripts/.gitkeep` [F] (Deleted)
* `research_stage1/` [C/D]
* `research_stage1_1/` [C/D]
* `research_audit/` [C/D]
* `captain_results/` [E]
* `captain_traces/` [E]
