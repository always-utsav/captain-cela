# Data Model

The data model ensures immutability of observations and provides structured representations for research layers.

## Core Models
- `ExecutionRun`: Root trace object containing lists of `Event` and `Artifact`.
- `Event`: Represents an execution step (e.g. `TOOL_CALL`, `REASONING`).
- `Artifact`: Wraps textual/multimodal data or references.
- `ProvenanceRecord`: Immutable tuple asserting an artifact's origin.

## CELA Extensions
- `Evidence`: Classifies `Artifact` by its semantic role (e.g., `OBSERVATION`, `INTERPRETATION`).
- `Candidate`: A candidate evidence-flow channel for failure analysis.
- `ChannelIntervention`: Defines an intervention on an evidence-flow edge.
- `PairedTrial`: Tracks factual vs. counterfactual outcome for a specific intervention.
- `CascadeResult` & `SelectionResult`: Represents set-level effects and greedy selection paths.

See [execution.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/models/execution.py) and [model.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/evidence/model.py).
