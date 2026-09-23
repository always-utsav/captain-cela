# Developer Guide

Welcome to the CAPTAIN/CELA project. This guide explains how to extend and maintain the codebase.

## Code Organization

- `captain/`: Main package containing the core CELA implementation.
  - `experiments/`: Scripts for running the research campaign, generating claims, and plotting figures.
- `research/`: Contains raw experimental data, generated figures, and main execution scripts (`run_campaign.py`, `run_real_llm.py`).
- `tests/`: Unit and integration tests.

## Adding New Benchmarks

1. Define a new `BenchmarkScenario` in the corresponding module.
2. Ensure it implements the standard scenario interface.
3. Add the new scenario to the appropriate benchmark family in `run_campaign.py`.

## Adding New Methods

1. Subclass the base estimator/analyzer class.
2. Implement the `estimate()` or `analyze()` methods.
3. Integrate the method into the `ExperimentRunner`.
4. Define the method as a baseline (e.g., `A6`) for evaluation.

## Running Tests

All new code should be accompanied by tests.
```bash
python -m pytest tests/ -q
python -m ruff check captain/ tests/
python -m mypy captain
```
