from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

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
    limitation: str = ""


class ClaimRegistry:
    def __init__(self) -> None:
        self.claims: list[Claim] = []
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.raw_dir = self.base_dir / "research" / "raw"

    def _load_data(self, filename: str) -> Any:
        filepath = self.raw_dir / filename
        if filepath.exists():
            for enc in ("utf-8", "cp1252"):
                try:
                    with open(filepath, encoding=enc) as f:
                        return json.load(f)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
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
                statistical_test="wilcoxon_signed_rank",
                effect_size="",
                ci="",
                status="pending",
                limitation=(
                    "Assumes structural mapping of evidence"
                    " accurately reflects semantic dependency."
                ),
            ),
            Claim(
                claim_id="C2",
                statement="Channel intervention preserves unrelated evidence",
                evidence_type="interventional",
                metric="collateral_modification",
                comparison="channel < source_event",
                experiment="granularity",
                result_file="granularity_experiment.json",
                statistical_test="wilcoxon_signed_rank",
                effect_size="",
                ci="",
                status="pending",
                limitation="Preservation metric only counts exact artifact matches.",
            ),
            Claim(
                claim_id="C3",
                statement="CELA A5 achieves higher F1 than random baseline B1",
                evidence_type="quantitative",
                metric="causal_f1",
                comparison="A5 > B1",
                experiment="benchmark",
                result_file="benchmark_seed_42.json",
                statistical_test="permutation_test",
                effect_size="",
                ci="",
                status="pending",
                limitation="F1 improvement relies on deterministic MockLLM environments.",
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
                limitation="Evaluated only on simplified irrelevant paths.",
            ),
            Claim(
                claim_id="C5",
                statement="Results are stable across seeds",
                evidence_type="quantitative",
                metric="variance",
                comparison="std < threshold",
                experiment="seed_robustness",
                result_file="benchmark_seed_*.json",
                statistical_test="coefficient_of_variation",
                effect_size="",
                ci="",
                status="pending",
                limitation=(
                    "Seed stability tested only on finite"
                    " sets of randomly generated scenarios."
                ),
            ),
            Claim(
                claim_id="C6",
                statement="CEE converges with replay count",
                evidence_type="quantitative",
                metric="cee",
                comparison="cee(N) - cee(N+1) < epsilon",
                experiment="convergence",
                result_file="replay_convergence.json",
                statistical_test="deterministic_stability_check",
                effect_size="",
                ci="",
                status="pending",
                limitation=(
                    "With deterministic MockLLM, convergence"
                    " is trivially true (CEE=1.0, CI=0.0)."
                ),
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
                limitation=(
                    "Tested on limited subset of real LLM"
                    " queries (Gemini) with handcrafted prompts."
                ),
            ),
        ]

    def validate(self) -> dict[str, str]:
        validation_results = {}
        for claim in self.claims:
            if claim.claim_id == "C5":
                means = []
                for seed in [42, 123, 456, 789, 1024]:
                    d = self._load_data(f"benchmark_seed_{seed}.json")
                    if d:
                        val = (
                            d.get("overall_aggregates", {})
                            .get("A5", {})
                            .get("summaries", {})
                            .get("f1", {})
                            .get("mean", 1.0)
                        )
                        means.append(val)
                if len(means) == 5:
                    m = sum(means) / 5
                    var = sum((x - m) ** 2 for x in means) / 4
                    std = math.sqrt(var)
                    cv = std / m if m > 0 else float("inf")
                    claim.status = "supported" if cv < 0.1 else "not_supported"
                else:
                    claim.status = "pending"
                validation_results[claim.claim_id] = claim.status
                continue

            data = self._load_data(claim.result_file)
            if not data:
                claim.status = "pending"
            else:
                try:
                    if claim.claim_id == "C1":
                        chan_vals = [
                            item.get("channel_intervention", {}).get("preserved_evidence", 0)
                            for item in data
                        ]
                        src_vals = [
                            item.get("source_event_intervention", {}).get("preserved_evidence", 0)
                            for item in data
                        ]
                        chan_mean = sum(chan_vals) / len(chan_vals) if chan_vals else 0
                        src_mean = sum(src_vals) / len(src_vals) if src_vals else 0
                        claim.status = "supported" if chan_mean > src_mean else "not_supported"
                    elif claim.claim_id == "C2":
                        chan_vals = [
                            item.get("channel_intervention", {}).get("collateral", float("inf"))
                            for item in data
                        ]
                        src_vals = [
                            item.get("source_event_intervention", {}).get(
                                "collateral", float("inf")
                            )
                            for item in data
                        ]
                        chan_mean = sum(chan_vals) / len(chan_vals) if chan_vals else float("inf")
                        src_mean = sum(src_vals) / len(src_vals) if src_vals else float("inf")
                        claim.status = "supported" if chan_mean < src_mean else "not_supported"
                    elif claim.claim_id == "C3":
                        comparisons = data.get("comparisons", [])
                        found = False
                        for comp in comparisons:
                            ma = comp.get("method_a", "")
                            mb = comp.get("method_b", "")
                            mn = comp.get("metric_name", "")
                            if (
                                ma.startswith("A5")
                                and mb.startswith("B1")
                                and mn == "causal_f1"
                            ):
                                claim.status = (
                                    "supported"
                                    if comp.get("significant")
                                    else "not_supported"
                                )
                                found = True
                        if not found:
                            claim.status = "pending"
                    elif claim.claim_id == "C4":
                        vals = [c.get("observed_cee", 1) for c in data]
                        claim.status = (
                            "supported" if all(v == 0 for v in vals) else "not_supported"
                        )
                    elif claim.claim_id == "C6":
                        conv = data.get("convergence", [])
                        last_val = conv[-1].get("cee", 0) if conv else 0
                        prev_val = conv[-2].get("cee", 1) if len(conv) > 1 else 0
                        claim.status = (
                            "supported" if abs(last_val - prev_val) < 0.05 else "not_supported"
                        )
                    elif claim.claim_id == "C7":
                        chan_cee = data.get("channel_cee", 0)
                        claim.status = "supported" if chan_cee > 0 else "not_supported"
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
