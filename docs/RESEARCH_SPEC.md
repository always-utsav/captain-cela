# Research Specification

## 1. Research Problem

Autonomous multimodal agents execute sequences of observations,
reasoning, tool calls, and memory operations. When failures occur,
they propagate through the agent's execution trace via
information-bearing channels — not merely through step adjacency.

Existing failure-diagnosis methods typically attribute failures at
the granularity of execution steps. This conflates the execution
event (what happened) with the information transformation (what
evidence moved or changed). Consequently, step-level attribution
may identify *where* a failure manifested without explaining *how*
the failure-causing information propagated through the system.

The problem is: **How do we localize the specific
information-bearing channels through which failure-causing evidence
propagated, rather than merely identifying the execution steps
that participated in the failure?**

## 2. Research Question

> How can provenance-defined multimodal evidence-flow channels
> serve as intervention targets within autonomous-agent executions,
> enabling controlled counterfactual replay to estimate their
> contribution to downstream failure propagation and identify
> effective intervention points?

## 3. CELA Definition

**CELA — Counterfactual Evidence-Lineage Attribution.**

CELA is a research method that:

1. Represents agent execution as evidence flowing through
   provenance-defined channels (not merely steps).
2. Defines interventions on those evidence-flow channels.
3. Uses controlled counterfactual replay to measure the effect
   of channel-level interventions on downstream outcomes.
4. Localizes failure-propagation bottlenecks at the
   evidence-channel granularity.
5. Identifies intervention points for failure prevention.

## 4. CAPTAIN / CELA Distinction

**CAPTAIN** is the engineering platform:

- Reference agent (Stage 1)
- Canonical data model (Stage 2)
- Trace collection (Stage 3)
- Trace storage/query (Stage 4)
- Provenance extraction (Stage 5)
- Execution graph (Stages 6–7)
- Visualization (Stage 8)
- Intervention specification (Stage 9)
- Counterfactual replay (Stage 10)

**CELA** is the research method built on CAPTAIN:

- Evidence identity and lineage (Stage 12)
- Failure model and evidence-channel interventions (Stage 13)
- Causal estimation via controlled paired replay (Stage 14)
- Cascade prevention via greedy intervention (Stage 15)
- Benchmark and comparative evaluation (Stage 16)
- Scientific validation (Stage 17)

CAPTAIN provides the infrastructure.
CELA provides the research contribution.
They are related but not identical.

## 5. Primary Research Object

The primary CELA intervention unit is an **evidence-flow
channel**, not merely an execution step.

An evidence-flow channel represents an information-bearing
transformation or transfer between two evidence objects:

```
e = (E_i → E_j)
```

where:
- `E_i` is the source evidence object
- `E_j` is the target evidence object
- `e` represents the information transformation/channel

The execution event that caused the transformation remains
linked. Evidence-flow channels are not disconnected from the
execution graph — they are a layer on top of it:

```
Execution Event
    ↕ (produces/consumes)
Evidence Object
    ↕ (artifact/reference identity)
Artifact
    ↕ (provenance relationship)
Evidence-Flow Channel
```

## 6. Evidence Definition

An **evidence object** is an identifiable unit of information
that participates in agent execution. Evidence objects have:

- **Identity**: a unique ID traceable through provenance
- **Type**: categorized by the evidence ontology (§8)
- **Value**: the information content
- **Provenance**: how the evidence was created/derived
- **Producer**: the execution event that created it
- **Consumers**: the execution events that used it

In the current CAPTAIN implementation, evidence objects map to
`Artifact` instances in the canonical data model.

## 7. Evidence-Flow Edge Definition

An **evidence-flow edge** is a directed relationship between
two evidence objects that represents information
transformation or transfer:

```
edge = (source_evidence, target_evidence, channel_type, producing_event)
```

Properties:
- **Source**: the evidence object providing information
- **Target**: the evidence object receiving/derived from it
- **Channel type**: the nature of the transformation
- **Producing event**: the execution event that mediated it
- **Provenance method**: how the edge was established
- **Provenance confidence**: certainty of the relationship

