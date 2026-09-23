# Introduction

## What is CAPTAIN/CELA?
**CAPTAIN** (Counterfactual Analysis Platform for Trace-based Investigation of Autonomous Agent Cascades) is an engineering platform that provides the infrastructure for tracking, graphing, and analyzing multimodal autonomous agent executions. 

**CELA** (Counterfactual Evidence-Lineage Attribution) is the research method built on top of CAPTAIN. It operationalizes causal intervention on provenance-defined evidence-flow channels to evaluate how failures propagate through agent reasoning and actions.

## Why does it exist?
As autonomous agents become more complex—utilizing reasoning cycles, working memory, and tool use—understanding why they fail becomes challenging. Standard debugging often points to the step where a failure manifested, but not necessarily the causal pathway of corrupted information that led to that failure. CAPTAIN and CELA exist to provide a controlled environment to study these failure cascades through causal counterfactual replay.

## What problem does it solve?
Existing failure-diagnosis methods typically attribute failures to specific execution steps or actions. This conflates the execution event (what happened) with the actual information transformation (what evidence moved or changed). When a single tool or step produces multiple pieces of evidence, step-level attribution cannot distinguish which specific piece of evidence caused downstream failure. CELA aims to solve this by enabling interventions directly on the information-bearing evidence channels.

## Who is it for?
CAPTAIN/CELA is a research-oriented platform for researchers and engineers studying AI agent reliability, interpretability, and failure analysis. It provides a standardized data model, tracing mechanisms, and a suite of benchmark topologies (BF-A through BF-K) to rigorously test attribution methods.
