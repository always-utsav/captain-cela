# 30: Real-LLM Validation

The Real-LLM Validation is a targeted sanity check designed to verify the foundational premise of CELA: that an LLM's output genuinely depends on the evidence content provided to it, and that replacing this content alters the outcome.

## Protocol
- **Provider**: Google Gemini API
- **Model**: `gemini-3.6-flash`
- **Temperature**: 0.0
- **Trials**: 5
- **Prompts**: Handcrafted for three conditions (factual, channel-blocked, source-blocked).
- **Evaluator**: Keyword presence ("42").

## Results
- **Channel CEE**: `0.40`
- **Source-Event CEE**: `0.40`

## Important Caveats
- **Not End-to-End**: This experiment does NOT run CAPTAIN's agent, the evidence graph generation, or the replay engine.
- **Scope limitation**: It uses one model, one scenario, and handcrafted prompts. It validates the theoretical premise of the intervention mechanism, not the full system's effectiveness in the wild.
