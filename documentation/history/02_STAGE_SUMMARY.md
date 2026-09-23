# Stage Summary

The CAPTAIN/CELA project evolved through a series of discrete stages, each expanding the architecture from basic tracing up to rigorous statistical evaluation.

| Stage | Date | Objectives / Key Additions | Status / Notes |
|-------|------|----------------------------|----------------|
| **0** | 2026-08-04 | Repo foundation, architecture contract, config, logging, docs | Complete |
| **1** | 2026-08-07 | Reference multimodal agent, MockLLM, planner, memory, tools | Complete (65 tests) |
| **2** | 2026-08-07 | Canonical data model (events, execution, artifacts) | Complete (71 tests) |
| **3** | 2026-08-08 | TraceCollector, TracedAgent (observer wrapper) | Complete (45 tests) |
| **4** | 2026-08-09 | FileTraceStore, TraceQuery | Complete (40 tests) |
| **5** | 2026-08-09 | ProvenanceExtractor, ProvenanceQuery (hard provenance) | Complete (31 tests) |
| **6** | 2026-08-09 | ExecutionGraphBuilder | Complete (30 tests) |
| **7** | 2026-08-09 | GraphValidator, GraphAnalyzer | Complete (29 tests) |
| **8** | 2026-08-09 | Flask Explorer, vis-network visualization | Complete (15 tests) |
| **9** | 2026-08-09 | Intervention model (ARTIFACT_REPLACEMENT, EVENT_DISABLE) | Complete (33 tests) |
| **10** | 2026-08-09 | CounterfactualReplayEngine | Complete (21 tests) |
| **11** | 2026-08-18 | CELA research lock, hypothesis definition, baseline freeze | Complete |
| **12** | 2026-08-19 | EvidenceLineageBuilder, EvidenceFlowGraph | Complete (39 tests) |
| **13** | 2026-08-19 | FailureAnalyzer, candidate generation | Complete (38 tests) |
| **14** | 2026-08-19 | CEEEstimator, paired replay, BottleneckAnalyzer | Complete (31 tests) |
| **14.1** | 2026-08-19 | `channel_to_intervention` correction (multi-channel fidelity) | **Critical Fix** (14 tests) |
| **15** | 2026-08-20 | CascadeEstimator, GreedyCascadeSelector, utility/cost | Complete (33 tests) |
| **16** | 2026-08-30 | Benchmarks (BF-A to BF-F), Baselines B1-B5, A1-A5 | Complete (33 tests) |
| **17** | 2026-08-30 | statistics.py, ExperimentRunner, paired Wilcoxon/permutation | Complete (34 tests) |
| **18** | 2026-09-01 | demo.py, Explorer APIs, full integration | Complete (22 tests) |
| **1.1** | 2026-09-04 | Causal responsiveness validation | Complete |
| **1.1-B** | 2026-09-05 | Shared-source validation fix | **Critical Fix** (commit 98e6366) |
| **RS 2** | 2026-09-08 | Full campaign: 11 families, 275 scenarios, website | Complete (commit d5b4a24) |
| **Freeze** | 2026-09-22 | Audit, label corrections, C3 negative result confirmed | **Frozen** (commit 27ed11a, 682 tests) |
