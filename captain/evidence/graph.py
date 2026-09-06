"""CELA evidence-flow graph.

Provides the evidence-flow analysis view on top of the existing
CAPTAIN :class:`~captain.graph.model.ExecutionGraph`.  This is
an **additional** view — it does NOT replace ``captain.graph``.

The existing execution graph answers:
    "What execution entities are structurally connected?"

The evidence graph answers:
    "What information/evidence moved or transformed between them?"

**An evidence-flow edge is NOT a causal claim.**

Usage::

    from captain.evidence.graph import EvidenceFlowGraph

    builder = EvidenceLineageBuilder(run)
    evidence, transformations = builder.build()
    graph = EvidenceFlowGraph.from_lineage(evidence, transformations)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from captain.evidence.model import Evidence, EvidenceTransformation


class EvidenceFlowGraph(BaseModel):
    """Lightweight evidence-flow graph for CELA analysis.

    Stores evidence nodes and transformation edges with
    lookup, traversal, and serialization support.

    Does NOT replace ``captain.graph.ExecutionGraph``.
    Cycle-safe traversal is provided.
    """

    evidence: list[Evidence] = Field(default_factory=list)
    transformations: list[EvidenceTransformation] = Field(default_factory=list)

    @staticmethod
    def from_lineage(
        evidence: list[Evidence],
        transformations: list[EvidenceTransformation],
    ) -> EvidenceFlowGraph:
        """Construct from lineage builder output."""
        return EvidenceFlowGraph(
            evidence=list(evidence),
            transformations=list(transformations),
        )

    # --- Counts ---

    @property
    def evidence_count(self) -> int:
        """Number of evidence nodes."""
        return len(self.evidence)

    @property
    def transformation_count(self) -> int:
        """Number of transformation edges."""
        return len(self.transformations)

    # --- Lookup ---

    def get_evidence(self, evi_id: str) -> Evidence | None:
        """Look up evidence by ID."""
        for e in self.evidence:
            if e.evidence_id == evi_id:
                return e
        return None

    def get_by_artifact(self, art_id: str) -> Evidence | None:
        """Look up evidence by artifact ID."""
        for e in self.evidence:
            if e.artifact_id == art_id:
                return e
        return None

    # --- Adjacency ---

    def outgoing(self, evi_id: str) -> list[EvidenceTransformation]:
        """Get outgoing transformations from evidence."""
        return [t for t in self.transformations if t.source_evidence_id == evi_id]

    def incoming(self, evi_id: str) -> list[EvidenceTransformation]:
        """Get incoming transformations to evidence."""
        return [t for t in self.transformations if t.target_evidence_id == evi_id]

    # --- Traversal (cycle-safe) ---

    def upstream(self, evi_id: str) -> list[str]:
        """All evidence IDs upstream of the given ID.

        Cycle-safe BFS. Does NOT include the starting ID.
        """
        visited: set[str] = {evi_id}
        queue = [evi_id]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            for tx in self.incoming(current):
                src = tx.source_evidence_id
                if src not in visited:
                    visited.add(src)
                    result.append(src)
                    queue.append(src)

        return result

    def downstream(self, evi_id: str) -> list[str]:
        """All evidence IDs downstream of the given ID.

        Cycle-safe BFS. Does NOT include the starting ID.
        """
        visited: set[str] = {evi_id}
        queue = [evi_id]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            for tx in self.outgoing(current):
                tgt = tx.target_evidence_id
                if tgt not in visited:
                    visited.add(tgt)
                    result.append(tgt)
                    queue.append(tgt)

        return result

    # --- Serialization ---

    def to_dict(self) -> dict[str, Any]:
        """Export to JSON-compatible dict."""
        return {
            "evidence": [e.model_dump(mode="json") for e in self.evidence],
            "transformations": [t.model_dump(mode="json") for t in self.transformations],
            "evidence_count": self.evidence_count,
            "transformation_count": self.transformation_count,
        }
