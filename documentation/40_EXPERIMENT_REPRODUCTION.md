# Experiment Reproduction

This document provides a step-by-step guide to reproducing every V1 experiment for the CELA paper.

## 1. Setup
Ensure Python 3.11.9 is installed on Windows.
```bash
pip install -e .
```

## 2. Run the Main Campaign (Deterministic)
Execute the benchmark suites across 5 seeds (42, 123, 456, 789, 1024).
```bash
python research/run_campaign.py
```
**Expected Output:**
- `research/raw/benchmark_seed_*.json`
- `research/raw/campaign_full.json`
- `research/raw/granularity_experiment.json`
- `research/raw/negative_controls.json`
- `research/raw/replay_convergence.json`
- `research/raw/scalability.json`

## 3. Real-LLM Validation
This is a sanity check to verify CEE > 0 on a real LLM.
```bash
# Ensure GEMINI_API_KEY is in .env
python research/run_real_llm.py
```
**Expected Output:** `research/raw/real_llm_validation.json`

## 4. Generate Figures
```bash
python captain/experiments/figures.py
```
**Expected Output:** `.svg` and `.png` files in `research/figures/`.

## 5. Validate Claims
Run the claim validator to compute statistical tests and verify support status.
```bash
python captain/experiments/claims.py
```
**Expected Output:** Console output verifying C1-C7 based on `research/raw/claim_registry.json`.
