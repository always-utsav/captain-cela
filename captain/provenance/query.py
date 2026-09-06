"""Provenance query API for CAPTAIN.

The :class:`ProvenanceQuery` provides lineage traversal over provenance
relationships extracted from an :class:`~captain.models.execution.ExecutionRun`.

It answers questions like:

- Which event produced this artifact?
- Which events consumed this artifact?
- What is the upstream provenance chain of an artifact?
- What is the downstream consumer chain?
- Is artifact A an ancestor of artifact B?

This is INFORMATION LINEAGE, not causal inference.
"""

from __future__ import annotations

from captain.models.execution import ExecutionRun
from captain.provenance.extractor import ProvenanceExtractor
from captain.provenance.model import ProvenanceRecord, RelationshipType


class ProvenanceQuery:
    """Query interface for artifact/event lineage.

    Builds internal indexes from provenance records for efficient
    lookups.  All results are deterministically ordered.

    Args:
        run: The execution run to query provenance for.
        records: Optional pre-extracted records.  If ``None``,
            :class:`ProvenanceExtractor` is used automatically.
    """

    def __init__(
        self,
        run: ExecutionRun,
        records: list[ProvenanceRecord] | None = None,
    ) -> None:
        self._run = run
        self._records = records if records is not None else ProvenanceExtractor(run).extract()

        # Build indexes
        self._artifact_map = {a.artifact_id: a for a in run.artifacts}
        self._event_map = {e.event_id: e for e in run.events}

        # artifact_id -> producer event_id
        self._producers: dict[str, str] = {}
        # artifact_id -> list of consumer event_ids
        self._consumers: dict[str, list[str]] = {}
        # event_id -> list of output artifact_ids
        self._event_outputs: dict[str, list[str]] = {}
        # event_id -> list of input artifact_ids
        self._event_inputs: dict[str, list[str]] = {}

        for rec in self._records:
            if rec.relationship == RelationshipType.PRODUCED:
                self._producers[rec.artifact_id] = rec.event_id
                self._event_outputs.setdefault(rec.event_id, []).append(rec.artifact_id)
            elif rec.relationship == RelationshipType.CONSUMED:
                self._consumers.setdefault(rec.artifact_id, []).append(rec.event_id)
                self._event_inputs.setdefault(rec.event_id, []).append(rec.artifact_id)

    @property
    def records(self) -> list[ProvenanceRecord]:
        """All extracted provenance records."""
        return list(self._records)

    # --- Direct queries -----------------------------------------------------

    def get_producer(self, artifact_id: str) -> str | None:
        """Return the event ID that produced *artifact_id*, or None."""
        return self._producers.get(artifact_id)

    def get_consumers(self, artifact_id: str) -> list[str]:
        """Return event IDs that consumed *artifact_id*, sorted."""
        return sorted(self._consumers.get(artifact_id, []))

    def get_upstream_artifacts(self, event_id: str) -> list[str]:
        """Return artifact IDs consumed by *event_id* (direct inputs)."""
        return sorted(self._event_inputs.get(event_id, []))

    def get_downstream_artifacts(self, event_id: str) -> list[str]:
        """Return artifact IDs produced by *event_id* (direct outputs)."""
        return sorted(self._event_outputs.get(event_id, []))

    # --- Multi-hop traversal ------------------------------------------------

    def trace_upstream(self, artifact_id: str) -> list[str]:
        """Trace artifact upstream to its origins.

        Returns an ordered list of artifact IDs forming the upstream
        provenance chain, starting from *artifact_id* and traversing
        backwards through producer events and their input artifacts.

        Protected against cycles via visited-set tracking.
        """
        chain: list[str] = []
        visited: set[str] = set()
        self._traverse_upstream(artifact_id, chain, visited)
        return chain

    def trace_downstream(self, artifact_id: str) -> list[str]:
        """Trace artifact downstream through its consumers.

        Returns an ordered list of artifact IDs reachable by following
        consumer events and their output artifacts.

        Protected against cycles via visited-set tracking.
        """
        chain: list[str] = []
        visited: set[str] = set()
        self._traverse_downstream(artifact_id, chain, visited)
        return chain

    def is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if *ancestor_id* is an upstream ancestor of *descendant_id*.

        Traverses the upstream chain of *descendant_id* looking for
        *ancestor_id*.
        """
        if ancestor_id == descendant_id:
            return False
        upstream = self.trace_upstream(descendant_id)
        return ancestor_id in upstream

    def is_descendant(self, descendant_id: str, ancestor_id: str) -> bool:
        """Check if *descendant_id* is a downstream descendant of *ancestor_id*."""
        return self.is_ancestor(ancestor_id, descendant_id)

    # --- Internal traversal -------------------------------------------------

    def _traverse_upstream(
        self,
        artifact_id: str,
        chain: list[str],
        visited: set[str],
    ) -> None:
        """Recursively traverse upstream provenance."""
        if artifact_id in visited:
            return
        visited.add(artifact_id)

        producer_event_id = self._producers.get(artifact_id)
        if producer_event_id is None:
            return

        # Get input artifacts of the producer event
        input_arts = sorted(self._event_inputs.get(producer_event_id, []))
        for inp_art_id in input_arts:
            if inp_art_id not in visited:
                chain.append(inp_art_id)
                self._traverse_upstream(inp_art_id, chain, visited)

    def _traverse_downstream(
        self,
        artifact_id: str,
        chain: list[str],
        visited: set[str],
    ) -> None:
        """Recursively traverse downstream consumers."""
        if artifact_id in visited:
            return
        visited.add(artifact_id)

        consumer_event_ids = sorted(self._consumers.get(artifact_id, []))
        for consumer_id in consumer_event_ids:
            # Get output artifacts of the consumer event
            output_arts = sorted(self._event_outputs.get(consumer_id, []))
            for out_art_id in output_arts:
                if out_art_id not in visited:
                    chain.append(out_art_id)
                    self._traverse_downstream(out_art_id, chain, visited)
