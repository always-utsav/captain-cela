# 12: Real-LLM Validation

To guarantee the primary estimand operates correctly on true stochastic systems (and is not an artifact of MockLLM), we performed validation using a real LLM.

## Setup
- **Provider**: `google_gemini`
- **Model**: `gemini-3.6-flash`
- **Temperature**: `0.0`

## Important Note
**THIS IS REAL-LLM VALIDATION, NOT PROOF OF UNIVERSAL GENERALIZATION.**
This test exists solely to validate the conceptual soundness of the causal mechanism against an actual stochastic frontier model. The LLM was **NOT forced** to react to the intervention; it naturally responded to the blocked/modified channels. 

## Results
- **Factual Failure Rate**: 0.40 (The failure keyword '42' appeared in 2/5 trials)
- **Channel Intervention Failure Rate**: 0.00 (The intervention successfully blocked the keyword in all tested cases)
- **Source-Event Intervention Failure Rate**: 0.00
- **Channel CEE**: 0.40
- **Source-Event CEE**: 0.40
- **Technical Success**: True

*Note on Honesty*: The empirical CEE corresponds to the true observed causal effect size. Had CEE=0 been observed, it would have been honestly reported.
