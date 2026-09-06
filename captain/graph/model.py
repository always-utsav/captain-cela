"""Execution graph data model for CAPTAIN.

Defines the typed graph representation of an agent execution:

- :class:`NodeType` / :class:`EdgeType` -- graph element classification.
- :class:`GraphNode` -- a node representing an Event or Artifact.
- :class:`GraphEdge` -- a directed edge representing a provenance relationship.
- :class:`ExecutionGraph` -- the complete graph with traversal and export API.

The graph is structural, not causal.  Execution order is preserved via
sequence numbers on event nodes, but adjacency does NOT imply causation.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(enum.StrEnum):
    """Type of graph node."""

    EVENT = "event"
    ARTIFACT = "artifact"


class EdgeType(enum.StrEnum):
    """Type of directed graph edge.

    - ``PRODUCED``: Event -> Artifact (the event created the artifact).
    - ``CONSUMED``: Artifact -> Event (the event consumed the artifact).
    - ``DERIVED``: Artifact -> Artifact (lineage through an event).
    """

    PRODUCED = "produced"
    CONSUMED = "consumed"
    DERIVED = "derived"


class GraphNode(BaseModel):
    """A node in the execution graph.

    Holds a reference to its canonical source (event or artifact) by ID,
    plus lightweight metadata.  Does NOT embed the full Event/Artifact.

    Attributes:
        node_id: The canonical source ID (event_id or artifact_id).
        node_type: Whether this is an EVENT or ARTIFACT node.
        label: Human-readable label (e.g. event type or artifact type).
        sequence_number: For EVENT nodes, the execution order.
            ``None`` for ARTIFACT nodes.
        metadata: Additional key/value context.
    """

    node_id: str
    node_type: NodeType
    label: str = ""
    sequence_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A directed edge in the execution graph.

    Attributes:
        source_id: ID of the source node.
        target_id: ID of the target node.
        edge_type: The relationship type.
        metadata: Additional context.
    """

    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionGraph:
    """Typed execution graph built from a canonical ExecutionRun.

    Provides node/edge lookup, predecessor/successor queries,
    upstream/downstream traversal, and JSON-compatible export.

    This is a STRUCTURAL graph -- adjacency represents provenance
    relationships, not proven causal links.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        # Adjacency indexes
        self._successors: dict[str, list[str]] = {}
        self._predecessors: dict[str, list[str]] = {}

    # --- Node management ----------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph (idempotent by node_id)."""
        if node.node_id not in self._nodes:
            self._nodes[node.node_id] = node
            self._successors.setdefault(node.node_id, [])
            self._predecessors.setdefault(node.node_id, [])

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge to the graph.

        Both source and target must already be nodes.  Edges to/from
        unknown nodes are silently ignored (malformed-reference safety).
        """
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            return
        self._edges.append(edge)
        self._successors[edge.source_id].append(edge.target_id)
        self._predecessors[edge.target_id].append(edge.source_id)

    # --- Node lookup --------------------------------------------------------

    def get_node(self, node_id: str) -> GraphNode | None:
        """Return a node by ID, or ``None``."""
        return self._nodes.get(node_id)

    def get_event_node(self, event_id: str) -> GraphNode | None:
        """Return an EVENT node by event ID, or ``None``."""
        node = self._nodes.get(event_id)
        if node is not None and node.node_type == NodeType.EVENT:
            return node
        return None

    def get_artifact_node(self, artifact_id: str) -> GraphNode | None:
        """Return an ARTIFACT node by artifact ID, or ``None``."""
        node = self._nodes.get(artifact_id)
        if node is not None and node.node_type == NodeType.ARTIFACT:
            return node
        return None

    # --- Adjacency ----------------------------------------------------------

    def get_successors(self, node_id: str) -> list[str]:
        """Return sorted successor node IDs."""
        return sorted(self._successors.get(node_id, []))

    def get_predecessors(self, node_id: str) -> list[str]:
        """Return sorted predecessor node IDs."""
        return sorted(self._predecessors.get(node_id, []))

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        """Return all edges originating from *node_id*."""
        return [e for e in self._edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        """Return all edges targeting *node_id*."""
        return [e for e in self._edges if e.target_id == node_id]

    # --- Structural traversal -----------------------------------------------

    def get_artifact_events(self, artifact_id: str) -> list[str]:
        """Return event IDs connected to an artifact (producers + consumers)."""
        result: set[str] = set()
        for edge in self._edges:
            if edge.source_id == artifact_id and self._is_event(edge.target_id):
                result.add(edge.target_id)
            if edge.target_id == artifact_id and self._is_event(edge.source_id):
                result.add(edge.source_id)
        return sorted(result)

    def get_event_artifacts(self, event_id: str) -> list[str]:
        """Return artifact IDs connected to an event (produced + consumed)."""
        result: set[str] = set()
        for edge in self._edges:
            if edge.source_id == event_id and self._is_artifact(edge.target_id):
                result.add(edge.target_id)
            if edge.target_id == event_id and self._is_artifact(edge.source_id):
                result.add(edge.source_id)
        return sorted(result)

    def get_event_events(self, event_id: str) -> list[str]:
        """Return event IDs structurally connected to *event_id* through shared artifacts."""
        connected: set[str] = set()
        for art_id in self.get_event_artifacts(event_id):
            for evt_id in self.get_artifact_events(art_id):
                if evt_id != event_id:
                    connected.add(evt_id)
        return sorted(connected)

    # --- Multi-hop traversal ------------------------------------------------

    def traverse_downstream(self, node_id: str) -> list[str]:
        """BFS downstream from *node_id*. Cycle-safe. Deterministic order."""
        return self._bfs(node_id, direction="down")

    def traverse_upstream(self, node_id: str) -> list[str]:
        """BFS upstream from *node_id*. Cycle-safe. Deterministic order."""
        return self._bfs(node_id, direction="up")

    # --- Counts -------------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Total number of nodes."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Total number of edges."""
        return len(self._edges)

    @property
    def event_node_count(self) -> int:
        """Number of EVENT nodes."""
        return sum(1 for n in self._nodes.values() if n.node_type == NodeType.EVENT)

    @property
    def artifact_node_count(self) -> int:
        """Number of ARTIFACT nodes."""
        return sum(1 for n in self._nodes.values() if n.node_type == NodeType.ARTIFACT)

    # --- Export -------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Export the graph as a JSON-compatible dictionary.

        Format::

            {
                "nodes": [ {node_id, node_type, label, sequence_number, metadata}, ... ],
                "edges": [ {source_id, target_id, edge_type, metadata}, ... ],
                "node_count": int,
                "edge_count": int,
            }
        """
        return {
            "nodes": [n.model_dump() for n in self._sorted_nodes()],
            "edges": [e.model_dump() for e in self._edges],
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }

    # --- Internal -----------------------------------------------------------

    def _is_event(self, node_id: str) -> bool:
        n = self._nodes.get(node_id)
        return n is not None and n.node_type == NodeType.EVENT

    def _is_artifact(self, node_id: str) -> bool:
        n = self._nodes.get(node_id)
        return n is not None and n.node_type == NodeType.ARTIFACT

    def _sorted_nodes(self) -> list[GraphNode]:
        """Nodes sorted: events by sequence_number first, then artifacts by ID."""
        events = sorted(
            (n for n in self._nodes.values() if n.node_type == NodeType.EVENT),
            key=lambda n: (n.sequence_number or 0, n.node_id),
        )
        artifacts = sorted(
            (n for n in self._nodes.values() if n.node_type == NodeType.ARTIFACT),
            key=lambda n: n.node_id,
        )
        return events + artifacts

    def _bfs(self, start_id: str, *, direction: str) -> list[str]:
        """BFS traversal with visited-set cycle protection."""
        visited: set[str] = {start_id}
        result: list[str] = []
        queue: list[str] = []

        # Seed with direct neighbors
        neighbors = (
            self.get_successors(start_id)
            if direction == "down"
            else self.get_predecessors(start_id)
        )
        for nid in neighbors:
            if nid not in visited:
                visited.add(nid)
                queue.append(nid)
                result.append(nid)

        while queue:
            current = queue.pop(0)
            next_neighbors = (
                self.get_successors(current)
                if direction == "down"
                else self.get_predecessors(current)
            )
            for nid in next_neighbors:
                if nid not in visited:
                    visited.add(nid)
                    queue.append(nid)
                    result.append(nid)

        return result
