# Research Paper Map

This map aligns the project's evidence and claims to the structure of the final research paper.

## 1. Abstract & Introduction
- **Core Narrative:** Causal attribution in AI agents can be made more selective by intervening at the evidence-flow channel level rather than the source-event level.
- **Allowed Claims:** C1.
- **Unsupported Claims to Omit/Reframe:** Do not claim universal superiority or state that CELA beats baselines on all tasks (due to C3).

## 2. Related Work
- **Content:** Competitor comparison based on `competitor_matrix.csv` and `31_COMPETITOR_COMPARISON.md`.
- **References:** Who&When Pro, CAR, CausalFlow, AgentRx.

## 3. Problem Definition & Methodology
- **Content:** Definitions of `EvidenceFlowGraph`, channel-level intervention (`ARTIFACT_REPLACEMENT`), and CEE.
- **Allowed Claims:** C4 (Negative controls validate logic).

## 4. Benchmark & Setup
- **Content:** Introduction of the 11 benchmark families (BF-A through BF-K) and the deterministic `MockLLM` environment.
- **Data:** `26_FINAL_SCIENTIFIC_FREEZE.md` section 3.

## 5. Results & Granularity Comparison
- **Content:** Primary experiment showing channel vs. source-event interventions.
- **Allowed Claims:** C1, C2.
- **Figures:** `fig_granularity`, `fig_collateral`, `fig_attribution`.
- **Negative Result:** Explicitly report C3 (A5 not significantly better than B1 on overall causal_f1, p=0.1156).

## 6. Robustness & Scalability
- **Content:** Verification of stability across seeds and replay convergence.
- **Allowed Claims:** C5, C6 (noting C6 is trivially true due to determinism).
- **Figures:** `fig_convergence`, `fig_scalability`.

## 7. Real-LLM Validation
- **Content:** Sanity check using Google Gemini.
- **Allowed Claims:** C7.
- **Figures:** `fig_real_llm`.
- **Constraint:** Clearly state this is a sanity check, not a full end-to-end evaluation.

## 8. Limitations & Discussion
- **Content:** Outline limitations (MockLLM, limited real-LLM scope, unmet statistical significance on F1).

## 9. Conclusion
- **Content:** Reiterate that channel-level intervention allows more precise causal localization with reduced collateral damage.
