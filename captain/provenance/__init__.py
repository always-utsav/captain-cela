"""CAPTAIN provenance/lineage system.

This sub-package provides information-lineage analysis for canonical
execution traces.  It answers "where did this information come from?"
without performing causal inference.

Core types::

    from captain.provenance import (
        ProvenanceExtractor,
        ProvenanceQuery,
        ProvenanceRecord,
        RelationshipType,
    )
"""

from captain.provenance.extractor import ProvenanceExtractor
from captain.provenance.model import ProvenanceRecord, RelationshipType
from captain.provenance.query import ProvenanceQuery

__all__ = [
    "ProvenanceExtractor",
    "ProvenanceQuery",
    "ProvenanceRecord",
    "RelationshipType",
]