In the current CAPTAIN implementation, evidence-flow edges
map to combinations of:
- `ProvenanceRecord` (PRODUCED, CONSUMED, DERIVED)
- `GraphEdge` (structural graph connections)
- Event→Artifact and Artifact→Event relationships

## 8. Evidence Ontology

The following minimal, extensible evidence ontology classifies
evidence objects by their role in agent execution:

| Evidence Type | Description | CAPTAIN Mapping |
|---------------|-------------|-----------------|
| OBSERVATION | Original input/sensory evidence | TEXT/IMAGE artifact from INPUT event |
| INTERPRETATION | Model-derived understanding | MODEL_OUTPUT artifact from REASONING event |
| MEMORY_EVIDENCE | Stored working memory content | Value from MEMORY_WRITE event |
| RETRIEVED_CONTEXT | Recalled/retrieved memory | Value from MEMORY_READ event |
| PLANNING_PREMISE | Basis for plan decisions | STRUCTURED_DATA from PLANNING event |
| TOOL_INPUT | Arguments/evidence sent to tool | Payload from TOOL_CALL event |
| TOOL_OUTPUT | Results returned from tool | TOOL_OUTPUT artifact from TOOL_RESULT event |
| DERIVED | Transformed/synthesized evidence | Any artifact with DERIVED provenance |

This ontology is extensible. Additional types (e.g., audio,
video, retrieval-augmented context) should be added only when
required by actual experiments, not for theoretical
completeness.

## 9. Hard Provenance (Primary)

CELA lineage reconstruction **must prioritize deterministic
hard provenance**:

- Artifact IDs
- Event IDs
- Memory keys
- Input/output artifact references
- Explicit tool argument references
- Producer event IDs
- Creation timestamps
- Execution event relationships (parent_event_id)
- Sequence numbers
- Explicit model-provided references

Hard provenance is the primary lineage mechanism. It is
deterministic, auditable, and reproducible.

## 10. Semantic Provenance (Future Optional Extension)

Semantic provenance may later supplement hard provenance using:

- Embedding similarity
- Lexical overlap / n-gram matching
- Semantic similarity scoring
- Model-assisted evidence linking

**Semantic provenance must NOT replace hard provenance.**

When semantic provenance is added, each derived relationship
must record:
- Provenance method (hard / semantic / hybrid)
- Provenance confidence score
- Provenance source identifier

This supports a critical future ablation:

| Condition | Provenance |
|-----------|-----------|
| A8 | Hard provenance only |
| A9 | Hard + semantic provenance |

## 11. Failure Definition

A **failure** is an execution outcome that deviates from the
intended or correct behavior. Operationally:

- A task-level failure: the agent produces an incorrect,
  incomplete, or harmful final response
- A step-level failure: an intermediate step produces
  incorrect intermediate evidence

Failure is defined by a **failure oracle** — a function
`F(run) → {0, 1}` that classifies execution outcomes:

- `Y = 1`: failure occurred
- `Y = 0`: no failure

The failure oracle is experiment-specific. For synthetic
benchmarks, ground-truth answers provide the oracle.
For real-world scenarios, human evaluation may be required.

## 12. Counterfactual Intervention Semantics

CELA interventions operate on evidence-flow channels, not
merely on execution steps.

**Step-level intervention** (existing / prior work):
> "What if step S had produced a different output?"

**Evidence-channel intervention** (CELA):
> "What if the evidence flowing through channel e had been
> different (or absent)?"

Channel-level interventions are implemented through the
existing CAPTAIN intervention types (Stage 9):

| CAPTAIN Intervention | Evidence-Channel Mapping |
|---------------------|-------------------------|
| ARTIFACT_REPLACEMENT | Replace evidence at channel source |
| TOOL_RESULT_OVERRIDE | Replace tool-output evidence |
| EVENT_DISABLE | Block the channel entirely |
| EVENT_OUTPUT_OVERRIDE | Replace channel output |

