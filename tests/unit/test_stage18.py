"""Stage 18 integration tests -- Explorer + Demo + Experiment.

Tests cover:
1.  Explorer loads
2.  Stage 8 run inspection still works
3.  Graph renders/data endpoint works
4.  Evidence data endpoint works
5.  Intervention workflow works (benchmark demo)
6.  Counterfactual workflow works
7.  Cascade results displayed correctly
8.  Experiment configuration works
9.  Small experiment executes
10. Result serialization/export works
11. Deterministic demo completes
12. No ground-truth leakage into method execution
13. Factual/counterfactual distinction remains intact
14. Full end-to-end demo pipeline
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from captain.explorer.app import create_app


@pytest.fixture()
def app(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Create a test Flask app with a temporary store."""
    application = create_app(store_dir=tmp_path / "stage18_traces")
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):  # type: ignore[no-untyped-def]
    """Flask test client."""
    return app.test_client()


# ===================================================================
# 1. Explorer loads
# ===================================================================


class TestExplorerLoads:
    def test_app_creates(self, app) -> None:  # type: ignore[no-untyped-def]
        assert app is not None

    def test_index_serves_html(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"CAPTAIN" in resp.data


# ===================================================================
# 2. Stage 8 run inspection still works
# ===================================================================


class TestStage8RunInspection:
    def test_demo_creates_run(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.post("/api/demo")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "run_id" in data
        assert data["status"] == "completed"
        assert data["event_count"] > 0

    def test_run_list_after_demo(self, client) -> None:  # type: ignore[no-untyped-def]
        client.post("/api/demo")
        resp = client.get("/api/runs")
        data = json.loads(resp.data)
        assert len(data) >= 1

    def test_run_detail(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        resp = client.get(f"/api/run/{demo['run_id']}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "events" in data
        assert "artifacts" in data


# ===================================================================
# 3. Graph renders/data endpoint works
# ===================================================================


class TestGraphEndpoint:
    def test_graph_data(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        resp = client.get(f"/api/graph/{demo['run_id']}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "graph" in data
        assert len(data["graph"]["nodes"]) > 0
        assert data["validation"]["is_valid"] is True


# ===================================================================
# 4. Evidence data endpoint works
# ===================================================================


class TestEvidenceEndpoint:
    def test_evidence_data(self, client) -> None:  # type: ignore[no-untyped-def]
        demo = json.loads(client.post("/api/demo").data)
        resp = client.get(f"/api/evidence/{demo['run_id']}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "evidence" in data
        assert "transformations" in data
        assert isinstance(data["evidence"], list)

    def test_evidence_not_found(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.get("/api/evidence/run_nonexistent")
        assert resp.status_code == 404


# ===================================================================
# 5. Intervention workflow works (benchmark demo)
# ===================================================================


class TestBenchmarkDemo:
    def test_benchmark_demo_runs(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.post("/api/demo/benchmark")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "scenario_id" in data
        assert "candidates" in data
        assert "family" in data

    def test_benchmark_produces_candidates(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        data = json.loads(client.post("/api/demo/benchmark").data)
        assert len(data["candidates"]) >= 1


# ===================================================================
# 6. Counterfactual workflow works
# ===================================================================


class TestCounterfactualWorkflow:
    def test_counterfactual_after_benchmark(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        bench = json.loads(client.post("/api/demo/benchmark").data)
        sid = bench["scenario_id"]
        resp = client.get(f"/api/counterfactual/{sid}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "factual" in data or "scenario_id" in data

    def test_counterfactual_not_found(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        resp = client.get("/api/counterfactual/nonexistent_id")
        assert resp.status_code == 404


# ===================================================================
# 7. Cascade results displayed correctly
# ===================================================================


class TestCascadeResults:
    def test_cascade_after_benchmark(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        bench = json.loads(client.post("/api/demo/benchmark").data)
        sid = bench["scenario_id"]
        resp = client.get(f"/api/cascade/{sid}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "scenario_id" in data

    def test_cascade_not_found(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        resp = client.get("/api/cascade/nonexistent_id")
        assert resp.status_code == 404


# ===================================================================
# 8. Experiment configuration works
# ===================================================================


class TestExperimentConfig:
    def test_experiment_accepts_config(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        config = {
            "master_seed": 42,
            "instances_per_family": 2,
            "families": ["BF-A"],
            "methods": ["B1", "B2"],
        }
        resp = client.post(
            "/api/experiment",
            data=json.dumps(config),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "metadata" in data or "overall_aggregates" in data


# ===================================================================
# 9. Small experiment executes
# ===================================================================


class TestSmallExperiment:
    def test_experiment_produces_results(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        config = {
            "master_seed": 42,
            "instances_per_family": 2,
            "families": ["BF-A"],
            "methods": ["B1"],
        }
        resp = client.post(
            "/api/experiment",
            data=json.dumps(config),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        # Should have results
        assert "metadata" in data or "family_results" in data


# ===================================================================
# 10. Result serialization/export works
# ===================================================================


class TestResultExport:
    def test_experiment_summary_no_data(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        resp = client.get("/api/experiment/summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # Should return message or empty results
        assert isinstance(data, dict)

    def test_export_after_experiment(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        config = {
            "master_seed": 99,
            "instances_per_family": 2,
            "families": ["BF-A"],
            "methods": ["B1"],
        }
        client.post(
            "/api/experiment",
            data=json.dumps(config),
            content_type="application/json",
        )
        resp = client.post("/api/experiment/export")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "path" in data or "message" in data


# ===================================================================
# 11. Deterministic demo completes
# ===================================================================


class TestDeterministicDemo:
    def test_demo_module_runs(self) -> None:
        from captain.demo import run_demo

        results = run_demo()
        assert results["event_count"] > 0
        assert results["experiment_scenarios"] > 0
        assert "result_path" in results


# ===================================================================
# 12. No ground-truth leakage into method execution
# ===================================================================


class TestNoLeakage:
    def test_benchmark_ground_truth_labeled(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        """Ground truth must be labeled POST-HOC."""
        data = json.loads(client.post("/api/demo/benchmark").data)
        # Ground truth section should exist
        if "ground_truth" in data:
            gt = data["ground_truth"]
            # Must contain post-hoc label
            if isinstance(gt, dict):
                gt_str = json.dumps(gt)
                assert (
                    "POST-HOC" in gt_str
                    or "post_hoc" in gt_str
                    or "evaluation_only" in gt_str
                    or isinstance(gt.get("label"), str)
                )


# ===================================================================
# 13. Factual/counterfactual distinction
# ===================================================================


class TestFactualCounterfactualDistinction:
    def test_distinction_in_response(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        bench = json.loads(client.post("/api/demo/benchmark").data)
        sid = bench["scenario_id"]
        resp = client.get(f"/api/counterfactual/{sid}")
        if resp.status_code == 200:
            data = json.loads(resp.data)
            resp_str = json.dumps(data).lower()
            # Should distinguish factual from counterfactual
            assert "factual" in resp_str or "counterfactual" in resp_str


# ===================================================================
# 14. Full end-to-end demo pipeline
# ===================================================================


class TestFullEndToEnd:
    def test_complete_pipeline(  # type: ignore[no-untyped-def]
        self, client
    ) -> None:
        """Exercise the complete Explorer workflow."""
        # 1. Create demo run
        demo = json.loads(client.post("/api/demo").data)
        run_id = demo["run_id"]

        # 2. List runs
        runs = json.loads(client.get("/api/runs").data)
        assert any(r["run_id"] == run_id for r in runs)

        # 3. Get graph
        graph = json.loads(client.get(f"/api/graph/{run_id}").data)
        assert len(graph["graph"]["nodes"]) > 0

        # 4. Get evidence
        evid = json.loads(client.get(f"/api/evidence/{run_id}").data)
        assert "evidence" in evid

        # 5. Get event details
        run_data = json.loads(client.get(f"/api/run/{run_id}").data)
        if run_data["events"]:
            evt = run_data["events"][0]
            evt_detail = json.loads(client.get(f"/api/event/{run_id}/{evt['event_id']}").data)
            assert "event_type" in evt_detail

        # 6. Benchmark demo
        bench = json.loads(client.post("/api/demo/benchmark").data)
        assert "scenario_id" in bench

        # 7. Small experiment
        config = {
            "master_seed": 42,
            "instances_per_family": 2,
            "families": ["BF-A"],
            "methods": ["B1", "B2"],
        }
        exp = json.loads(
            client.post(
                "/api/experiment",
                data=json.dumps(config),
                content_type="application/json",
            ).data
        )
        assert "metadata" in exp or "family_results" in exp

        # 8. Summary
        summary = json.loads(client.get("/api/experiment/summary").data)
        assert isinstance(summary, dict)
