# Evidence-Flow Model

The `EvidenceFlowGraph` maps structural dependencies into information flow.

- **Nodes**: `Evidence` objects representing units of information.
- **Edges**: `EvidenceTransformation` objects describing how evidence transferred through mediating execution events.
- **Semantics**: Edges trace hard provenance and categorize flow (e.g., `TOOL_DISPATCH`, `OBSERVATION`). Edges denote data dependence, NOT causal certainty (which requires CEE estimation).

See [graph.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/evidence/graph.py).
