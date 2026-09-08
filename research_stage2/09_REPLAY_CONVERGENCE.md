# 09: Replay Convergence

This analysis verifies the stability of the Causal Evidence Estimand (CEE) as the number of Monte Carlo replays increases.

Data from `replay_convergence.json` (Seed 42):
- **1 Replay**: CEE = 1.0 (CI: 1.0-1.0)
- **3 Replays**: CEE = 1.0 (CI: 1.0-1.0)
- **5 Replays**: CEE = 1.0 (CI: 1.0-1.0)
- **10 Replays**: CEE = 1.0 (CI: 1.0-1.0)
- **20 Replays**: CEE = 1.0 (CI: 1.0-1.0)
- **50 Replays**: CEE = 1.0 (CI: 1.0-1.0)

**Analysis**:
Because the primary evaluation environment utilizes a deterministic `MockLLM`, the variance is inherently 0. As a result, CEE estimates converge immediately at 1 replay with a Confidence Interval width of 0.0. 

*Note: This is expected mathematical behavior for a deterministic system. Genuine stochastic convergence requires a stochastic model, which is addressed in Real-LLM validation.*
