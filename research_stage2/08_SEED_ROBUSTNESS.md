# 08: Seed Robustness

To ensure results are not statistical flukes driven by arbitrary initialization parameters, all families were evaluated across 5 distinct random seeds:
- `42`
- `123`
- `456`
- `789`
- `1024`

**Conclusion**: Across all 275 scenarios, the benchmark structural properties, method rankings, and granularity metrics remained stable across seeds. The selective advantage of channel intervention (BF-G) over source-event intervention was consistent regardless of the initialization state.
