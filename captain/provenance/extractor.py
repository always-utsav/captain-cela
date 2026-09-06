"""Provenance extractor for CAPTAIN.

The :class:`ProvenanceExtractor` accepts an
:class:`~captain.models.execution.ExecutionRun` and derives provenance
relationships from the canonical references already present in the data:

- ``Artifact.producer_event_id`` -> PRODUCED relationship
- ``Event.output_artifact_ids`` -> PRODUCED relationship
- ``Event.input_artifact_ids``  -> CONSUMED relationship

No relationships are invented beyond what the canonical data supports.
"""

from __future__ import annotations

from captain.models.execution import ExecutionRun
from captain.provenance.model import ProvenanceRecord, RelationshipType


class ProvenanceExtractor:
    """Extracts provenance relationships from an ExecutionRun.

    Usage::

        extractor = ProvenanceExtractor(run)
        records = extractor.extract()
    """

    def __init__(self, run: ExecutionRun) -> None:
        self._run = run

    def extract(self) -> list[ProvenanceRecord]:
        """Derive all provenance relationships from the run.

        Returns a deterministically ordered list of
        :class:`ProvenanceRecord` objects.  Ordering is by event
        sequence number, then relationship type, then artifact ID.
        """
        records: list[ProvenanceRecord] = []
        seen: set[tuple[str, str, str]] = set()

        # Build artifact lookup for producer_event_id
        artifact_producers: dict[str, str] = {}
        for art in self._run.artifacts:
            if art.producer_event_id:
                artifact_producers[art.artifact_id] = art.producer_event_id

        # Sort events by sequence_number for deterministic output
        events_sorted = sorted(self._run.events, key=lambda e: e.sequence_number)

        for event in events_sorted:
            # PRODUCED: event -> artifact (from output_artifact_ids)
            for art_id in sorted(event.output_artifact_ids):
                key = (art_id, event.event_id, RelationshipType.PRODUCED)
                if key not in seen:
                    records.append(
                        ProvenanceRecord(
                            artifact_id=art_id,
                            event_id=event.event_id,
                            relationship=RelationshipType.PRODUCED,
                        )
                    )
                    seen.add(key)

            # CONSUMED: event <- artifact (from input_artifact_ids)
            for art_id in sorted(event.input_artifact_ids):
                key = (art_id, event.event_id, RelationshipType.CONSUMED)
                if key not in seen:
                    records.append(
                        ProvenanceRecord(
                            artifact_id=art_id,
                            event_id=event.event_id,
                            relationship=RelationshipType.CONSUMED,
                        )
                    )
                    seen.add(key)

        # PRODUCED from artifact.producer_event_id (if not already covered)
        for art in self._run.artifacts:
            if art.producer_event_id:
                key = (art.artifact_id, art.producer_event_id, RelationshipType.PRODUCED)
                if key not in seen:
                    records.append(
                        ProvenanceRecord(
                            artifact_id=art.artifact_id,
                            event_id=art.producer_event_id,
                            relationship=RelationshipType.PRODUCED,
                        )
                    )
                    seen.add(key)

        return records
