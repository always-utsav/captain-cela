# 25: Results

This document summarizes the quantitative results derived from the raw data.

## Granularity Comparison (BF-G)
Comparing channel-level (ARTIFACT_REPLACEMENT) vs. source-event-level (TOOL_RESULT_OVERRIDE) interventions:
- **Preserved Evidence**: Channel intervention preserves 1 benign evidence artifact; source-event preserves 0.
- **Collateral Modification**: Channel intervention causes 0 collateral modifications; source-event causes 1.

## Negative Controls
- All 4 negative controls passed perfectly.
- The observed Counterfactual Effect Estimate (CEE) was `0.0` for all controls, indicating no spurious causal attributions in the absence of genuine causality.

## Deterministic Replay Stability
- Evaluated on deterministic MockLLM.
- **Result**: CEE = 1.0 at all replay counts with a confidence interval width of 0.0.
- *Note*: This is trivially true due to the deterministic nature of the mock environment and serves as a sanity check rather than evidence of stochastic convergence.

## Scalability
- Evaluated across 4 benchmark families.
- **Result**: Intervention resolution takes <5ms per family.

## Real-LLM Validation (Sanity Check)
- Model: Gemini-3.6-flash.
- **Result**: Channel CEE = `0.40`, Source-event CEE = `0.40`.
- *Note*: This confirms that the LLM's output genuinely depends on the content of its evidence (verifying the premise of CELA).

## Comparative Performance (A5 vs B1)
- **Result**: The difference in `causal_f1` between CELA-full (A5) and Random baseline (B1) is **not statistically significant** (p=0.1156).
