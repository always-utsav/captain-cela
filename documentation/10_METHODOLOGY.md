# CELA Methodology

The Counterfactual Evidence-Flow Analysis (CELA) method follows a rigorous pipeline:

1. **Observe**: Record execution trace (events, artifacts) using the CAPTAIN tracing infrastructure.
2. **Represent**: Construct the Execution Graph and elevate it to an `EvidenceFlowGraph` mapping provenance.
3. **Analyze**: Identify failure-manifesting events and extract upstream evidence channels (`Candidate` extraction).
4. **Intervene**: Define precise, selective channel-level interventions (`ChannelIntervention` -> event overriding).
5. **Replay**: Perform counterfactual replay by blocking the specific information channel.
6. **Estimate**: Compute CEE (Counterfactual Evidence-Flow Effect) by comparing factual vs. counterfactual outcomes.
7. **Compare**: Compare CEE values to identify the causal bottleneck, and optionally select intervention sets for cascade prevention.
