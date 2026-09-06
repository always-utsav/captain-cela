"""Hard-provenance lineage extraction from ExecutionRun.

Constructs :class:`~captain.evidence.model.Evidence` objects and
:class:`~captain.evidence.model.EvidenceTransformation` edges
from an existing CAPTAIN :class:`~captain.models.execution.ExecutionRun`
using **deterministic hard provenance only**.

No semantic similarity, embeddings, or LLM inference is used.

The lineage builder reuses the existing
:class:`~captain.provenance.extractor.ProvenanceExtractor` and
canonical event/artifact references to derive evidence relationships.

Usage::

    builder = EvidenceLineageBuilder(run)
    evidence, transformations = builder.build()
"""

from __future__ import annotations

from captain.evidence.model import (
    Evidence,
    EvidenceTransformation,
    EvidenceType,
    ProvenanceMethod,
    TransformationType,
)
from captain.models.enums import ArtifactType, EventType
from captain.models.events import Event
from captain.models.execution import ExecutionRun
from captain.provenance.extractor import ProvenanceExtractor
from captain.provenance.model import RelationshipType

# ===================================================================
# Artifact-type → evidence-type mapping
# ===================================================================

_ART_TO_EVI: dict[ArtifactType, EvidenceType] = {
    ArtifactType.TEXT: EvidenceType.TEXT,
    ArtifactType.IMAGE: EvidenceType.IMAGE,
    ArtifactType.STRUCTURED_DATA: EvidenceType.STRUCTURED,
    ArtifactType.FILE: EvidenceType.TEXT,
    ArtifactType.TOOL_OUTPUT: EvidenceType.TOOL_OUTPUT,
    ArtifactType.MODEL_OUTPUT: EvidenceType.MODEL_OUTPUT,
}


def _evidence_type_for_event(
    evt: Event,
) -> EvidenceType:
    """Derive evidence type from event context."""
    et = evt.event_type
    if et == EventType.MEMORY_WRITE:
        return EvidenceType.MEMORY
    if et == EventType.TOOL_CALL:
        return EvidenceType.TOOL_INPUT
    if et == EventType.TOOL_RESULT:
        return EvidenceType.TOOL_OUTPUT
    if et == EventType.REASONING:
        return EvidenceType.MODEL_OUTPUT
    if et == EventType.PLANNING:
        return EvidenceType.STRUCTURED
    return EvidenceType.TEXT


def _transformation_type(
    src_evt: Event | None,
    tgt_evt: Event,
) -> TransformationType:
    """Derive transformation type from event types."""
    et = tgt_evt.event_type
    if et == EventType.INPUT:
        return TransformationType.OBSERVATION
    if et == EventType.REASONING:
        return TransformationType.INTERPRETATION
    if et == EventType.MEMORY_WRITE:
        return TransformationType.MEMORY_STORE
    if et == EventType.PLANNING:
        return TransformationType.PLANNING_DERIVATION
    if et == EventType.TOOL_CALL:
        return TransformationType.TOOL_DISPATCH
    if et == EventType.TOOL_RESULT:
        return TransformationType.TOOL_RETURN
    if et == EventType.OUTPUT:
        return TransformationType.RESPONSE_DERIVATION
    return TransformationType.INTERPRETATION


# ===================================================================
# Lineage builder
# ===================================================================


