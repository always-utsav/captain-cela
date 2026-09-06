# 07 BENCHMARK VALIDATION

## Family Validation Summary

All families validated via test_family_structure (5 parametrized tests, all PASS).

### BF-A: SINGLE_CHANNEL
- **Mechanism:** One tool (calculator) produces failure keyword "42"
- **Ground truth:** 1 causal channel (calculator result -> downstream)
- **Evaluator:** keyword "any" match on "42"
- **Candidates:** 2 (causal + distractor)
- **Expected:** Causal channel CEE > distractor CEE
- **Confound:** MockLLM hardcodes "42" in responses regardless of tool result
- **Smoke F1 (B1/B2/B4):** 0.000 — baselines select wrong channel

### BF-B: REDUNDANT_OR
- **Mechanism:** Two tools both produce failure keywords (OR logic)
- **Ground truth:** 2 causal channels, either sufficient alone
- **Evaluator:** keyword "any" match
- **Expected:** Individual CEE high for both; joint not needed
- **Confound:** Shared source event may prevent joint intervention
- **Smoke F1:** 0.667

### BF-C: COMPLEMENTARY_AND
- **Mechanism:** Two tools must BOTH produce keywords (AND logic)
- **Ground truth:** 2 causal channels, both required
- **Evaluator:** keyword "all" match
- **Expected:** Individual CEE moderate; joint CEE high
- **Smoke F1:** 0.667

### BF-D: DISTRACTOR
- **Mechanism:** Failure caused by one channel; distractor present
- **Ground truth:** 1 causal + multiple distractors
- **Evaluator:** keyword match
- **Expected:** Method should avoid selecting distractors
- **Negative control:** Distractor CEE = 0 (VERIFIED, 0/6 false positives)
- **Smoke F1:** 0.000

### BF-E: CASCADE
- **Mechanism:** Multi-hop A -> B -> C -> Failure
- **Ground truth:** Root cause channel identified
- **Evaluator:** keyword match on chain end
- **Expected:** Root attribution requires depth traversal
- **Smoke F1:** 1.000

### BF-F: COST_ASYMMETRIC
- **Mechanism:** Channels with different intervention costs
- **Ground truth:** Budget-feasible set specified
- **Evaluator:** keyword match
- **Expected:** Cost-aware selection outperforms cost-blind
- **Smoke F1:** 0.667

## Evaluator Independence

All evaluators built via `_build_keyword_evaluator()`:
- Input: keyword list + logic ("any"/"all")
- Checks: execution output text only
- Does NOT check: which interventions were applied
- Does NOT receive: ground truth labels

## Ground Truth Structure

All families provide:
- `causal_channel_ids`: list of causally relevant intervention IDs
- `irrelevant_channel_ids`: list of non-causal channels
- `required_prevention_sets`: minimal sets for prevention
- `single_intervention_outcomes`: expected outcome per channel

## Verdict: PASS WITH LIMITATION
- All families generate valid scenarios
- Ground truth correctly specified
- Evaluators independent
- **Limitation:** MockLLM does not react to interventions, so CEE measurement yields 0
