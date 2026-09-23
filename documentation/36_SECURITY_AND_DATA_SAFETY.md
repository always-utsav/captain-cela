# Security and Data Safety

Security and data integrity are fundamental to the CAPTAIN/CELA experimental setup.

## API Key Management
- **No API keys in code:** API keys are never hardcoded in the repository.
- **Environment Variables:** All keys must be loaded via a `.env` file or environment variables.
- **Git Ignore:** The `.env` file is explicitly included in `.gitignore` to prevent accidental commits of sensitive credentials.

## Ground Truth Isolation
- **No Ground Truth Leakage:** The evaluation mechanisms and causal estimators (e.g., `CEEEstimator`, `CascadeEstimator`) do not have access to the ground truth `CausalMechanismSpec` during inference or metric calculation.
- Ground truth is strictly used post-hoc in `claims.py` and `figures.py` to evaluate the accuracy of the attribution methods.
- The `MockLLM` determines failure based strictly on the content of the state, without exposing the underlying logic to the intervention tools.

## Sandbox and Execution Safety
- Interventions (e.g., `ARTIFACT_REPLACEMENT`) are scoped strictly to the virtual `EvidenceFlowGraph` and do not execute arbitrary code or modify local files outside of the test environment.
