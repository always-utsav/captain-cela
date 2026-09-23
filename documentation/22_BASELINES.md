# 22: Baselines

The evaluation compares 10 attribution methods, comprising 5 baseline heuristics and 5 variants of the CELA framework.

## Standard Baselines

| Code | Name | Description |
|------|------|-------------|
| B1 | Random | Random candidate selection |
| B2 | Provenance-only | Select by provenance connectivity |
| B3 | CEE-rank | Rank by individual CEE |
| B4 | Cost-only | Select cheapest intervention |
| B5 | Oracle | Ground-truth selection (upper bound) |

## CELA Variants

| Code | Name | Description |
|------|------|-------------|
| A1 | CELA-provenance | Select by provenance connectivity |
| A2 | CELA-CEE | Rank by individual CEE |
| A3 | CELA-cascade | Cascade estimation |
| A4 | CELA-greedy | Greedy cascade selection |
| A5 | CELA-full | Full CELA pipeline |

### Documented Equivalences

- **A1 ≡ B2**: CELA-provenance is functionally equivalent to the Provenance-only baseline.
- **A2 ≡ B3**: CELA-CEE is functionally equivalent to the CEE-rank baseline.
