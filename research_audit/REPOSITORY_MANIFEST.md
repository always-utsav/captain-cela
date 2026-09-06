# REPOSITORY MANIFEST

**Project:** CAPTAIN/CELA
**Date:** 2026-09-04
**Total source files:** 63 .py (captain/) + 38 (tests/) = 101
**Total non-cache size:** ~1.48 MB
**Git:** NOT initialized (no .git directory)

---

## Root Files

| File | Size | Classification |
|------|------|----------------|
| .env.example | 188B | KEEP_AND_COMMIT |
| .gitignore | 333B | KEEP_AND_COMMIT |
| CLAUDE.md | 2.2KB | KEEP_AND_COMMIT |
| LICENSE | 1.1KB | KEEP_AND_COMMIT |
| README.md | 4.4KB | KEEP_AND_COMMIT |
| README_STAGE_0.md | 25KB | KEEP_AND_COMMIT |
| pyproject.toml | 809B | KEEP_AND_COMMIT |

---

## Source Directories (captain/)

| Directory | Files | Classification |
|-----------|-------|----------------|
| captain/ (root) | 2 (__init__, demo) | KEEP_AND_COMMIT |
| captain/adapters/ | 2 | KEEP_AND_COMMIT |
| captain/agent/ | 8 | KEEP_AND_COMMIT |
| captain/analysis/ | 3 | KEEP_AND_COMMIT |
| captain/benchmarks/ | 4 | KEEP_AND_COMMIT |
| captain/core/ | 4 | KEEP_AND_COMMIT |
| captain/counterfactual/ | 1 (__init__ only) | KEEP_AND_COMMIT |
| captain/evidence/ | 4 | KEEP_AND_COMMIT |
| captain/experiments/ | 3 | KEEP_AND_COMMIT |
| captain/explorer/ | 3 + 1 template | KEEP_AND_COMMIT |
| captain/failures/ | 3 | KEEP_AND_COMMIT |
| captain/graph/ | 5 | KEEP_AND_COMMIT |
| captain/intervention/ | 3 | KEEP_AND_COMMIT |
| captain/models/ | 6 | KEEP_AND_COMMIT |
| captain/provenance/ | 4 | KEEP_AND_COMMIT |
| captain/replay/ | 2 | KEEP_AND_COMMIT |
| captain/storage/ | 3 | KEEP_AND_COMMIT |
| captain/tracing/ | 3 | KEEP_AND_COMMIT |

---

## Tests (tests/)

| Directory | Files | Classification |
|-----------|-------|----------------|
| tests/ | 3 (__init__, integration/__init__, unit/__init__) | KEEP_AND_COMMIT |
| tests/unit/ | 35 test files | KEEP_AND_COMMIT |
| tests/fixtures/ | 1 (.gitkeep) | KEEP_AND_COMMIT |

---

## Documentation (docs/)

| File | Size | Classification |
|------|------|----------------|
| ALGORITHMS.md | 5.9KB | KEEP_AND_COMMIT |
| ARCHITECTURE.md | 13.5KB | KEEP_AND_COMMIT |
| DATA_MODEL.md | 28.1KB | KEEP_AND_COMMIT |
| EXPERIMENTS.md | 4.8KB | KEEP_AND_COMMIT |
| RESEARCH_SPEC.md | 20.7KB | KEEP_AND_COMMIT |
| decisions/README.md | 312B | KEEP_AND_COMMIT |

---

## Project State (project_state/)

| File | Size | Classification |
|------|------|----------------|
| CHANGELOG.md | 20KB | KEEP_AND_COMMIT |
| COMPLETED_MODULES.md | 33.3KB | KEEP_AND_COMMIT |
| CURRENT_STATE.md | 943B | KEEP_AND_COMMIT |
| NEXT_TASK.md | 291B | KEEP_AND_COMMIT |

---

## Generated Artifacts

| Directory | Contents | Classification |
|-----------|----------|----------------|
| captain_results/ | 12 experiment JSONs + traces/ | GENERATED_ARTIFACT / KEEP_BUT_GITIGNORE |
| captain_traces/ | 8 run JSONs | GENERATED_ARTIFACT / KEEP_BUT_GITIGNORE |

---

## Placeholder Directories

| Directory | Classification |
|-----------|----------------|
| benchmarks/ | KEEP_AND_COMMIT (.gitkeep only) |
| data/ | KEEP_AND_COMMIT (.gitkeep files only) |
| docker/ | KEEP_AND_COMMIT (.gitkeep only) |
| scripts/ | KEEP_AND_COMMIT |

---

## New Research Directories (created this session)

| Directory | Classification |
|-----------|----------------|
| research_audit/ | KEEP_AND_COMMIT |
| research_results/ | KEEP_BUT_GITIGNORE (raw data) |

---

## Cache Directories (auto-generated, must be gitignored)

| Directory | Classification |
|-----------|----------------|
| .mypy_cache/ | KEEP_BUT_GITIGNORE |
| .pytest_cache/ | KEEP_BUT_GITIGNORE |
| .ruff_cache/ | KEEP_BUT_GITIGNORE |
| __pycache__/ (16+ dirs) | KEEP_BUT_GITIGNORE |

---

## Secrets Scan

| Check | Result |
|-------|--------|
| .env file | NOT PRESENT (safe) |
| .env.example | Contains only placeholder config keys (safe) |
| API keys in source | NONE FOUND |
| Credentials in config | NONE FOUND |
| Git history secrets | N/A (no git repo) |

---

## Environment

| Property | Value |
|----------|-------|
| Python | 3.11.9 |
| OS | Windows 10 (10.0.26200) |
| pydantic | 2.10.4 |
| Flask | 3.1.0 |
| pytest | 9.1.1 |
| ruff | 0.16.1 |
| mypy | 2.3.0 |
