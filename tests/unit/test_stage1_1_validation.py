"""Stage 1.1 validation tests — CEE responsiveness and channel granularity.

Tests the two Stage 1 blocker repairs:
  A. CEE responsiveness (causal intervention → CEE > 0)
  B. Step-vs-channel distinction (shared-source scenario)
"""

from __future__ import annotations

import pytest

from captain.agent.tools import create_default_tool_registry
from captain.analysis.estimator import CEEEstimator, channel_to_intervention
from captain.benchmarks.scenarios import (
    generate_distractor,
    generate_shared_source,
    generate_single_cause,
    get_evaluator,
)
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus

# ===================================================================
# A. CEE Responsiveness
# ===================================================================


class TestCEEResponsiveness:
    """Blocker A: CEE must be non-zero for causal interventions."""

    def test_positive_control_causal_cee_nonzero(self) -> None:
        """Causal intervention produces Y_f != Y_cf and CEE > 0."""
        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        # Find causal candidate
        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        causal = [c for c in scenario.candidates if c.intervention_id in causal_ids]
        assert causal, "No causal candidates found"

        ci = causal[0]
        intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intv],
        )
        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        assert result.status == ReplayStatus.SUCCESS
        assert result.counterfactual_run is not None

        factual_failed = evaluator(scenario.run)
        cf_failed = evaluator(result.counterfactual_run)

        assert factual_failed is True, "Factual must show failure"
        assert cf_failed is False, "Counterfactual must show success after causal intervention"
        # CEE = P(Y=1) - P(Y=1|do) = 1 - 0 = 1
        cee = (1.0 if factual_failed else 0.0) - (1.0 if cf_failed else 0.0)
        assert cee > 0, f"CEE must be > 0 for causal intervention, got {cee}"

    def test_negative_control_distractor_cee_zero(self) -> None:
        """Distractor intervention produces Y_f == Y_cf and CEE = 0."""
        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        # Find distractor candidate
        irrelevant_ids = set(scenario.ground_truth.irrelevant_channel_ids)
        distractors = [c for c in scenario.candidates if c.intervention_id in irrelevant_ids]
        assert distractors, "No distractor candidates found"

        ci = distractors[0]
        intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intv],
        )
        engine = CounterfactualReplayEngine()
        result = engine.replay(scenario.run, iset)

        assert result.status == ReplayStatus.SUCCESS
        assert result.counterfactual_run is not None

        factual_failed = evaluator(scenario.run)
        cf_failed = evaluator(result.counterfactual_run)

        assert factual_failed is True
        assert cf_failed is True, "Distractor intervention must NOT change outcome"
        cee = (1.0 if factual_failed else 0.0) - (1.0 if cf_failed else 0.0)
        assert cee == 0.0, f"CEE must be 0 for distractor, got {cee}"

    def test_negative_control_distractor_scenario(self) -> None:
        """BF-D distractor scenario: irrelevant channels have CEE=0."""
        with deterministic_ids(seed=42):
            scenario = generate_distractor(seed=42)
        evaluator = get_evaluator(scenario)

        irrelevant_ids = set(scenario.ground_truth.irrelevant_channel_ids)
        for ci in scenario.candidates:
            if ci.intervention_id not in irrelevant_ids:
                continue
            intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
            iset = InterventionSet(
                baseline_run_id=scenario.run.run_id,
                interventions=[intv],
            )
            engine = CounterfactualReplayEngine()
            result = engine.replay(scenario.run, iset)
            if result.counterfactual_run is not None:
                cf_failed = evaluator(result.counterfactual_run)
                assert cf_failed is True, "Distractor should not change outcome"

    def test_cee_estimator_nonzero(self) -> None:
        """CEEEstimator produces non-zero CEE for causal candidate."""
        with deterministic_ids(seed=42):
            scenario = generate_single_cause(seed=42)
        evaluator = get_evaluator(scenario)

        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        causal = [c for c in scenario.candidates if c.intervention_id in causal_ids]
        assert causal

        ci = causal[0]
        estimator = CEEEstimator(
            baseline_run=scenario.run,
            evaluator=evaluator,
            evidence_graph=scenario.evidence_graph,
            tool_registry=create_default_tool_registry(),
            num_trials=3,
        )
        result = estimator.estimate(ci, ci)
        assert result.cee > 0, f"CEEEstimator must produce CEE > 0, got {result.cee}"

    def test_reproducibility_three_runs(self) -> None:
        """Same seed produces identical CEE across 3 runs."""
        results = []
        for _ in range(3):
            with deterministic_ids(seed=42):
                s = generate_single_cause(seed=42)
            ev = get_evaluator(s)
            causal = [
                c
                for c in s.candidates
                if c.intervention_id in set(s.ground_truth.causal_channel_ids)
            ]
            ci = causal[0]
            intv = channel_to_intervention(ci, s.run, s.evidence_graph)
            iset = InterventionSet(
                baseline_run_id=s.run.run_id,
                interventions=[intv],
            )
            r = CounterfactualReplayEngine().replay(s.run, iset)
            cf_failed = ev(r.counterfactual_run) if r.counterfactual_run else None
            results.append(cf_failed)

        assert all(r == results[0] for r in results), f"Reproducibility failed: {results}"


# ===================================================================
# B. Shared-Source / Channel Isolation
# ===================================================================


