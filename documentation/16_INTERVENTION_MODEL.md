# Intervention Model

## Types of Interventions
- `ARTIFACT_REPLACEMENT`: Directly replaces an artifact value.
- `TOOL_RESULT_OVERRIDE`: Mocks a tool's output to inject counterfactual data.
- `EVENT_DISABLE`: Prevents a non-essential event from executing.
- `EVENT_OUTPUT_OVERRIDE`: Replaces output at the event boundary.

## Channel vs. Source-Event Interventions
A channel-level intervention targets a specific edge $A \rightarrow B$. To implement this accurately (`channel_to_intervention`), CAPTAIN resolves the source evidence producing event and overwrites it. If the event produces multiple artifacts, it targets the specific artifact. This ensures that collateral channels (e.g., $C \rightarrow B$ through the same mediating event) are preserved intact, making channel-level interventions strictly more selective than node-level blocking.

See [model.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/intervention/model.py).
