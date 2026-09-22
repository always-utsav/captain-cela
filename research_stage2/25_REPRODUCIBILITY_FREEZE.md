# Reproducibility Freeze

## Software Environment
- Python: 3.11.9
- OS: Windows-10-10.0.26200-SP0
- Repository: https://github.com/always-utsav/captain-cela.git
- Stage 2 Commit: d5b4a2462f5ad95e9f132006a8fd870dc098ebe3

## Regenerate All Deterministic Results

```bash
# Install dependencies
pip install pydantic flask ruff mypy pytest matplotlib

# Run full campaign (deterministic, ~60s)
python research/run_campaign.py

# Generate figures from frozen data
python captain/experiments/figures.py

# Regenerate claim registry
python captain/experiments/claims.py
```

## Non-Deterministic Results (Require API Access)

```bash
# Requires GEMINI_API_KEY in .env
# Model: gemini-3.6-flash (may become unavailable)
# Results may differ due to model updates
python research/run_real_llm.py
```

## Result Files

All deterministic results are committed to `research/raw/`.
Real-LLM results are committed as a snapshot but may differ on re-execution.

## Verification

```bash
python -m pytest tests/ -q
python -m ruff check captain/ tests/
python -m mypy captain
```
