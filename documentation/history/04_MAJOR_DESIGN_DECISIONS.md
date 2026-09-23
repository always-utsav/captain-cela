# Major Design Decisions

Throughout the CAPTAIN/CELA project, several critical architectural choices were made that defined the rigorous, conservative nature of the research methodology.

## 1. MockLLM over Real LLM for Benchmarks
All benchmark experiments use a deterministic `MockLLMProvider` rather than live calls to OpenAI/Anthropic/Google models.
- **Rationale**: Ensures perfect reproducibility and isolates the evaluation of the *attribution algorithm* from the inherent stochasticity of LLMs. Real LLMs introduce noise that would obscure whether a failure was caused by the intervention or by random generation variance.
- **Trade-off**: The synthetic scenarios are controlled and scripted. A "Real-LLM sanity check" (Stage 2) using Gemini 3.6-flash was added purely to validate the premise that LLM outputs genuinely depend on evidence, but not for end-to-end benchmarking.

## 2. Hard Provenance Only
The project strictly relies on "hard provenance" (structural data flow) rather than semantic provenance (LLM-judged relevance).
- **Rationale**: Hard provenance is structurally guaranteed by the tracing layer (`input_artifact_ids` and `output_artifact_ids`). It avoids relying on an LLM to judge its own causal dependencies, preventing circular reasoning and hallucination in the evaluation pipeline.

## 3. Strict Separation of Ground Truth (No Leakage)
The `ScenarioGroundTruth` and `CausalMechanismSpec` are never exposed to the baseline methods or the CELA pipeline.
- **Rationale**: Maintains absolute information parity. All methods (A1-A5, B1-B4) receive the exact same candidates from the `FailureAnalyzer`. The independent evaluator checks observable outputs only.

## 4. Immutable Baselines and Fresh IDs
Counterfactual replays never mutate the original baseline trace. Instead, fresh IDs are generated for all counterfactual events and artifacts, linked back via `parent_run_id`.
- **Rationale**: Preserves the integrity of the original failure trace. Multi-channel and paired replays require comparing the mutated run precisely against an unmodified reference.

## 5. Artifacts vs. Events (The Evidence Wrapper)
The data model explicitly separates Events (actions) from Artifacts (data), and the Evidence layer wraps these Artifacts without duplicating values.
- **Rationale**: This separation is the foundation of CELA. It allows the intervention engine to target a specific Artifact (the channel) via `ARTIFACT_REPLACEMENT` without having to disable the entire Event that produced it.

## 6. Stdlib-only Statistics
All statistical tests (bootstrap CI, Wilcoxon, permutation) were implemented from scratch using Python's standard library (math, random) without scipy/numpy dependencies.
- **Rationale**: Reduces dependency footprint and forces a deep, explicit understanding of the statistical methods being applied, ensuring tests exactly match the data assumptions (e.g., permutation for binary outcomes).
