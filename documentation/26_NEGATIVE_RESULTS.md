# 26: Negative Results

Transparency in reporting null or contradictory findings is a core tenet of the CAPTAIN/CELA project.

## 1. C3 Statistical Insignificance (A5 vs B1)
CELA-full (A5) does not achieve a statistically significantly higher `causal_f1` than the random baseline (B1), yielding a p-value of `0.1156` (after Holm-Bonferroni correction). This suggests that the controlled synthetic scenarios may be too simple for the full CELA pipeline to demonstrate a statistically significant advantage over random selection in this specific metric.

## 2. Replay Convergence is Trivially True
The observation that Counterfactual Effect Estimate (CEE) converges to 1.0 with a confidence interval of 0.0 across all replay counts is a direct artifact of using a deterministic MockLLM. It is mathematically guaranteed in a deterministic system and does not constitute evidence of stochastic convergence.

## 3. Real-LLM Validation is Not End-to-End
The Real-LLM experiment is purely a sanity check on the premise of evidence-dependence. It was conducted with handcrafted prompts on a single model (Gemini-3.6-flash) and does not involve the full CAPTAIN agent, evidence graph, or replay engine.

## 4. Unimplemented Experiments
Three experiments documented in configuration schemas were NOT implemented or executed:
- Pathway stress test
- Cascade/joint intervention test
- Cost/utility sweep test

## 5. Conceptual Mismatches in Benchmarks
- **BF-H**: Labeled "branching" but is topologically convergent.
- **BF-J**: Tests parallel independent sources, not a true root-vs-symptom cycle.
- **BF-K**: Tests downstream persistence of a failure rather than a genuine but ineffective repair attempt.