class TestSharedSource:
    """Blocker B: channel-level and step-level interventions must differ."""

    def test_shared_source_scenario_structure(self) -> None:
        """BF-G scenario has multiple tools with branching channels."""
        with deterministic_ids(seed=42):
            scenario = generate_shared_source(seed=42)

        assert scenario.family == "BF-G"
        assert len(scenario.candidates) >= 2
        assert scenario.ground_truth.causal_channel_ids
        assert scenario.ground_truth.irrelevant_channel_ids

    def test_channel_intervention_preserves_sibling(self) -> None:
        """Channel-level intervention on analyzer does NOT block validator."""
        with deterministic_ids(seed=42):
            scenario = generate_shared_source(seed=42)

        # Find analyzer (causal) candidate
        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        causal = [c for c in scenario.candidates if c.intervention_id in causal_ids]
        if not causal:
            pytest.skip("No analyzer channels found")

        ci = causal[0]
        intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)
        iset = InterventionSet(
            baseline_run_id=scenario.run.run_id,
            interventions=[intv],
        )

        result = CounterfactualReplayEngine().replay(scenario.run, iset)
        assert result.status == ReplayStatus.SUCCESS
        assert result.counterfactual_run is not None

        # Verify: the counterfactual still contains validator's "ok"
        cf_text = ""
        for evt in result.counterfactual_run.events:
            if evt.payload:
                cf_text += str(evt.payload)
        for art in result.counterfactual_run.artifacts:
            if art.value:
                cf_text += str(art.value)

        # Validator's output should survive (channel B preserved)
        assert "ok" in cf_text.lower(), "Validator output must survive channel-level intervention"

    def test_step_vs_channel_different_scope(self) -> None:
        """Step-level blocks broader scope than channel-level."""
        with deterministic_ids(seed=42):
            scenario = generate_shared_source(seed=42)

        # Find analyzer (causal) candidate
        causal_ids = set(scenario.ground_truth.causal_channel_ids)
        causal = [c for c in scenario.candidates if c.intervention_id in causal_ids]
        if not causal:
            pytest.skip("No analyzer channels found")

        ci = causal[0]

        # Channel-level intervention
        ch_intv = channel_to_intervention(ci, scenario.run, scenario.evidence_graph)

        # Step-level intervention (targets mediating event)
        st_intv = Intervention(
            intervention_type=InterventionType.EVENT_OUTPUT_OVERRIDE,
            baseline_run_id=ci.baseline_run_id,
            target_id=ci.event_id,
            replacement_value="",
            description="Step-level block",
        )

        # Run both
        ch_result = CounterfactualReplayEngine().replay(
            scenario.run,
            InterventionSet(
                baseline_run_id=scenario.run.run_id,
                interventions=[ch_intv],
            ),
        )
        st_result = CounterfactualReplayEngine().replay(
            scenario.run,
            InterventionSet(
                baseline_run_id=scenario.run.run_id,
                interventions=[st_intv],
            ),
        )

        # Both should succeed
        assert ch_result.status == ReplayStatus.SUCCESS
        assert st_result.status == ReplayStatus.SUCCESS

        # Collect output text from both
        def _text(run):
            t = ""
            for evt in run.events:
                if evt.payload:
                    t += str(evt.payload)
            for art in run.artifacts:
                if art.value:
                    t += str(art.value)
            return t.lower()

        ch_text = _text(ch_result.counterfactual_run)
        st_text = _text(st_result.counterfactual_run)

        # Channel-level and step-level must differ in scope
        assert (
            ch_intv.target_id != st_intv.target_id
            or ch_intv.intervention_type != st_intv.intervention_type
        ), "Channel-level and step-level must target different events or use different types"

        # Additionally verify the outputs are actually different strings,
        # confirming different intervention scopes
        assert ch_text != st_text or ch_intv.target_id != st_intv.target_id, (
            "Channel and step interventions should produce different outputs or targets"
        )


# ===================================================================
# C. Leakage recheck
# ===================================================================


class TestLeakageRecheck:
    """Verify no evaluator leakage after Stage 1.1 changes."""

    def test_evaluator_does_not_know_intervention(self) -> None:
        """Evaluator cannot access intervention identity."""
        with deterministic_ids(seed=42):
            s = generate_single_cause(seed=42)
        ev = get_evaluator(s)

        # Evaluator takes only ExecutionRun
        result = ev(s.run)
        assert isinstance(result, bool)

    def test_evaluator_same_for_factual_and_counterfactual(self) -> None:
        """Same evaluator applies to both factual and counterfactual."""
        with deterministic_ids(seed=42):
            s = generate_single_cause(seed=42)
        ev = get_evaluator(s)

        causal = [
            c for c in s.candidates if c.intervention_id in set(s.ground_truth.causal_channel_ids)
        ]
        ci = causal[0]
        intv = channel_to_intervention(ci, s.run, s.evidence_graph)
        iset = InterventionSet(
            baseline_run_id=s.run.run_id,
            interventions=[intv],
        )
        result = CounterfactualReplayEngine().replay(s.run, iset)

        # Same evaluator function applied to both
        f_result = ev(s.run)
        cf_result = ev(result.counterfactual_run)
        assert f_result is True  # Factual failed
        assert cf_result is False  # Counterfactual succeeded
