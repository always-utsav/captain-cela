"""Failure-relevant region and candidate channel extraction.

Given a failed execution and its evidence-flow graph, this module:

1. Resolves the failure target to evidence node(s).
2. Discovers the failure-relevant evidence region (upstream).
3. Extracts candidate evidence-flow channels from that region.
4. Optionally ranks candidates by a non-causal screening score.

**Failure-relevant region ≠ causal ancestor set.**

The region is a candidate-search space. Causal responsibility
requires intervention + replay + outcome measurement (Stage 14).

**screening_score ≠ CEE ≠ causal probability.**

The score only answers: "How useful is this edge as a candidate
for later causal testing?"
"""

from __future__ import annotations

from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.model import EvidenceTransformation
from captain.failures.model import (
    Candidate,
    ChannelIntervention,
    ChannelInterventionType,
    Failure,
)


class FailureAnalyzer:
    """Extracts failure-relevant evidence region and candidates.

    Usage::

        analyzer = FailureAnalyzer(graph, failure)
        region = analyzer.relevant_region()
        candidates = analyzer.candidates()
        interventions = analyzer.interventions()
    """

    def __init__(
        self,
        graph: EvidenceFlowGraph,
        failure: Failure,
    ) -> None:
        self._graph = graph
        self._failure = failure

    # --- Failure target resolution ---

    def failure_targets(self) -> list[str]:
        """Resolve failure to evidence node IDs.

        Returns evidence IDs associated with the failure.
        If failure_evidence_ids are set, uses those directly.
        If failure_event_id is set, finds evidence created by
        that event.
        Falls back to the last evidence by sequence number.

        Returns empty list if no resolution is possible.
        """
        f = self._failure
        g = self._graph

        # Direct evidence IDs
        if f.failure_evidence_ids:
            valid = [eid for eid in f.failure_evidence_ids if g.get_evidence(eid) is not None]
            if valid:
                return valid

        # By event ID
        if f.failure_event_id:
            matches = [
                e.evidence_id for e in g.evidence if e.creation_event_id == f.failure_event_id
            ]
            if matches:
                return matches

        # Fallback: last evidence by sequence number
        if g.evidence:
            max_seq = max(e.sequence_number for e in g.evidence)
            return [e.evidence_id for e in g.evidence if e.sequence_number == max_seq]

        return []

    # --- Failure-relevant region ---

    def relevant_region(self) -> list[str]:
        """Discover failure-relevant evidence region.

        Returns all evidence IDs upstream of the failure
        targets (plus the targets themselves).

        This is a structural candidate-search space,
        NOT a causal ancestor set.

        Deterministic, cycle-safe.
        """
        targets = self.failure_targets()
        if not targets:
            return []

        region: set[str] = set(targets)
        for tid in targets:
            upstream = self._graph.upstream(tid)
            region.update(upstream)

        # Sort for determinism
        return sorted(region)

    # --- Candidate extraction ---

    def candidates(
        self,
        *,
        max_candidates: int = 0,
    ) -> list[Candidate]:
        """Extract candidate evidence-flow channels.

        Returns transformations within the failure-relevant
        region, ranked by non-causal screening score.

        Args:
            max_candidates: Maximum candidates to return.
                0 = no limit.
        """
        region = set(self.relevant_region())
        targets = set(self.failure_targets())
        if not region:
            return []

        run_id = self._failure.run_id
        candidates: list[Candidate] = []

        for tx in self._graph.transformations:
            # Both source and target must be in the region
            if tx.source_evidence_id not in region:
                continue
            if tx.target_evidence_id not in region:
                continue
            # No self-loops
            if tx.source_evidence_id == tx.target_evidence_id:
                continue

            dist = self._graph_distance(tx.target_evidence_id, targets)
            score = self._screening_score(tx, dist, targets)

            src_evi = self._graph.get_evidence(tx.source_evidence_id)
            tgt_evi = self._graph.get_evidence(tx.target_evidence_id)

            candidates.append(
                Candidate(
                    run_id=run_id,
                    source_evidence_id=tx.source_evidence_id,
                    target_evidence_id=tx.target_evidence_id,
                    transformation_type=tx.transformation_type.value,
                    event_id=tx.event_id,
                    source_evidence_type=src_evi.evidence_type.value if src_evi else "",
                    target_evidence_type=tgt_evi.evidence_type.value if tgt_evi else "",
                    sequence_number=tx.sequence_number,
                    graph_distance=dist,
                    screening_score=score,
                    provenance_method=tx.provenance_method.value,
                )
            )

        # Sort by screening score descending, then sequence
        candidates.sort(key=lambda c: (-c.screening_score, c.sequence_number))

        if max_candidates > 0:
            candidates = candidates[:max_candidates]

        return candidates

    # --- Intervention generation ---

    def interventions(
        self,
        *,
        max_candidates: int = 0,
    ) -> list[ChannelIntervention]:
        """Generate BLOCK interventions for candidate channels.

        Returns validated ChannelIntervention specifications.
        These are specifications only — execution happens in
        Stage 14.
        """
        cands = self.candidates(max_candidates=max_candidates)
        result: list[ChannelIntervention] = []

        for c in cands:
            result.append(
                ChannelIntervention(
                    intervention_type=ChannelInterventionType.BLOCK,
                    baseline_run_id=c.run_id,
                    source_evidence_id=c.source_evidence_id,
                    target_evidence_id=c.target_evidence_id,
                    event_id=c.event_id,
                    candidate_id=c.candidate_id,
                    description=(
                        f"Block {c.source_evidence_type}→{c.target_evidence_type} channel"
                    ),
                )
            )

        return result

    # --- Non-causal screening ---

    def _graph_distance(self, evi_id: str, targets: set[str]) -> int:
        """BFS distance from evidence to nearest failure target.

        Returns 0 if evi_id is a target, -1 if unreachable.
        """
        if evi_id in targets:
            return 0

        visited: set[str] = {evi_id}
        queue: list[tuple[str, int]] = [(evi_id, 0)]

        while queue:
            current, dist = queue.pop(0)
            for tx in self._graph.outgoing(current):
                tgt = tx.target_evidence_id
                if tgt in targets:
                    return dist + 1
                if tgt not in visited:
                    visited.add(tgt)
                    queue.append((tgt, dist + 1))

        return -1

    def _screening_score(
        self,
        tx: EvidenceTransformation,
        distance: int,
        targets: set[str],
    ) -> float:
        """Compute non-causal screening score.

        **This is NOT a causal probability or CEE estimate.**

        Higher score = more relevant as a candidate for
        later causal testing.

        Transparent, deterministic, configurable factors:
        - proximity: closer to failure → higher
        - reachability: can reach failure → bonus
        - direct: target IS a failure node → bonus
        """
        score = 0.0

        # Reachability bonus
        if distance >= 0:
            score += 1.0

        # Proximity (inverse distance, capped)
        if distance > 0:
            score += 1.0 / distance
        elif distance == 0:
            score += 2.0  # Direct failure edge

        # Target is failure evidence
        if tx.target_evidence_id in targets:
            score += 1.0

        return score
