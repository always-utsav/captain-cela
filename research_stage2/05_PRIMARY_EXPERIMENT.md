# 05: Primary Experiment (Granularity)

This experiment evaluates the core hypothesis on Family `BF-G`: Finer provenance-defined evidence-channel intervention vs coarse source-event-level intervention.

Based on actual results from `granularity_experiment.json` (Seed 42, `bf_g_42` and matching results across all 5 seeds):

## Channel Intervention
- **Type**: `artifact_replacement` (e.g., Target: `art_a792e50efa8a0013`)
- **Affected Evidence**: 1
- **Preserved Evidence**: 1
- **Collateral Modifications**: 0
- **CEE**: 1.0

## Source-Event Intervention
- **Type**: `tool_result_override` (e.g., Target: `evt_c87340c40e927f63`)
- **Affected Evidence**: 2
- **Preserved Evidence**: 0
- **Collateral Modifications**: 1
- **CEE**: 1.0

## Conclusion
Both interventions achieve `CEE = 1.0`, meaning they successfully block the failure pathway. However, **channel intervention is vastly more selective**: it successfully isolates the exact causal artifact (affecting 1, preserving 1, with 0 collateral), whereas source-event-level intervention unnecessarily modifies benign data (affecting 2, collateral = 1). This confirms the hypothesis that channel intervention affects fewer non-causal pathways.
