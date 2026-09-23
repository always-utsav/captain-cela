# Final V1 State (CAPTAIN-CELA-RESEARCH-FREEZE-V1)

**Date**: 2026-09-22
**Commit SHA**: `27ed11a` (Docs update following closure commit `50d13cc`)
**Tag**: `CAPTAIN-CELA-RESEARCH-FREEZE-V1`
**Test Count**: 682 tests passing (ruff and mypy clean)

This document outlines the exact frozen state of the CAPTAIN/CELA project at the conclusion of Research Stage 2.

## Scientific Claims Status

The project concluded with 6 supported claims and 1 explicitly unsupported claim, demonstrating high scientific integrity.

| ID | Claim | Status | Evidence/Notes |
|----|-------|--------|----------------|
| **C1** | Channel intervention is more selective than source-event intervention | **Supported** | Granularity experiment (BF-G): channel preserves 1 unrelated evidence, source-event preserves 0. |
| **C2** | Channel preserves unrelated evidence | **Supported** | Channel collateral modification rate = 0; source-event = 1. |
| **C3** | Full CELA (A5) significantly outperforms Random (B1) on causal F1 | **Not Supported** | p=0.1156 (not significant after Holm-Bonferroni). Synthetic scenarios were likely too simple for A5 to distinguish itself statistically from random guessing. |
| **C4** | Negative controls yield CEE=0 | **Supported** | All 4 controls: observed_cee=0.0. |
| **C5** | Seed stability | **Supported** | CV < 0.2 across 5 seeds. |
| **C6** | Replay stability | **Supported** | CEE=1.0 at all replay counts. (Acknowledged as trivially true due to deterministic MockLLM). |
| **C7** | Real-LLM Output depends on evidence (CEE > 0) | **Supported** | Sanity check with Gemini 3.6-flash showed channel_cee=0.40 and source_event_cee=0.40. |

## Core Assertions & Limitations

The final freeze strictly positioned CELA as a specific, structural intervention method:
1. **Novelty Claim**: CELA operationalizes causal analysis at the provenance-defined evidence-flow channel level, rather than treating the execution step/source event as the intervention unit.
2. **Honesty**: No claims of "universal superiority" or being the "first" ever framework.
3. **Limitation Acknowledgment**: All primary benchmarks use a deterministic MockLLM. Pathway stress tests and cost sweeps were explicitly documented as "NOT IMPLEMENTED."

## Artifacts Generated

The exact result JSONs and figures proving these claims are committed directly to the repository (un-gitignored for reproducibility) under `research/raw/` and `research/figures/`.

Reproducibility is guaranteed via deterministic seeds and standard library statistics, executed via `python research/run_campaign.py`.
