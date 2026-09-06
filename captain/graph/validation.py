"""Graph validation for CAPTAIN.

The :class:`GraphValidator` checks an :class:`ExecutionGraph` for structural
integrity issues and returns a structured :class:`ValidationResult`.

Validation categories:

- **errors**: Issues that indicate a broken graph (e.g. edges referencing
  missing nodes, invalid edge/node type combinations).
- **warnings**: Issues that may indicate problems but do not break the graph
  (e.g. isolated nodes, missing sequence numbers on event nodes).

A graph with zero errors is considered **valid**.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field

from captain.graph.model import EdgeType, ExecutionGraph, NodeType


class Severity(enum.StrEnum):
    """Severity of a validation finding."""

    ERROR = "error"
    WARNING = "warning"


class ValidationFinding(BaseModel):
    """A single validation finding.

    Attributes:
        severity: ERROR or WARNING.
        code: Machine-readable finding code (e.g. ``"EDGE_MISSING_NODE"``).
        message: Human-readable description.
        node_id: Related node ID, if applicable.
        edge_index: Related edge index, if applicable.
        metadata: Additional context.
    """

    severity: Severity
    code: str
    message: str
    node_id: str | None = None
    edge_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Structured result of graph validation.

    Attributes:
        is_valid: True if zero errors were found.
        errors: Findings with ERROR severity.
        warnings: Findings with WARNING severity.
    """

    is_valid: bool = True
    errors: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[ValidationFinding] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)

    @property
    def finding_count(self) -> int:
        """Total findings (errors + warnings)."""
        return self.error_count + self.warning_count


# Valid edge type/node type combinations (source_type, edge_type, target_type)
_VALID_EDGE_COMBINATIONS: set[tuple[NodeType, EdgeType, NodeType]] = {
    (NodeType.EVENT, EdgeType.PRODUCED, NodeType.ARTIFACT),
    (NodeType.ARTIFACT, EdgeType.CONSUMED, NodeType.EVENT),
    (NodeType.ARTIFACT, EdgeType.DERIVED, NodeType.ARTIFACT),
}


class GraphValidator:
    """Validates an :class:`ExecutionGraph` for structural integrity.

    Usage::

        result = GraphValidator.validate(graph)
        if result.is_valid:
            ...
    """

    @staticmethod
    def validate(graph: ExecutionGraph) -> ValidationResult:
        """Run all validation checks and return a structured result."""
        findings: list[ValidationFinding] = []

        GraphValidator._check_adjacency_consistency(graph, findings)
        GraphValidator._check_edge_node_references(graph, findings)
        GraphValidator._check_edge_type_combinations(graph, findings)
        GraphValidator._check_self_loops(graph, findings)
        GraphValidator._check_event_sequence_numbers(graph, findings)
        GraphValidator._check_isolated_nodes(graph, findings)

        errors = [f for f in findings if f.severity == Severity.ERROR]
        warnings = [f for f in findings if f.severity == Severity.WARNING]

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _check_adjacency_consistency(
        graph: ExecutionGraph, findings: list[ValidationFinding]
    ) -> None:
        """Verify successor/predecessor indexes match the edge list."""
        # Build expected adjacency from edges
        expected_succ: dict[str, list[str]] = {}
        expected_pred: dict[str, list[str]] = {}
        for node_id in graph._nodes:
            expected_succ[node_id] = []
            expected_pred[node_id] = []
        for edge in graph._edges:
            expected_succ[edge.source_id].append(edge.target_id)
            expected_pred[edge.target_id].append(edge.source_id)

        for node_id in graph._nodes:
            actual_succ = graph._successors.get(node_id, [])
            if sorted(actual_succ) != sorted(expected_succ.get(node_id, [])):
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="ADJACENCY_MISMATCH_SUCCESSORS",
                        message=f"Successor index mismatch for node '{node_id}'",
                        node_id=node_id,
                    )
                )
            actual_pred = graph._predecessors.get(node_id, [])
            if sorted(actual_pred) != sorted(expected_pred.get(node_id, [])):
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="ADJACENCY_MISMATCH_PREDECESSORS",
                        message=f"Predecessor index mismatch for node '{node_id}'",
                        node_id=node_id,
                    )
                )

    @staticmethod
    def _check_edge_node_references(
        graph: ExecutionGraph, findings: list[ValidationFinding]
    ) -> None:
        """Check that all edges reference existing nodes."""
        for i, edge in enumerate(graph._edges):
            if edge.source_id not in graph._nodes:
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="EDGE_MISSING_SOURCE",
                        message=f"Edge {i} references missing source '{edge.source_id}'",
                        edge_index=i,
                    )
                )
            if edge.target_id not in graph._nodes:
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="EDGE_MISSING_TARGET",
                        message=f"Edge {i} references missing target '{edge.target_id}'",
                        edge_index=i,
                    )
                )

    @staticmethod
    def _check_edge_type_combinations(
        graph: ExecutionGraph, findings: list[ValidationFinding]
    ) -> None:
        """Check that edge types match valid node type combinations."""
        for i, edge in enumerate(graph._edges):
            src = graph._nodes.get(edge.source_id)
            tgt = graph._nodes.get(edge.target_id)
            if src is None or tgt is None:
                continue  # Already caught by _check_edge_node_references
            combo = (src.node_type, edge.edge_type, tgt.node_type)
            if combo not in _VALID_EDGE_COMBINATIONS:
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="INVALID_EDGE_COMBINATION",
                        message=(
                            f"Edge {i}: {src.node_type.value} "
                            f"--{edge.edge_type.value}--> "
                            f"{tgt.node_type.value} is not a valid combination"
                        ),
                        edge_index=i,
                    )
                )

    @staticmethod
    def _check_self_loops(graph: ExecutionGraph, findings: list[ValidationFinding]) -> None:
        """Detect self-referential edges."""
        for i, edge in enumerate(graph._edges):
            if edge.source_id == edge.target_id:
                findings.append(
                    ValidationFinding(
                        severity=Severity.ERROR,
                        code="SELF_LOOP",
                        message=f"Edge {i} is a self-loop on '{edge.source_id}'",
                        edge_index=i,
                        node_id=edge.source_id,
                    )
                )

    @staticmethod
    def _check_event_sequence_numbers(
        graph: ExecutionGraph, findings: list[ValidationFinding]
    ) -> None:
        """Warn if event nodes are missing sequence numbers."""
        for node in graph._nodes.values():
            if node.node_type == NodeType.EVENT and node.sequence_number is None:
                findings.append(
                    ValidationFinding(
                        severity=Severity.WARNING,
                        code="EVENT_MISSING_SEQUENCE",
                        message=f"Event node '{node.node_id}' has no sequence_number",
                        node_id=node.node_id,
                    )
                )

    @staticmethod
    def _check_isolated_nodes(graph: ExecutionGraph, findings: list[ValidationFinding]) -> None:
        """Warn about nodes with no edges."""
        for node_id in graph._nodes:
            has_edges = (
                len(graph._successors.get(node_id, [])) > 0
                or len(graph._predecessors.get(node_id, [])) > 0
            )
            if not has_edges:
                findings.append(
                    ValidationFinding(
                        severity=Severity.WARNING,
                        code="ISOLATED_NODE",
                        message=f"Node '{node_id}' has no edges",
                        node_id=node_id,
                    )
                )
