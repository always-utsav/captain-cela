# Experimental Evolution

The experimental methodology of the CAPTAIN/CELA project expanded from simple functional tests to a rigorous, multi-family benchmark suite with robust statistical validation.

## Early Evaluation (Stages 1-13)
Initially, evaluation consisted purely of unit testing functionality: ensuring the tracer recorded events, the graph built correctly, and the replay engine executed without crashing. There was no scientific measurement of attribution accuracy.

## The Benchmark Framework (Stage 16)
Stage 16 introduced formal, comparative evaluation. A hidden `CausalMechanismSpec` generated scenarios with known ground truth, which was strictly isolated from the evaluation methods.
Initially, 6 benchmark families were created:
- **BF-A**: Single channel (single cause + distractor)
- **BF-B**: Redundant OR logic
- **BF-C**: Complementary AND logic
- **BF-D**: Distractor heavy
- **BF-E**: Cascade (multi-hop)
- **BF-F**: Cost-asymmetric

The framework evaluated standard dimensions: Attribution, Localization, Prevention, and Discrimination.

## Baselines and Methods Defined
A strict set of methods was defined for comparison:
- **B1**: Random
- **B2 / A1**: Provenance-only (select by connectivity)
- **B3 / A2**: CEE-rank (rank by individual CEE)
- **A3**: CELA-cascade
- **A4**: CELA-greedy (budget constrained)
- **A5**: CELA-full
- **B5**: Exhaustive Oracle (for regret computation, not a fair baseline)

## Statistical Rigor (Stage 17)
To ensure validity, Stage 17 introduced formal statistics. The independent experimental unit was defined as the *scenario instance*, not individual replays. 
Tests were implemented from scratch:
- Bootstrap percentile CI (2000 resamples)
- Paired Wilcoxon signed-rank (continuous metrics)
- Permutation tests (binary/bounded metrics)
- Holm-Bonferroni corrections for multiple comparisons.

## The Full Campaign (Research Stage 2)
The final campaign significantly expanded the benchmark suite to 11 families, adding:
- **BF-G**: Shared source (The primary granularity experiment)
- **BF-H**: Convergent mixed inputs (originally mislabeled "branching")
- **BF-I**: Convergent single causal
- **BF-J**: Parallel sources (originally mislabeled "root vs symptom")
- **BF-K**: Downstream persistence (originally mislabeled "downstream repair")

In total, 275 scenarios were run across 5 seeds, producing the final data artifacts.

## Real-LLM Validation Restricting
A crucial evolution in experimental scope was the handling of real LLMs. Originally envisioned as an end-to-end validation, it was narrowed significantly by the final freeze. The Real-LLM experiment (Gemini 3.6-flash) was explicitly re-labeled as a **"Sanity Check"** (Claim C7). It did not run the CAPTAIN agent or replay engine; it used handcrafted prompts purely to validate the theoretical premise that LLM outputs genuinely change when input evidence is manipulated.
