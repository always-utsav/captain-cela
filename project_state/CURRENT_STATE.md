# CAPTAIN -- Current State

**Implementation Stage**: 18 (COMPLETE -- FINAL)

**Research Stage 2**: COMPLETE -- FROZEN FOR PAPER WRITING

All 18 planned implementation stages are complete.
Research Stage 2 experimental campaign executed, audited, and frozen.

## Implementation Stages (Historical)

- Stages 0-10: Infrastructure (tracing, agent, tools, graph, replay)
- Stage 11: Research lock (CELA definition frozen)
- Stages 12-15: CELA core (evidence, failure, estimation, cascade)
- Stage 16: Benchmark & evaluation framework
- Stage 17: Statistical validation & experiment runner
- Stage 18: Final integration, demo, reproducibility

## Research Stage 2 (Scientific Campaign)

- 275 scenarios across 11 benchmark families, 5 seeds
- Primary experiment: channel vs source-event intervention granularity
- Real-LLM sanity check (Gemini 3.6-flash)
- Final scientific closure audit completed
- See `research_stage2/26_FINAL_SCIENTIFIC_FREEZE.md`

## Verification

- 682 tests passing
- ruff check: clean
- mypy captain: clean
- No API keys in repository

## Key Commits

```
50d13cc  Final scientific closure
d5b4a24  Stage 2 campaign
98e6366  Stage 1.1-B baseline
```

## Commands

```bash
# One-command demo
python -m captain.demo

# Launch Explorer (includes /research endpoint)
python -m captain.explorer

# Run tests
python -m pytest tests/ -q

# Regenerate campaign results (deterministic)
python research/run_campaign.py
```
