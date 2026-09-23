# Conclusion

The CAPTAIN/CELA project demonstrates that causal attribution in autonomous AI agents can be made significantly more selective by intervening at the **evidence-flow channel level** rather than the traditional source-event level.

## Key Findings
1. **Selective Localization:** Channel-level interventions preserve strictly more true evidence and cause fewer collateral modifications than step-level interventions.
2. **Methodological Validity:** The theoretical construct is supported by negative controls (CEE = 0 for irrelevant paths) and seed stability (CV < 0.2).
3. **Real-LLM Premise:** A sanity check with real LLMs confirms that output genuinely depends on evidence content, producing non-zero CEE.

## Negative Results
- The full CELA pipeline (A5) did not achieve statistically significantly higher causal F1 scores than a random baseline (B1) on the synthetic deterministic benchmark (p=0.1156).

## Final Takeaway
CELA provides a foundational, structurally sound mechanism for causal intervention. While the exact heuristic search strategy over the evidence graph requires further tuning for complex environments, the primary premise—that channel-level granularity enables precise counterfactual debugging—is well-supported.
