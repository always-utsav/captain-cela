# Evidence Package — CAPTAIN/CELA

This directory contains the complete evidence package for the
CAPTAIN/CELA research project.

## Structure

```
research/evidence/
    evidence_checksums.json    # SHA-256 checksums for all raw files
    generate_checksums.py      # Script to regenerate checksums
    README.md                  # This file
```

## Raw Evidence Location

All raw experiment results are in `research/raw/`:

| File | Description | Deterministic? |
|------|-------------|---------------|
| benchmark_seed_{42,123,456,789,1024}.json | 5-seed benchmark campaign | Yes |
| campaign_full.json | Campaign summary | Yes |
| granularity_experiment.json | Channel vs source-event | Yes |
| negative_controls.json | 4 negative controls | Yes |
| replay_convergence.json | 6-point replay sweep | Yes |
| scalability.json | 4-family runtime | Yes |
| real_llm_validation.json | Gemini sanity check | No (API-dependent) |
| experiment_manifest.json | Experiment configuration | Yes |
| claim_registry.json | Validated claims | Yes |

## Figures

All figures are in `research/figures/` (SVG + PNG).

## Traceability

Every paper claim traces to:

```
Claim -> Hypothesis -> Experiment -> Raw File -> Metric -> Statistic -> Figure
```

See `documentation/41_RESULTS_EVIDENCE_LEDGER.md` for the complete mapping.

## Verification

```bash
# Regenerate checksums
python research/evidence/generate_checksums.py

# Compare with committed checksums
# (manual diff of evidence_checksums.json)

# Regenerate all deterministic results
python research/run_campaign.py

# Regenerate figures
python captain/experiments/figures.py

# Regenerate claims
python captain/experiments/claims.py
```

## V1 Baseline

Tag: `CAPTAIN-CELA-RESEARCH-FREEZE-V1`
Commit: `27ed11a`

The V1 results are preserved permanently via the git tag.
