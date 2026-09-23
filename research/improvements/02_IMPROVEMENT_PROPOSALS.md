# Improvement Proposals — CAPTAIN/CELA V2

## Status: Under Investigation

This document tracks proposed improvements, their feasibility,
and implementation decisions.

---

## Proposal 1: Implement Missing Experiments

**Weakness**: V1 declared pathway_stress, cascade, and cost_utility
experiments as NOT IMPLEMENTED.

**Proposal**: Implement all three in `campaign.py`.

**Status**: IMPLEMENTING

**Impact**: Fills 3 gaps in experimental coverage.

---

## Proposal 2: Step-Level Baseline

**Weakness**: V1 compares channel-level vs source-event-level
intervention. A true step-level baseline (block entire execution
step: all tools, all artifacts) would strengthen the comparison.

**Feasibility**: INVESTIGATE

The current intervention model supports:
- `ARTIFACT_REPLACEMENT`: modifies one artifact (channel-level)
- `TOOL_RESULT_OVERRIDE`: modifies tool result (source-event-level)
- `EVENT_DISABLE`: disables an event entirely (closest to step-level)

EVENT_DISABLE could serve as a step-level baseline if the evaluator
treats the disabled event's effects as "no output produced."

**Decision**: Requires further investigation of how EVENT_DISABLE
propagates through the replay engine.

---

## Proposal 3: Better CEE Confidence Intervals

**Weakness**: With deterministic MockLLM, bootstrap CI has width 0.

**Proposal**: When replay is deterministic, report CI as
"trivially zero-width (deterministic)" rather than computing bootstrap.

**Feasibility**: EASY — conditional check in CEEEstimator.

**Decision**: DOCUMENT AS LIMITATION rather than implementing a
stochastic layer that would add complexity without scientific value.

---

## Proposal 4: Shapley-Style Attribution

**Weakness**: Current attribution does not account for interaction
effects between channels.

**Feasibility**: COMPLEX — requires exponential number of replay
combinations (2^n for n channels).

**Decision**: REJECT for V2 — would require fundamentally different
estimation approach. Document as future work.

---

## Proposal 5: Real LLM Pilot Expansion

**Weakness**: V1 sanity check uses 1 model, 1 scenario, 5 trials.

**Proposal**: Expand to 3 scenarios, 10 trials, keep gemini-3.6-flash.

**Feasibility**: MODERATE — requires Gemini API calls.

**Status**: PROPOSED — depends on API cost budget.

---

## Proposal 6: Weakness Audit Tests

**Weakness**: V1 has no dedicated stress tests.

**Proposal**: Add `test_weakness_audit.py` with 10+ edge-case tests.

**Status**: IMPLEMENTING

---

## Rejected Proposals

### R1: Stochastic Replay Engine
**Reason**: Would require a real LLM during replay, fundamentally
changing the evaluation paradigm. The deterministic benchmark
provides controlled conditions; stochastic evaluation is a
separate research direction.

### R2: Multi-Agent Cascade
**Reason**: CAPTAIN currently traces single-agent executions.
Multi-agent cascade modeling would require architectural changes
beyond the scope of V2.

### R3: External Benchmark Porting
**Reason**: No competitor benchmark provides compatible interfaces
for fair comparison. Porting would risk unfair advantage to CELA.