class EvidenceLineageBuilder:
    """Constructs evidence and transformations from an ExecutionRun.

    Uses deterministic hard provenance only. Reuses the existing
    :class:`~captain.provenance.extractor.ProvenanceExtractor`
    to derive canonical relationships.

    Usage::

        builder = EvidenceLineageBuilder(run)
        evidence, transformations = builder.build()
    """

    def __init__(self, run: ExecutionRun) -> None:
        self._run = run

    def build(
        self,
    ) -> tuple[list[Evidence], list[EvidenceTransformation]]:
        """Extract evidence and transformations.

        Returns:
            Tuple of (evidence_list, transformation_list).
            Both lists are deterministically ordered by
            sequence number.
        """
        run = self._run

        # Index events
        evt_by_id = {e.event_id: e for e in run.events}
        events_sorted = sorted(run.events, key=lambda e: e.sequence_number)

        # --- Phase 1: Create evidence for each artifact ---
        art_evi: dict[str, str] = {}  # artifact_id -> evidence_id
        evidence: list[Evidence] = []

        for art in run.artifacts:
            evi_type = _ART_TO_EVI.get(art.artifact_type, EvidenceType.TEXT)

            # Refine by producing event
            prod_evt = None
            if art.producer_event_id:
                prod_evt = evt_by_id.get(art.producer_event_id)
                if prod_evt:
                    ctx_type = _evidence_type_for_event(prod_evt)
                    if ctx_type != EvidenceType.TEXT:
                        evi_type = ctx_type

            seq = 0
            if prod_evt:
                seq = prod_evt.sequence_number

            evi = Evidence(
                evidence_type=evi_type,
                artifact_id=art.artifact_id,
                creation_event_id=(art.producer_event_id or ""),
                sequence_number=seq,
            )
            art_evi[art.artifact_id] = evi.evidence_id
            evidence.append(evi)

        # --- Phase 2: Create evidence for event payloads ---
        # Memory writes and tool calls may carry payload-only
        # evidence not captured by artifacts
        evt_evi: dict[str, str] = {}  # event_id -> evidence_id

        for evt in events_sorted:
            if evt.event_type == EventType.MEMORY_WRITE and not evt.output_artifact_ids:
                evi = Evidence(
                    evidence_type=EvidenceType.MEMORY,
                    creation_event_id=evt.event_id,
                    sequence_number=evt.sequence_number,
                    metadata={
                        "key": evt.payload.get("key", ""),
                    },
                )
                evt_evi[evt.event_id] = evi.evidence_id
                evidence.append(evi)

            if evt.event_type == EventType.TOOL_CALL and not any(
                a_id in art_evi for a_id in evt.output_artifact_ids
            ):
                evi = Evidence(
                    evidence_type=EvidenceType.TOOL_INPUT,
                    creation_event_id=evt.event_id,
                    sequence_number=evt.sequence_number,
                    metadata={
                        "tool_name": evt.payload.get("tool_name", ""),
                    },
                )
                evt_evi[evt.event_id] = evi.evidence_id
                evidence.append(evi)

        # --- Phase 3: Build transformations from provenance ---
        prov = ProvenanceExtractor(run)
        records = prov.extract()

        # Track which artifacts are produced/consumed by events
        produced: dict[str, str] = {}  # art_id -> event_id
        consumed: dict[str, list[str]] = {}  # event_id -> [art_ids]

        for rec in records:
            if rec.relationship == RelationshipType.PRODUCED:
                produced[rec.artifact_id] = rec.event_id
            elif rec.relationship == RelationshipType.CONSUMED:
                consumed.setdefault(rec.event_id, []).append(rec.artifact_id)

        transformations: list[EvidenceTransformation] = []

        # For each consuming event, create edges from consumed
        # artifacts' evidence to produced artifacts' evidence
        for evt in events_sorted:
            eid = evt.event_id
            in_arts = consumed.get(eid, [])
            out_arts = [a_id for a_id in evt.output_artifact_ids if a_id in art_evi]

            for src_aid in sorted(in_arts):
                src_evi_id = art_evi.get(src_aid)
                if not src_evi_id:
                    continue
                for tgt_aid in sorted(out_arts):
                    tgt_evi_id = art_evi.get(tgt_aid)
                    if not tgt_evi_id:
                        continue
                    if src_evi_id == tgt_evi_id:
                        continue

                    src_evt = None
                    if src_aid in produced:
                        src_evt = evt_by_id.get(produced[src_aid])

                    transformations.append(
                        EvidenceTransformation(
                            source_evidence_id=src_evi_id,
                            target_evidence_id=tgt_evi_id,
                            transformation_type=(_transformation_type(src_evt, evt)),
                            event_id=eid,
                            provenance_method=ProvenanceMethod.HARD,
                            confidence=1.0,
                            sequence_number=evt.sequence_number,
                        )
                    )

            # Event-payload evidence: connect input artifacts
            # to payload-only evidence
            if eid in evt_evi:
                tgt_evi_id = evt_evi[eid]
                for src_aid in sorted(in_arts):
                    src_evi_id = art_evi.get(src_aid)
                    if not src_evi_id:
                        continue
                    src_evt = None
                    if src_aid in produced:
                        src_evt = evt_by_id.get(produced[src_aid])

                    transformations.append(
                        EvidenceTransformation(
                            source_evidence_id=src_evi_id,
                            target_evidence_id=tgt_evi_id,
                            transformation_type=(_transformation_type(src_evt, evt)),
                            event_id=eid,
                            provenance_method=ProvenanceMethod.HARD,
                            confidence=1.0,
                            sequence_number=evt.sequence_number,
                        )
                    )

        # --- Phase 4: Set parent evidence IDs ---
        evi_by_id = {e.evidence_id: e for e in evidence}
        for tx in transformations:
            tgt = evi_by_id.get(tx.target_evidence_id)
            if tgt and tx.source_evidence_id not in tgt.parent_evidence_ids:
                tgt.parent_evidence_ids.append(tx.source_evidence_id)

        # Sort for determinism
        evidence.sort(key=lambda e: e.sequence_number)
        transformations.sort(
            key=lambda t: (
                t.sequence_number,
                t.source_evidence_id,
                t.target_evidence_id,
            )
        )

        return evidence, transformations