The key distinction: CELA selects *which* channels to
intervene on based on provenance-defined evidence lineage,
not merely based on step position.

## 13. Primary Estimand: CEE

The **Counterfactual Evidence-Flow Effect (CEE)** is the
primary causal estimand.

For an evidence-flow edge `e` with channel `C_e`:

```
CEE(e) = P(Y=1) − P(Y=1 | do(C_e = c_cf))
```

For a blocking intervention (channel removal):

```
CEE_block(e) = P(Y=1) − P(Y=1 | do(C_e = ∅))
```

The planned empirical paired estimator (Stage 14):

```
CEE_hat(e) = (1/N) Σ_r [Y_r − Y_r^cf]
```

where:
- `Y_r` is the factual outcome for run `r`
- `Y_r^cf` is the counterfactual outcome for run `r`
- `N` is the number of paired replays

**CEE is NOT implemented in Stage 11.** This section freezes
the specification for Stage 14 implementation.

## 14. Propagation Profile

For a lineage path `L = (e_1, e_2, ..., e_k)`:

```
Π(L) = [CEE(e_1), CEE(e_2), ..., CEE(e_k)]
```

The propagation profile is a **diagnostic representation**,
not a novel causal estimand. It visualizes how measured
effects distribute along a specific evidence-flow path.

It does NOT claim that individual CEE values along a path
are causally independent or that the profile constitutes a
new causal quantity beyond its individual components.

## 15. Propagation Bottleneck

The propagation bottleneck is the evidence-flow edge with
the largest measured causal effect within a failure-relevant
subgraph:

```
e* = argmax_{e ∈ E_F} CEE(e)
```

where `E_F` is the failure-relevant evidence-flow edge set.

**Constraints on the bottleneck claim:**

- Only statistically supported effects are eligible
- The bottleneck is relative to `E_F`, not globally optimal
- Ties are broken by provenance ordering
- The bottleneck may differ from both the failure origin
  and the final failure actuator — this is hypothesis H2

**Not implemented in Stage 11.** Documented as planned
Stage 14 functionality.

## 16. Greedy Cascade Intervention

The future prevention objective:

```
S* = argmin_S Cost(S)
subject to: P(Y=1 | do(S)) ≤ ε
```

The first implementation will use **greedy search**, not
globally optimal combinatorial optimization. Therefore the
result is a:

**GREEDY COUNTERFACTUAL CASCADE INTERVENTION**

unless mathematical optimality is established.

The greedy algorithm:
1. Rank channels by CEE
2. Greedily add the highest-CEE channel to the
   intervention set
3. Re-estimate failure probability after intervention
4. Stop when `P(Y=1 | do(S)) ≤ ε` or budget exhausted

**Not implemented in Stage 11.** Documented as planned
Stage 15 functionality.

## 17. Assumptions

CELA rests on the following assumptions:

**A-SUTVA**: Stable Unit Treatment Value Assumption.
Intervening on one evidence channel does not alter the
treatment assignment of other channels except through
the agent's execution mechanics.

**A-DETERMINISM**: Given the same LLM responses, tool
implementations, and task input, the agent execution is
deterministic. (Satisfied by MockLLMProvider in the current
implementation.)

**A-FAITHFULNESS**: The provenance graph faithfully
represents the actual information-flow structure of the
execution. (Satisfied by hard provenance; may be weakened
for semantic provenance.)

**A-MODULARITY**: The agent's execution can be decomposed
into identifiable evidence-producing and evidence-consuming
steps. (Satisfied by the Stage 1 reference agent
architecture.)

