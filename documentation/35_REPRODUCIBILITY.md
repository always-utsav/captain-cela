# Reproducibility

This document provides the exact commands and requirements to reproduce all results in the CAPTAIN/CELA project.

## Environment Requirements
- **OS:** Windows
- **Python:** 3.11.9
- **Environment Management:** standard `venv` or `conda`
- **Dependencies:** Installed via `pip install -e .` from the project root.

## Reproducing Deterministic Results

All core benchmark experiments use a deterministic `MockLLM` with fixed seeds to ensure 100% reproducibility without requiring API keys.

```bash
# Run the full experimental campaign across multiple seeds
python research/run_campaign.py

# Generate all figures from the raw data
python captain/experiments/figures.py

# Validate all scientific claims against the generated data
python captain/experiments/claims.py
```

## Reproducing Real-LLM Validation

The real-LLM validation is a sanity check that requires a valid Gemini API key. It uses a fixed model (`gemini-3.6-flash`) with a temperature of `0.0`.

```bash
# Requires GEMINI_API_KEY to be set in the .env file
python research/run_real_llm.py
```

## Running Verification Tools

To verify code integrity, run the test suite and linters:

```bash
# Run tests
python -m pytest tests/ -q

# Run linter
python -m ruff check captain/ tests/

# Run type checker
python -m mypy captain
```

## Notes on Reproducibility
- The core CEE convergence is deterministic and trivially stable.
- "No t-tests are performed (stdlib-only implementation)". Statistical tests use permutation tests or Wilcoxon signed-rank tests implemented natively.
