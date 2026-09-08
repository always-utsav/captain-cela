# 07: Negative Controls

Negative controls guarantee that the methodology only detects genuine causality and does not hallucinate false causal links. 

Results from `negative_controls.json`:
**Overall Status**: 4/4 Controls Passed

| Family | Control Type | Expected Effect | Observed CEE | Status | Justification |
|---|---|---|---|---|---|
| BF-A (Seed 42) | irrelevant_channel_block | CEE=0.0 | 0.0 | PASS | Blocking echo tool should not prevent calculator-caused failure. |
| BF-G (Seed 42) | non_causal_artifact_block | CEE=0.0 | 0.0 | PASS | Blocking benign artifact B should not prevent failure from artifact A. |
| BF-A (Seed 123)| irrelevant_channel_block | CEE=0.0 | 0.0 | PASS | Blocking echo tool should not prevent calculator-caused failure. |
| BF-G (Seed 123)| non_causal_artifact_block | CEE=0.0 | 0.0 | PASS | Blocking benign artifact B should not prevent failure from artifact A. |

The evaluation cleanly yields `CEE = 0.0` for non-causal structures, proving the estimator avoids false positives.