**A-REPLAY-VALIDITY**: Counterfactual replay under
intervention produces a valid alternative execution.
(Satisfied by Stage 10's full re-execution architecture.)

## 18. Identification Limitations

**Confounding**: Shared upstream evidence may create
spurious associations between channels. CELA mitigates
this through paired replay (same execution context) but
does not claim to eliminate all confounding.

**Interference**: In recurrent agents, intervening on one
channel may affect the agent's behavior on subsequent
cycles in ways not captured by channel-level analysis.

**Scope**: CELA is validated on the Stage 1 reference agent.
Generalization to arbitrary agent architectures requires
additional validation.

**Determinism**: The current implementation uses
MockLLMProvider. Extension to stochastic LLMs requires
repeated sampling and confidence intervals.

**Granularity**: Evidence-channel granularity may be too
coarse or too fine for some failure modes. The optimal
granularity is an empirical question.

## 19. Research Hypotheses

These are **working hypotheses subject to experimental
validation**, not established results:

**H1 — Causal Attribution**: Evidence-flow intervention can
localize failure-relevant information pathways more
precisely than step-only attribution.

**H2 — Propagation Localization**: The strongest
evidence-flow causal bottleneck can differ from both the
initial evidence origin and the final failure actuator.

**H3 — Intervention Effectiveness**: Intervening on
evidence-flow bottlenecks can reduce failure probability
while preserving more useful behavior than indiscriminate
intervention.

**H4 — Multimodal Advantage**: Explicit evidence lineage
can improve attribution in failures involving cross-modal
transformations compared with execution-step-only
representations.

## 20. Baselines

The following baselines are frozen for future comparative
evaluation (Stage 16):

| # | Baseline | Description |
|---|----------|-------------|
| B1 | Naive final-action | Attribute failure to the last action |
| B2 | Step-level counterfactual | Intervene on each step independently |
| B3 | CAR-style step intervention | Step do-interventions with stochastic replay |
| B4 | CausalFlow-style attribution | Step-level counterfactual causal attribution |
| B5 | CHIEF-style graph attribution | Causal graph + counterfactual failure attribution |
| B6 | Provenance-only | Structural provenance without counterfactual replay |
| B7 | Random intervention | Random channel selection baseline |
| B8 | CELA | The proposed method |

The exact feasibility of reproducing external baselines
(B3–B5) must be verified during Stage 16.

## 21. Metrics

Candidate evaluation metrics frozen for Stage 16–17:

### Attribution
- Top-1 localization accuracy
- Top-k recall
- Origin localization accuracy
- Bottleneck localization accuracy

### Causal Estimation
- CEE estimation error (vs. known ground truth)
- Confidence interval coverage
- Calibration
- False positive rate

### Failure Propagation
- Propagation localization accuracy
- Origin / bottleneck / actuator distinction

### Prevention
- Failure reduction rate
- Utility preservation rate
- Intervention cost
- Number of interventions required

### Efficiency
- Replay count per analysis
- Candidate reduction ratio
- Runtime (wall-clock)
- Cost per analyzed failure

## 22. Ablations

Ablation conditions frozen for Stage 16–17:

| ID | Ablation | What is Removed |
|----|----------|-----------------|
| A1 | No evidence lineage | Remove evidence identity; use step-only |
| A2 | Step intervention | Replace channel intervention with step intervention |
| A3 | No multimodal evidence identity | Collapse all evidence to untyped |
| A4 | No memory provenance | Remove memory-related evidence tracking |
| A5 | No temporal representation | Remove cycle/temporal indexing |
| A6 | No candidate screening | Evaluate all channels (no pruning) |
| A7 | No paired replay | Unpaired estimation instead of paired |
| A8 | Hard provenance only | No semantic provenance |
| A9 | Hard + semantic provenance | Full provenance |
| A10 | CEE ranking only | Rank by CEE without cascade intervention |

## 23. Benchmark Strategy

### Synthetic Ground Truth (Primary)

Construct controlled scenarios where:
- The failure-causing evidence channel is known by construction
- The propagation path is known by construction
- The correct intervention point is known by construction

This enables ground-truth evaluation of attribution accuracy.

### Scenario Categories
- Single-point failure (one corrupted evidence source)
- Cascading failure (multi-hop propagation)
- Cross-modal failure (text→tool→reasoning chain)
- Memory-mediated failure (evidence persists across cycles)
- Adversarial scenarios (prompt injection, poisoned retrieval,
  corrupted tool output)

### Controlled Variables
- Task complexity (number of steps, tool calls)
- Failure injection point (early, middle, late)
- Failure type (corrupted value, missing evidence, wrong tool)
- Evidence-flow graph structure (linear, branching, cyclic)

## 24. Experimental Protocol

1. **Setup**: Configure agent with known task, known correct
   answer, and known failure injection.
2. **Baseline execution**: Run TracedAgent → ExecutionRun.
3. **Failure verification**: Confirm failure oracle F(run)=1.
4. **Evidence extraction**: Build evidence-flow graph from
   provenance.
5. **Candidate screening**: Identify failure-relevant
   evidence channels.
6. **Controlled replay**: For each candidate channel, run
   paired counterfactual replay with channel intervention.
7. **Effect estimation**: Compute CEE for each channel.
8. **Attribution**: Rank channels by CEE; identify bottleneck.
9. **Evaluation**: Compare with ground truth and baselines.
10. **Ablation**: Repeat with ablation conditions.

**Not implemented in Stage 11.** This protocol is for
Stages 14–17.

## 25. Known Limitations and Explicit Non-Claims

### What CELA Does NOT Claim

- CELA does NOT invent counterfactual replay
  (established: Pearl, CAR, CausalFlow)
- CELA does NOT invent causal intervention
  (established: do-calculus, SCMs)
- CELA does NOT invent provenance graphs
  (established: W3C PROV, data provenance literature)
- CELA does NOT invent edge-level interventions
  (path-specific effects are established)
- CELA does NOT claim globally optimal intervention
  (greedy approximation only)
- CELA does NOT claim universal generalization
  (validated on Stage 1 reference agent only)

### Inherited / Established Methods

| Method | Source |
|--------|--------|
| Structural causal models (SCMs) | Pearl (2009) |
| do-interventions | Pearl (2009) |
| Counterfactual reasoning | Pearl, Halpern, etc. |
| Counterfactual replay | CAR, CausalFlow, etc. |
| Provenance | W3C PROV, data provenance |
| Causal graphs | Pearl, Spirtes, etc. |
| Step-level attribution | CAR, CausalFlow, CHIEF |
| Shapley attribution | Shapley (1953), SHAP |
| Confidence intervals | Standard statistics |
| Path-specific causal effects | Pearl, Avin, etc. |

### CELA Candidate Contribution

> CELA operationalizes provenance-defined multimodal
> evidence-flow channels as intervention targets within
> autonomous-agent executions and uses controlled
> counterfactual replay to estimate their contribution to
> downstream failure propagation and identify intervention
> points.

**Novelty is a research hypothesis to be validated against
the current literature and experimental baselines.**

The specific candidate contributions are:

1. **Evidence-centric intervention unit**: intervening on
   evidence-flow channels rather than execution steps
2. **Provenance-defined multimodal evidence-flow channel**:
   using hard provenance to define intervention targets
3. **Operationalization in agent replay**: connecting
   evidence-channel interventions to executable replay
4. **Failure-propagation analysis over channels**: analyzing
   failure propagation at evidence granularity
5. **Intervention-point selection from channel effects**:
   selecting prevention points based on measured CEE

### Distinguished from Prior Work

| System | What It Does | CELA Distinction |
|--------|-------------|-----------------|
| CAR | Step do-interventions, stochastic replay, Shapley | CELA targets evidence channels, not steps |
| CausalFlow | Step-level counterfactual attribution + repair | CELA uses provenance-defined channels |
| CHIEF | Causal graph + counterfactual failure attribution | CELA adds evidence lineage layer |
| Provenance-only | Structural lineage without counterfactual | CELA adds controlled replay + CEE |
| Step-level CF | Intervene per step | CELA intervenes per evidence channel |

These distinctions are **provisional**. They must be
empirically validated in Stages 16–17.
