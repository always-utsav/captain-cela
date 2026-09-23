# Failed Approaches and Corrections

The CAPTAIN/CELA project documented and corrected several critical flaws and misconceptions during its development. Maintaining scientific honesty required explicit acknowledgement of these failures and their subsequent fixes.

## 1. CEE Insensitivity to Tool Results (Fixed in Stage 14.1)
**The Failure**: In Stage 14, the Counterfactual Evidence-Flow Effect (CEE) was initially completely insensitive to true tool-result interventions. If an event produced multiple artifacts, attempting to block just one artifact inadvertently blocked the entire mediating event, destroying multi-channel fidelity.
**The Correction**: In Stage 14.1, `channel_to_intervention()` was heavily modified to use an `EvidenceFlowGraph`. It was fixed to target the *source evidence's producing event* via `TOOL_RESULT_OVERRIDE` instead of the mediating event. This restored the ability to block A→B while preserving C→B.

## 2. Shared-Source Scenario Flaw (Fixed in Stage 1.1-B)
**The Failure**: The initial BF-G benchmark (Shared Source) failed to provide a genuine shared source. The scenario setup inadvertently created independent sources, undermining the primary experiment designed to prove channel-level superiority.
**The Correction**: Commit `98e6366` redesigned the multi-artifact generation in the benchmark to ensure a single tool call genuinely produced multiple artifacts, correctly stressing the granularity difference.

## 3. Incorrect Statistical Claims (Corrected at Scientific Freeze)
**The Failure**: Early documentation and code (e.g., `claims.py`) referred to using "t-tests" for statistical significance. However, t-tests assume normal distribution, which is invalid for binary bounded outcomes (like failure prevention).
**The Correction**: The code actually implemented paired permutation tests and Wilcoxon signed-rank tests. The documentation and claim registry were audited and corrected to match the actual, valid tests used.

## 4. Misinterpretation of Replay Convergence
**The Failure**: Initial experimental analysis misinterpreted the fact that CEE was stable across multiple replays as a sign of "stochastic convergence."
**The Correction**: It was explicitly acknowledged in the Final Scientific Freeze that because the project uses a deterministic `MockLLM`, replay convergence (CEE=1.0 at all counts with 0.0 variance) is *trivially true* and expected, not an empirical discovery of stability.

## 5. Negative Result on Claim C3
**The Failure**: The hypothesis (C3) that the full CELA pipeline (A5) would achieve statistically significantly higher causal F1 than the random baseline (B1) failed.
**The Correction**: Rather than hiding the result or p-hacking, the project logged C3 as explicitly **Unsupported** (p=0.1156, not significant after Holm-Bonferroni correction). It was hypothesized that the controlled synthetic scenarios were simply too easy, allowing random selection to perform competitively.

## 6. Benchmark Label Mismatches
**The Failure**: Several benchmark families were mislabeled compared to their actual topological implementation. BF-F's keyword logic was self-contradictory (any vs all). BF-H was called "branching" but was actually convergent.
**The Correction**: In the final freeze, BF-F was fixed. BF-H, BF-J, and BF-K were relabeled ("convergent with mixed inputs", "parallel independent sources", "downstream persistence") to accurately reflect the code.

## 7. claims.py validate() Bug
**The Failure**: The `validate()` function in `claims.py` was completely broken and failed to parse the actual JSON data formats output by the experiment runner.
**The Correction**: Rewritten during the final audit to correctly parse the data, ensuring the claim registry accurately reflected the raw output.
