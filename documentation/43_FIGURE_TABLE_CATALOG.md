# Figure and Table Catalog

This catalog lists all figures and tables used in the research, mapping them to data sources and claims.

## Figures

| Figure | Data Source | Claims Supported | Generating Script |
|--------|------------|-----------------|-------------------|
| `fig_attribution` | `benchmark_seed_42.json` | — (descriptive) | `figures.py` |
| `fig_granularity` | `granularity_experiment.json` | C1, C2 | `figures.py` |
| `fig_collateral` | `granularity_experiment.json` | C2 | `figures.py` |
| `fig_convergence` | `replay_convergence.json` | C6 (trivially) | `figures.py` |
| `fig_scalability` | `scalability.json` | — (descriptive) | `figures.py` |
| `fig_negative_controls` | `negative_controls.json` | C4 | `figures.py` |
| `fig_real_llm` | `real_llm_validation.json` | C7 | `figures.py` |

## Tables

| Table | Data Source | Description |
|-------|-------------|-------------|
| Competitor Matrix | `competitor_matrix.csv` | Comparison of 12+ systems on various causal and tracking capabilities. |
| Final Benchmarks | `26_FINAL_SCIENTIFIC_FREEZE.md` | Description of 11 benchmark families (BF-A to BF-K). |
| Final Baselines | `26_FINAL_SCIENTIFIC_FREEZE.md` | Definitions of B1-B5 and A1-A5 estimators. |
