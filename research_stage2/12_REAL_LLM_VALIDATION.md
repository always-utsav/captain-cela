# 12: Real-LLM Validation (Controlled Sanity Check)

This experiment serves as a controlled real-LLM intervention sanity check. It does NOT run the CAPTAIN agent, evidence graph, or replay engine. Instead, it sends handcrafted prompts with and without the failure keyword to test whether the LLM's output actually changes when evidence is modified.

## Setup
- **Provider**: `google_gemini`
- **Model**: `gemini-3.6-flash`
- **Temperature**: `0.0`
- **Methodology**: Handcrafted prompts with/without failure keyword.

## Important Note
This validates the PREMISE that LLM outputs depend on evidence content. It does NOT prove CELA works end-to-end with real LLMs. 

## Limitations
- Only one model tested (`gemini-3.6-flash`).
- Uses handcrafted prompts rather than a true CAPTAIN trace.
- The replay engine and evidence graph are not utilized.

## Results
- **Factual Failure Rate**: 0.40 (The failure keyword '42' appeared in 2/5 trials)
- **Channel Intervention Failure Rate**: 0.00 (The intervention successfully blocked the keyword in all tested cases)
- **Source-Event Intervention Failure Rate**: 0.00
- **Channel CEE**: 0.40
- **Source-Event CEE**: 0.40
- **Technical Success**: True
