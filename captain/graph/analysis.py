"""Graph analysis for CAPTAIN.

The :class:`GraphAnalyzer` provides structural analysis over an
:class:`ExecutionGraph` without performing causal inference.

All results are deterministically ordered.  Structural paths through
artifacts do NOT imply causation -- they represent provenance connectivity.
"""

from __future__ import annotations

from captain.graph.model import ExecutionGraph, NodeType


class GraphAnalyzer:
    """Structural analysis of an :class:`ExecutionGraph`.

    Provides degree metrics, root/leaf detection, reachability, and
    structural path finding.  All results are deterministic.

    Args:
        graph: The execution graph to analyze.
    """

    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph

    # --- Degree metrics -----------------------------------------------------

    def in_degree(self, node_id: str) -> int:
        """Number of incoming edges to *node_id*."""
        return len(self._graph.get_predecessors(node_id))

    def out_degree(self, node_id: str) -> int:
        """Number of outgoing edges from *node_id*."""
        return len(self._graph.get_successors(node_id))

    def degree(self, node_id: str) -> int:
        """Total degree (in + out) of *node_id*."""
        return self.in_degree(node_id) + self.out_degree(node_id)

    # --- Roots, leaves, isolated --------------------------------------------

    def roots(self) -> list[str]:
        """Return node IDs with in-degree 0 (no predecessors), sorted."""
        return sorted(
            nid for nid in self._graph._nodes if len(self._graph.get_predecessors(nid)) == 0
        )

    def leaves(self) -> list[str]:
        """Return node IDs with out-degree 0 (no successors), sorted."""
        return sorted(
            nid for nid in self._graph._nodes if len(self._graph.get_successors(nid)) == 0
        )

    def isolated_nodes(self) -> list[str]:
        """Return node IDs with degree 0 (no edges at all), sorted."""
        return sorted(nid for nid in self._graph._nodes if self.degree(nid) == 0)

    # --- Reachability -------------------------------------------------------

    def reachable_downstream(self, node_id: str) -> list[str]:
        """All nodes reachable downstream (BFS). Deterministic, cycle-safe."""
        return self._graph.traverse_downstream(node_id)

    def reachable_upstream(self, node_id: str) -> list[str]:
        """All nodes reachable upstream (BFS). Deterministic, cycle-safe."""
        return self._graph.traverse_upstream(node_id)

    # --- Event ordering -----------------------------------------------------

    def event_execution_order(self) -> list[str]:
        """Return event node IDs sorted by sequence_number.

        This is the explicit execution ordering, NOT a structural
        graph traversal.
        """
        events = [
            (n.node_id, n.sequence_number or 0)
            for n in self._graph._nodes.values()
            if n.node_type == NodeType.EVENT
        ]
        events.sort(key=lambda x: (x[1], x[0]))
        return [eid for eid, _ in events]

    # --- Structural paths ---------------------------------------------------

    def structural_event_path(self, source_id: str, target_id: str) -> list[str] | None:
        """Find a structural path between two event nodes through artifacts.

        Returns the path as a list of node IDs (alternating events and
        artifacts), or ``None`` if no path exists.

        **Important**: this is structural connectivity through provenance
        edges, NOT a proven causal chain.

        Protected against cycles via visited-set tracking.
        """
        if source_id == target_id:
            return [source_id]

        # BFS for shortest structural path
        visited: set[str] = {source_id}
        # Queue entries: (current_node, path_so_far)
        queue: list[tuple[str, list[str]]] = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            for neighbor in self._graph.get_successors(current):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                new_path = [*path, neighbor]
                if neighbor == target_id:
                    return new_path
                queue.append((neighbor, new_path))

        return None

    def all_event_paths(self) -> list[list[str]]:
        """Return structural paths connecting event roots to event leaves.

        Each path is a list of event node IDs connected through artifacts.
        Only returns paths of length >= 2 (at least two events).

        Deterministic ordering: paths sorted lexicographically.
        """
        event_roots = [
            nid for nid in self.roots() if self._graph._nodes[nid].node_type == NodeType.EVENT
        ]
        event_leaves = [
            nid for nid in self.leaves() if self._graph._nodes[nid].node_type == NodeType.EVENT
        ]

        paths: list[list[str]] = []
        for root in event_roots:
            for leaf in event_leaves:
                if root == leaf:
                    continue
                path = self.structural_event_path(root, leaf)
                if path is not None:
                    # Filter to event-only path
                    event_path = [
                        nid
                        for nid in path
                        if self._graph._nodes.get(nid, None) is not None
                        and self._graph._nodes[nid].node_type == NodeType.EVENT
                    ]
                    if len(event_path) >= 2:
                        paths.append(event_path)

        # Deduplicate and sort for determinism
        seen: set[tuple[str, ...]] = set()
        unique: list[list[str]] = []
        for p in paths:
            key = tuple(p)
            if key not in seen:
                seen.add(key)
                unique.append(p)
        unique.sort()
        return unique

    # --- Summary ------------------------------------------------------------

    def summary(self) -> dict[str, int]:
        """Return a summary of graph metrics."""
        return {
            "node_count": self._graph.node_count,
            "edge_count": self._graph.edge_count,
            "event_nodes": self._graph.event_node_count,
            "artifact_nodes": self._graph.artifact_node_count,
            "roots": len(self.roots()),
            "leaves": len(self.leaves()),
            "isolated_nodes": len(self.isolated_nodes()),
        }
