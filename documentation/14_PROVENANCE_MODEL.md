# Provenance Model

## Extraction and Querying
- The `ProvenanceExtractor` derives relationships (`PRODUCED`, `CONSUMED`, `DERIVED`) directly from `ExecutionRun` references (`input_artifact_ids`, `output_artifact_ids`).
- The `ProvenanceQuery` API provides multi-hop cycle-safe traversal methods (`trace_upstream`, `trace_downstream`, `is_ancestor`).
- **Primary Mechanism**: Hard deterministic provenance based on data linkages. Semantic provenance is an optional future extension.

See [extractor.py](file:///c:/Users/utsav/Desktop/CAPTAIN/captain/provenance/extractor.py).
