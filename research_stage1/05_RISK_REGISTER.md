# 05 RISK REGISTER

## CRITICAL

### R1: MockLLM CEE Ceiling
- **Risk:** CEE=0 for all interventions because MockLLMProvider replays pre-scripted responses containing failure keywords regardless of tool-result changes
- **Impact:** Cannot demonstrate actual causal effect through replay
- **Mitigation:** Benchmark metrics use ground-truth-based selection evaluation (F1, recall, precision), not actual CEE measurement. Document as limitation.
- **Status:** CONFIRMED in smoke campaign

### R2: Shared-Source Replay Rejection
- **Risk:** Joint intervention on channels from same source event causes replay validation rejection ("Target has 2 interventions")
- **Impact:** Cannot jointly intervene on co-sourced channels
- **Mitigation:** Document as limitation. Does not affect single-channel experiments.
- **Status:** CONFIRMED in intervention fidelity tests

## HIGH

### R3: Synthetic-Only Benchmark
- **Risk:** Results on synthetic scenarios may not generalize
- **Impact:** Cannot claim real-world applicability
- **Mitigation:** State explicitly as limitation. Propose external benchmark (Who&When) for Stage 2.
- **Status:** ACCEPTED LIMITATION

### R4: Single Agent Architecture
- **Risk:** Only tested on Stage 1 reference agent
- **Impact:** Cannot claim multi-agent generality
- **Mitigation:** Document. Do not claim.
- **Status:** ACCEPTED LIMITATION

### R5: Step-vs-Channel Measurement
- **Risk:** In the current reference agent, each tool produces exactly one result artifact, so step-level and channel-level interventions often target the same event
- **Impact:** Novelty experiment may show no difference
- **Mitigation:** Need scenarios where one step produces multiple channels (shared-source with branching)
- **Status:** NEEDS STAGE 2 ATTENTION

## MEDIUM

### R6: Evaluation Independence
- **Risk:** Keyword evaluator is simple; may not reflect realistic failure assessment
- **Impact:** Results may not transfer to richer evaluators
- **Mitigation:** Document. Keyword evaluator is deterministic and independent.

### R7: UUID Nondeterminism (RESOLVED)
- **Risk:** uuid.uuid4() caused different IDs across runs
- **Impact:** Metric values differed between runs
- **Mitigation:** Implemented deterministic_ids() context manager
- **Status:** RESOLVED — verified 3 identical runs

### R8: No Direct Competitor Reproduction
- **Risk:** Cannot numerically compare against CAR, CausalFlow, CHIEF
- **Impact:** Cannot claim quantitative superiority
- **Mitigation:** Compare conceptually. Propose future work.
- **Status:** ACCEPTED LIMITATION

## LOW

### R9: Wilcoxon Tie Correction
- **Risk:** Wilcoxon test does not apply tie correction
- **Impact:** Slightly conservative p-values
- **Mitigation:** Low priority; ties are rare in CEE values

### R10: Hardcoded Method Names in Ablation
- **Risk:** _compute_ablation searches for "A1_cela" etc.
- **Impact:** Fragile if method naming changes
- **Mitigation:** Low risk; names are stable
