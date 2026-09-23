# How To Use CAPTAIN/CELA

This guide covers the basic usage of the CAPTAIN framework.

## Installation

```bash
git clone <repository_url>
cd CAPTAIN
pip install -e .
```

## Running the Demo

A simple interactive demo can be run to visualize the evidence flow graph:
*(Specify script if applicable, e.g., `python examples/demo.py`)*

## Using the Explorer

To inspect the generated results and the structure of benchmark scenarios, you can write custom scripts referencing the `BenchmarkScenario` and `EvidenceFlowGraph` classes.

## Running Tests

```bash
python -m pytest tests/ -q
```

## Running Benchmarks and Experiments

To execute the core benchmark suites:

```bash
python research/run_campaign.py
```

This will run scenarios across 11 benchmark families and output raw JSON data to `research/raw/`.

## Generating Figures

After running the experiments, generate the final charts:

```bash
python captain/experiments/figures.py
```
Outputs are saved in `research/figures/`.
