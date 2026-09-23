# Motivation

Understanding agent failures requires precise causal attribution. The motivation for shifting focus from execution steps to evidence-flow channels is driven by several key challenges in agent analysis.

## Why Evidence-Channel Granularity Matters
In complex agent executions, a single reasoning step or tool call may ingest multiple inputs and produce multiple outputs. If we only intervene at the step level, we lose visibility into which specific piece of information caused the failure. Evidence-channel granularity allows us to pinpoint the exact information pathway responsible for downstream errors.

## The Shared-Source Problem
Often, a single source event (e.g., a tool call fetching a user profile) returns multiple distinct pieces of evidence (e.g., age, location, preferences). If only one piece of evidence is corrupted and causes a failure, intervening on the entire source event is imprecise. 

## Collateral Modification
When we intervene at the source-event level (e.g., disabling a tool call or overriding all its outputs), we modify not only the failure-causing evidence but also all benign evidence produced by that event. This collateral modification distorts counterfactual replays and obscures the true causal mechanism. Channel-level interventions target only the specific edge carrying the corrupted data, preserving the rest of the execution context.

## Provenance vs. Causality
Lineage and provenance tell us where information came from (structural connectivity), but they do not guarantee causality. An agent might read a corrupted piece of evidence but never actually use it to make a decision. Causal counterfactual replay is required to move beyond structural provenance to determine if an evidence channel actually *caused* the observed failure.
