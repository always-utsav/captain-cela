"""Execution graph builder for CAPTAIN.

The :class:`ExecutionGraphBuilder` converts a canonical
:class:`~captain.models.execution.ExecutionRun` into an
:class:`~captain.graph.model.ExecutionGraph` via the Stage 5
provenance layer.

Pipeline::

    ExecutionRun
        |
    ProvenanceExtractor
        |
    ExecutionGraphBuilder
        |
    ExecutionGraph
"""

from __future__ import annotations

from captain.graph.model import EdgeType, ExecutionGraph, GraphEdge, GraphNode, NodeType
from captain.models.execution import ExecutionRun
from captain.provenance.extractor import ProvenanceExtractor
from captain.provenance.model import ProvenanceRecord, RelationshipType


class ExecutionGraphBuilder:
    """Builds an :class:`ExecutionGraph` from an :class:`ExecutionRun`.

    Uses the Stage 5 :class:`ProvenanceExtractor` to derive relationships,
    then maps them to graph nodes and directed edges.

    **Edge direction conventions**:

    - ``PRODUCED``: Event node -> Artifact node
    - ``CONSUMED``: Artifact node -> Event node
    - ``DERIVED``: Artifact node -> Artifact node

    **Malformed-reference behavior**: edges referencing unknown node IDs
    are silently dropped by the graph (no fabricated nodes).

    Usage::

        graph = ExecutionGraphBuilder.build(run)
    """

    @staticmethod
    def build(
        run: ExecutionRun,
        records: list[ProvenanceRecord] | None = None,
    ) -> ExecutionGraph:
        """Build an execution graph from a run.

        Args:
            run: The canonical execution run.
            records: Optional pre-extracted provenance records.
                If ``None``, :class:`ProvenanceExtractor` is used.

        Returns:
            A fully constructed :class:`ExecutionGraph`.
        """
        graph = ExecutionGraph()

        # --- Add event nodes ---
        for event in run.events:
            graph.add_node(
                GraphNode(
                    node_id=event.event_id,
                    node_type=NodeType.EVENT,
                    label=event.event_type.value,
                    sequence_number=event.sequence_number,
                    metadata={
                        "component": event.component,
                        "run_id": event.run_id,
                    },
                )
            )

        # --- Add artifact nodes ---
        for artifact in run.artifacts:
            graph.add_node(
                GraphNode(
                    node_id=artifact.artifact_id,
                    node_type=NodeType.ARTIFACT,
                    label=artifact.artifact_type.value,
                    metadata={
                        "has_value": artifact.value is not None,
                        "has_reference": artifact.reference is not None,
                    },
                )
            )

        # --- Add edges from provenance ---
        prov_records = records if records is not None else ProvenanceExtractor(run).extract()

        for rec in prov_records:
            edge = _record_to_edge(rec)
            if edge is not None:
                graph.add_edge(edge)

        return graph


def _record_to_edge(rec: ProvenanceRecord) -> GraphEdge | None:
    """Convert a provenance record to a graph edge."""
    if rec.relationship == RelationshipType.PRODUCED:
        # Event -> Artifact
        return GraphEdge(
            source_id=rec.event_id,
            target_id=rec.artifact_id,
            edge_type=EdgeType.PRODUCED,
        )
    if rec.relationship == RelationshipType.CONSUMED:
        # Artifact -> Event
        return GraphEdge(
            source_id=rec.artifact_id,
            target_id=rec.event_id,
            edge_type=EdgeType.CONSUMED,
        )
    if rec.relationship == RelationshipType.DERIVED and rec.source_artifact_id is not None:
        # Artifact -> Artifact
        return GraphEdge(
            source_id=rec.source_artifact_id,
            target_id=rec.artifact_id,
            edge_type=EdgeType.DERIVED,
        )
    return None
