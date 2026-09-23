# V2 Final Scientific Freeze — CAPTAIN/CELA

**Date**: 2026-09-23
**Status**: FROZEN FOR PAPER WRITING
**Predecessor**: V1 (tag CAPTAIN-CELA-RESEARCH-FREEZE-V1 at 27ed11a)

---

## Changes from V1

### New Experiments Implemented
1. **Pathway stress**: Controlled pathway-count experiment across BF-A/B/C/D/G
2. **Cascade experiment**: Individual vs joint intervention comparison (BF-B/C)
3. **Cost/utility sweep**: Budget efficiency analysis (BF-F)

### New Tests
- 10 weakness audit tests (`test_weakness_audit.py`)
- Total: 692 tests (was 682)

### New Documentation
- 65 documentation files in `documentation/`
- 7 historical documents
- Master index, project map, glossary, FAQ
- Complete claim-evidence matrix
- Paper blueprint (44_RESEARCH_PAPER_MAP.md)

### New Research Artifacts
- `research/comparison/competitor_matrix.csv` (12 systems)
- `research/comparison/comparison_protocol.md`
- `research/evidence/evidence_checksums.json` (SHA-256 for 27 files)
- `research/statistics/statistical_audit.json`
- `research/improvements/01_IMPROVEMENT_AUDIT.md`
- `research/improvements/02_IMPROVEMENT_PROPOSALS.md`
- `research/improvements/04_REJECTED_IMPROVEMENTS.md`

### Archive Operations
- `README_STAGE_0.md` → `documentation/archive/stages/`
- `project_state/COMPLETED_MODULES.md` → `documentation/archive/stages/`
- `project_state/NEXT_TASK.md` → `documentation/archive/stages/`
- `research/test_gemini.py` → `documentation/archive/generated/`
- Removed empty `.gitkeep` files from `benchmarks/`, `data/`, `docker/`, `scripts/`

---

## Final Research Question

Can causal attribution in autonomous AI-agent failure analysis be made more
selective by intervening at the evidence-flow channel level rather than at
the source-event level?

## Final Hypotheses

H1: Channel-level intervention is more selective than source-event-level
H2: CELA distinguishes causal from non-causal channels
H3: Real LLM outputs depend on evidence content (sanity)

## Final Benchmark

275 controlled scenario instances = 11 families × 5 seeds × 5 instances
+ 3 new experiment types (pathway stress, cascade, cost/utility)

## V2 Supported Claims

| ID | Claim | V1 Status | V2 Status |
|----|-------|-----------|-----------|
| C1 | Channel more selective | Supported | Supported |
| C2 | Channel preserves evidence | Supported | Supported |
| C3 | A5 > B1 on causal_f1 | Not supported | Not supported (p=0.1156) |
| C4 | Negative controls CEE=0 | Supported | Supported |
| C5 | Seed stability | Supported | Supported |
| C6 | Replay stability | Supported (trivially) | Supported (trivially) |
| C7 | Real-LLM CEE > 0 | Supported | Supported |

## Negative Results (Preserved)

1. C3: A5 vs B1 causal_f1 not significant (p=0.1156)
2. Replay convergence trivially true with deterministic MockLLM
3. AND-complementary single intervention may produce CEE=0 (design limitation)

## Competitor Analysis

12 systems analyzed. Key finding: CAPTAIN/CELA's evidence-channel
intervention granularity is distinct from step-level approaches.
No system provides directly comparable evaluation interfaces.
See `documentation/31_COMPETITOR_COMPARISON.md`.

## Statistical Audit

17 checks: 14 correct, 2 limited (sample size, power), 1 acceptable.
See `research/statistics/statistical_audit.json`.

## Weakness Audit

10 categories tested. All pass except:
- AND-complementary CEE=0 on single block (DESIGN_LIMITATION)
- Serial replay performance (ENGINEERING_LIMITATION)
See `research/improvements/01_IMPROVEMENT_AUDIT.md`.

## Rejected Improvements

5 proposals rejected with documented reasons:
1. Stochastic replay (changes evaluation paradigm)
2. Multi-agent cascade (architectural scope)
3. External benchmark porting (fairness risk)
4. Shapley attribution (computational cost)
5. Automatic scenario discovery (requires labeled data)

## Verification

- 692 tests passing
- ruff clean
- mypy clean (with documented type ignores)
- No API keys in repository
- .env properly gitignored
- Evidence checksums generated

## Reproducibility

```bash
python research/run_campaign.py          # Full V1 campaign
python captain/experiments/figures.py    # Regenerate figures
python captain/experiments/claims.py     # Regenerate claims
python research/evidence/generate_checksums.py  # Verify integrity
python research/statistics/statistical_audit.py # Statistical audit
python -m pytest tests/ -q               # Full test suite
```

## Exact Environment

- Python 3.11.9
- Windows-10-10.0.26200-SP0
- No external ML frameworks required for deterministic experiments
- Gemini API (google-generativeai 0.8.6) for real-LLM sanity check only
