# CAPTAIN/CELA Project History

This document provides a chronological narrative of the CAPTAIN (and later CELA) project's evolution, from its foundation as a general multimodal agent tracing framework to its culmination as a rigorous scientific evaluation of evidence-flow intervention.

## Foundation & Tracing (Stages 0-8)
**August 4-9, 2026**

The project began (Stage 0) with the establishment of the repository foundation, architecture contract, and quality tooling (ruff, mypy, pytest). Quickly following, Stage 1 introduced a reference multimodal agent architecture, notably relying on a `MockLLM` for deterministic testing. 

Stages 2 through 4 built the core tracing infrastructure: establishing a canonical event and execution data model (Stage 2), creating the `TraceCollector` and `TracedAgent` (Stage 3), and adding a storage and query layer (Stage 4). 

Stages 5 to 7 added analytical layers on top of the traces: a multimodal provenance system to track artifact derivation (Stage 5), an Execution Graph builder (Stage 6), and graph analysis and validation tools (Stage 7). Stage 8 provided a basic Flask Explorer and vis-network UI to visualize these execution graphs.

## Counterfactual Interventions (Stages 9-10)
**August 9, 2026**

With the trace and graph foundations in place, the project pivoted towards counterfactual analysis. Stage 9 introduced the intervention model (`ARTIFACT_REPLACEMENT`, `TOOL_RESULT_OVERRIDE`, `EVENT_DISABLE`). Stage 10 built the `CounterfactualReplayEngine`, allowing the agent to be re-run from a trace while injecting these interventions and observing the resulting behavior.

## CELA Research Pivot & Analysis (Stages 11-15)
**August 18-20, 2026**

Stage 11 marked a major turning point: the "CELA Research Lock". The project officially focused its research scope onto CELA (Counterfactual Evidence-Lineage Attribution). Evidence-flow channels, rather than coarse execution steps, became the primary research object, and the core estimand was defined as CEE (Counterfactual Evidence-Flow Effect). 

Stages 12 and 13 built out the specific CELA capabilities: Evidence flow graphs based on hard provenance (Stage 12), and failure analyzers that generate candidate channel interventions (Stage 13). 

Stage 14 introduced the `CEEEstimator` and paired replay. Shortly after, a critical correction occurred in **Stage 14.1**. Initially, CEE estimation was insensitive to true tool-result interventions. The bridge logic was corrected so `channel_to_intervention()` correctly mapped to source artifact replacement (`TOOL_RESULT_OVERRIDE`) instead of just disabling the mediating event, achieving true multi-channel fidelity. 

Stage 15 introduced cascade estimation and greedy selection to optimize intervention sets based on a cost/utility model.

## Evaluation & Benchmarks (Stages 16-18)
**August 30 - September 1, 2026**

Stages 16 and 17 focused on rigorous comparative evaluation. Stage 16 introduced the benchmark framework (initially families BF-A to BF-F) and baselines (B1-B5, A1-A5). Ground truth leakage was strictly prevented. Stage 17 added robust stdlib-only statistical validation (permutation/Wilcoxon tests, Holm-Bonferroni corrections) and an automated ExperimentRunner.

Stage 18 integrated the full pipeline into a reproducible demo and added extensive Explorer API endpoints.

## Refinement & The Final Campaign (Stage 1.1 to Scientific Closure)
**September 4-22, 2026**

Post-Stage 18, critical validations were performed. Stage 1.1 validated causal responsiveness, and Stage 1.1-B (commit 98e6366) fixed a flaw in the multi-artifact shared-source scenario to ensure it provided a genuine shared source.

**Research Stage 2** (Sept 8) executed the full experimental campaign. The benchmark suite was expanded to 11 families (BF-A to BF-K), running 275 scenarios across 5 seeds. This stage also introduced paper-quality figures and a dedicated research website UI. 

**Scientific Closure** (Sept 22, commit 50d13cc and docs update 27ed11a) concluded the project. A rigorous audit revealed and corrected several misalignments between documentation and code (e.g., benchmark keyword logic, renaming misleading benchmark labels). It correctly reported that hypothesis C3 was negative (not statistically significant) and refined language around the real-LLM validation to explicitly frame it as a sanity check rather than full-system proof. The final state is frozen at 682 tests passing, with a focus on scientific honesty and transparency.
