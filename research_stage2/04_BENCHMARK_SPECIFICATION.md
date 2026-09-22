# 04: Benchmark Specification

The CAPTAIN/CELA benchmark suite contains 11 families evaluating distinct causal reasoning mechanisms.

## BF-A: Simple Direct Causation
- **CausalMechanism Enum**: `SINGLE_CHANNEL`
- **Causal Structure**: One tool (calculator) produces failure; others (echo) are irrelevant.
- **Ground Truth**: Causal channel: calculator. Irrelevant channel: echo.
- **Origin/Propagation/Actuator**: Origin: calculator. Propagation: none. Actuator: calculator. Distractor: echo.
- **Prevention Set**: {calculator}
- **Evaluator Behavior**: Fails if the keyword is present.
- **Intended Scientific Question**: Can the system detect a basic single failing artifact among benign distractors?
- **Known Limitations**: Simple flat structure.

## BF-B: Redundant Causation (OR)
- **CausalMechanism Enum**: `REDUNDANT_OR`
- **Causal Structure**: Multiple tools independently produce failure-causing content.
- **Ground Truth**: Causal channels: all tools producing failure. Irrelevant channels: none.
- **Origin/Propagation/Actuator**: Origin: all causal tools. Propagation: none. Actuator: all causal tools.
- **Prevention Set**: Requires blocking ALL causal tools.
- **Evaluator Behavior**: Fails if ANY failure keyword is present.
- **Intended Scientific Question**: Can the system identify that multiple independent sources must be blocked?
- **Known Limitations**: No intermediate propagation.

## BF-C: Complementary Causation (AND)
- **CausalMechanism Enum**: `COMPLEMENTARY_AND`
- **Causal Structure**: Interaction between multiple tools causes failure.
- **Ground Truth**: Causal channels: all interacting tools.
- **Origin/Propagation/Actuator**: Origin: all causal tools. Propagation: none. Actuator: all causal tools.
- **Prevention Set**: Blocking ANY of the interacting tools prevents failure.
- **Evaluator Behavior**: Fails ONLY if ALL failure keywords are present.
- **Intended Scientific Question**: Can the system isolate joint necessary conditions?
- **Known Limitations**: Ignores temporal ordering.

## BF-D: Distractor / Masking
- **CausalMechanism Enum**: `DISTRACTOR`
- **Causal Structure**: One tool causes failure, many other tools provide noisy output.
- **Ground Truth**: Causal channel: the failing tool. Irrelevant channels: all noise tools.
- **Origin/Propagation/Actuator**: Origin: failing tool. Propagation: none. Actuator: failing tool. Distractors: noise tools.
- **Prevention Set**: {failing tool}
- **Evaluator Behavior**: Fails if keyword is present despite noise.
- **Intended Scientific Question**: Is the attribution robust to irrelevant but structurally plausible events?
- **Known Limitations**: Flat causal topology.

## BF-E: Multi-hop Cascade
- **CausalMechanism Enum**: `CASCADE`
- **Causal Structure**: Originating failure propagates linearly through intermediate reasoning steps.
- **Ground Truth**: Causal channels: origin and all intermediate steps.
- **Origin/Propagation/Actuator**: Origin: first step. Propagation: intermediate steps. Actuator: final step.
- **Prevention Set**: {origin}
- **Evaluator Behavior**: Fails if keyword reaches the final output.
- **Intended Scientific Question**: Can the system trace attribution back through a linear chain of events?
- **Known Limitations**: Strictly linear, no branching.

## BF-F: Cost-Asymmetric Spurious Correlation
- **CausalMechanism Enum**: `COST_ASYMMETRIC`
- **Causal Structure**: Two tools independently cause failure, but with different intervention costs.
- **Ground Truth**: Causal channels: both failing tools.
- **Origin/Propagation/Actuator**: Origin: both tools. Propagation: none. Actuator: both tools.
- **Prevention Set**: Blocking BOTH is required (uses `keyword_logic="all"` / AND logic).
- **Evaluator Behavior**: Fails if keywords are present. Budget feasibility tested.
- **Intended Scientific Question**: Does the system select cost-efficient interventions under a budget constraint?
- **Known Limitations**: Cost structure is artificially imposed.

## BF-G: Granular Provenance (Shared Source)
- **CausalMechanism Enum**: `SINGLE_CHANNEL` (not a dedicated enum)
- **Causal Structure**: A single tool produces multiple distinct outputs; only one channel causes failure.
- **Ground Truth**: Causal channel: the specific failing output channel. Irrelevant channels: the benign channels from the same source.
- **Origin/Propagation/Actuator**: Origin: tool event. Propagation: channel routing. Actuator: specific channel.
- **Prevention Set**: {failing channel}
- **Evaluator Behavior**: Fails if the specific channel content is present.
- **Intended Scientific Question**: Can the system differentiate between channels from the same source event?
- **Known Limitations**: Tool behavior must be perfectly separable.

## BF-H: Temporal Delay (Branching/Convergent)
- **CausalMechanism Enum**: `BRANCHING`
- **Causal Structure**: Actual topology is convergent with mixed inputs, testing delayed effects.
- **Ground Truth**: Causal channels: delayed failing input. Irrelevant channels: benign inputs.
- **Origin/Propagation/Actuator**: Origin: delayed failing input. Actuator: point of convergence.
- **Prevention Set**: {delayed failing input}
- **Evaluator Behavior**: Fails when delayed input converges and produces failure.
- **Intended Scientific Question**: Can causes be linked to temporally distant outcomes across convergent structures?
- **Known Limitations**: Convergence logic is simplified.

## BF-I: Multi-hop Conjunction
- **CausalMechanism Enum**: `CONVERGENT`
- **Causal Structure**: Convergent topology, but only the calculator is truly causal.
- **Ground Truth**: Causal channel: calculator. Irrelevant channels: other converging inputs.
- **Origin/Propagation/Actuator**: Origin: calculator. Propagation: convergence nodes. Actuator: final node.
- **Prevention Set**: {calculator}
- **Evaluator Behavior**: Fails based on calculator's specific contribution.
- **Intended Scientific Question**: Can the system handle multi-step graphs while ignoring non-causal converging inputs?
- **Known Limitations**: Only tests one specific causal path.

## BF-J: Circular / Root vs Symptom
- **CausalMechanism Enum**: `ROOT_VS_SYMPTOM`
- **Causal Structure**: Actually parallel independent sources rather than a true cycle or feedback loop.
- **Ground Truth**: Causal channels: parallel sources.
- **Origin/Propagation/Actuator**: Origin: independent sources.
- **Prevention Set**: Depends on parallel paths.
- **Evaluator Behavior**: Assesses independent source contributions.
- **Intended Scientific Question**: Can the system resolve reciprocal or parallel causal structures correctly?
- **Known Limitations**: Does not implement true cycles.

## BF-K: Downstream Repair / Epistemic Uncertainty
- **CausalMechanism Enum**: `DOWNSTREAM_REPAIR`
- **Causal Structure**: Actually downstream persistence with ineffective repair.
- **Ground Truth**: Causal channels: original failure. Irrelevant channels: ineffective repair attempt.
- **Origin/Propagation/Actuator**: Origin: original failure. Actuator: persistence node.
- **Prevention Set**: {original failure}
- **Evaluator Behavior**: Fails because the downstream repair fails to mitigate the issue.
- **Intended Scientific Question**: Can the system identify the root cause when downstream repair mechanisms are ineffective?
- **Known Limitations**: Repair mechanism is structurally present but functionally inert.
