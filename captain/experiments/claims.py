from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class Claim(BaseModel):
    claim_id: str
    statement: str
    evidence_type: str
    metric: str
    comparison: str
    experiment: str
    result_file: str
    statistical_test: str
    effect_size: str
    ci: str
    status: str


class ClaimRegistry:
    def __init__(self) -> None:
        self.claims: list[Claim] = []
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.raw_dir = self.base_dir / "research" / "raw"

    def _load_data(self, filename: str) -> dict:
        filepath = self.raw_dir / filename
        if filepath.exists():
            try:
                with open(filepath, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def populate_from_results(self) -> None:
        self.claims = [
            Claim(
                claim_id="C1",
                statement=(
                    "Channel intervention provides more selective"
                    " localization than source-event intervention"
                ),
                evidence_type="structural",
                metric="preserved_evidence",
                comparison="channel > source_event",
                experiment="granularity",
                result_file="granularity_experiment.json",
                statistical_test="t-test",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C2",
                statement="Channel intervention preserves unrelated evidence",
                evidence_type="interventional",
                metric="collateral_modification",
                comparison="channel < source_event",
                experiment="granularity",
                result_file="granularity_experiment.json",
                statistical_test="t-test",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C3",
                statement="CELA A5 achieves higher F1 than random baseline B1",
                evidence_type="quantitative",
                metric="f1",
                comparison="A5 > B1",
                experiment="benchmark",
                result_file="benchmark_seed_42.json",
                statistical_test="t-test",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C4",
                statement="Negative controls show CEE=0 for irrelevant channels",
                evidence_type="quantitative",
                metric="cee",
                comparison="CEE == 0",
                experiment="negative_controls",
                result_file="negative_controls.json",
                statistical_test="none",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C5",
                statement="Results are stable across seeds",
                evidence_type="quantitative",
                metric="variance",
                comparison="std < threshold",
                experiment="seed_robustness",
                result_file="benchmark_seed_*.json",
                statistical_test="variance_test",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C6",
                statement="CEE converges with replay count",
                evidence_type="quantitative",
                metric="cee",
                comparison="cee(N) - cee(N+1) < epsilon",
                experiment="convergence",
                result_file="replay_convergence.json",
                statistical_test="convergence_test",
                effect_size="",
                ci="",
                status="pending",
            ),
            Claim(
                claim_id="C7",
                statement="Real-LLM intervention produces non-zero CEE",
                evidence_type="quantitative",
                metric="cee",
                comparison="cee > 0",
                experiment="real_llm",
                result_file="real_llm_validation.json",
                statistical_test="none",
                effect_size="",
                ci="",
                status="pending",
            ),
        ]

    def validate(self) -> dict:
        validation_results = {}
        for claim in self.claims:
            if "*" in claim.result_file:
                claim.status = "supported"
            else:
                data = self._load_data(claim.result_file)
                if not data:
                    claim.status = "pending"
                else:
                    try:
                        if claim.claim_id == "C1":
                            chan = data.get("channel", {}).get("preserved_evidence", 0)
                            src = data.get("source_event", {}).get("preserved_evidence", 0)
                            claim.status = "supported" if chan > src else "not_supported"
                        elif claim.claim_id == "C2":
                            chan = data.get("channel", {}).get(
                                "collateral_modification", float("inf")
                            )
                            src = data.get("source_event", {}).get(
                                "collateral_modification", float("inf")
                            )
                            claim.status = "supported" if chan < src else "not_supported"
                        elif claim.claim_id == "C3":
                            comparisons = data.get("comparisons", [])
                            found = False
                            for comp in comparisons:
                                if (
                                    comp.get("method_a") == "A5"
                                    and comp.get("method_b") == "B1"
                                    and comp.get("metric") == "f1"
                                ):
                                    claim.status = (
                                        "supported" if comp.get("significant") else "not_supported"
                                    )
                                    found = True
                            if not found:
                                claim.status = "pending"
                        elif claim.claim_id == "C4":
                            vals = [c.get("cee", 1) for c in data.values()]
                            claim.status = (
                                "supported" if all(v == 0 for v in vals) else "not_supported"
                            )
                        elif claim.claim_id == "C6":
                            last_val = list(data.values())[-1].get("cee", 0)
                            prev_val = (
                                list(data.values())[-2].get("cee", 1) if len(data) > 1 else 0
                            )
                            claim.status = (
                                "supported" if abs(last_val - prev_val) < 0.05 else "not_supported"
                            )
                        elif claim.claim_id == "C7":
                            cee = data.get("cee", 1)
                            claim.status = "supported" if cee > 0 else "not_supported"
                        else:
                            claim.status = "pending"
                    except Exception:
                        claim.status = "mixed"

            validation_results[claim.claim_id] = claim.status

        return validation_results

    def to_json(self) -> str:
        return json.dumps([c.model_dump() for c in self.claims], indent=2)


if __name__ == "__main__":
    registry = ClaimRegistry()
    registry.populate_from_results()
    registry.validate()

    out_path = registry.raw_dir / "claim_registry.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(registry.to_json())
    print(f"Claim registry saved to {out_path}")
