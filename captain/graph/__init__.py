"""CAPTAIN execution graph infrastructure.

This sub-package provides the structural execution graph representation,
builder, validation, and analysis for canonical agent executions.

Core types::

    from captain.graph import (
        ExecutionGraph,
        ExecutionGraphBuilder,
        GraphAnalyzer,
        GraphValidator,
        GraphNode,
        GraphEdge,
        NodeType,
        EdgeType,
        ValidationResult,
    )
"""

from captain.graph.analysis import GraphAnalyzer
from captain.graph.builder import ExecutionGraphBuilder
from captain.graph.model import EdgeType, ExecutionGraph, GraphEdge, GraphNode, NodeType
from captain.graph.validation import GraphValidator, Severity, ValidationFinding, ValidationResult

__all__ = [
    "EdgeType",
    "ExecutionGraph",
    "ExecutionGraphBuilder",
    "GraphAnalyzer",
    "GraphEdge",
    "GraphNode",
    "GraphValidator",
    "NodeType",
    "Severity",
    "ValidationFinding",
    "ValidationResult",
]
