"""Stage 2 figure generation from frozen research data.

Reads machine-readable JSON from research/raw/ and produces
paper-quality SVG and PNG figures in research/figures/.

All figures are generated from frozen data — no computation.
matplotlib is an optional visualization dependency, not core runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib  # type: ignore[import-untyped]

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # type: ignore[import-untyped]
import numpy as np  # type: ignore[import-untyped]


def _base() -> tuple[Path, Path]:
    base = Path(__file__).resolve().parent.parent.parent
    raw = base / "research" / "raw"
    fig = base / "research" / "figures"
    fig.mkdir(parents=True, exist_ok=True)
    return raw, fig


def _load(path: Path) -> Any:
    if path.exists():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(fig_dir: Path, name: str) -> None:
    plt.tight_layout()
    plt.savefig(fig_dir / f"{name}.svg", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {name}")


# ---------------------------------------------------------------
# Figure 1: Attribution across families
# ---------------------------------------------------------------
def fig_attribution(raw: Path, figs: Path) -> None:
    data = _load(raw / "benchmark_seed_42.json")
    fam_results = data.get("family_results", {})

    families: list[str] = []
    a5_f1: list[float] = []
    b1_f1: list[float] = []

    for fam in sorted(fam_results.keys()):
        families.append(fam)
        results = fam_results[fam].get("results", [])
        f1_a5 = f1_b1 = 0.0
        for mr in results:
            m = mr.get("metrics", {})
            if mr.get("method_name") == "A5":
                f1_a5 = max(f1_a5, m.get("f1", 0.0))
            elif mr.get("method_name") == "B1":
                f1_b1 = max(f1_b1, m.get("f1", 0.0))
        a5_f1.append(f1_a5)
        b1_f1.append(f1_b1)

    if not families:
        return

    x = np.arange(len(families))
    w = 0.35
    _fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - w / 2, a5_f1, w, label="CELA A5", color="#2196F3")
    ax.bar(x + w / 2, b1_f1, w, label="Random B1", color="#FF9800")
    ax.set_ylabel("F1 Score")
    ax.set_title("Attribution F1: CELA A5 vs Random Baseline B1")
    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=45, ha="right")
    ax.legend()
    ax.set_ylim(0, 1.1)
    _save(figs, "fig_attribution")


# ---------------------------------------------------------------
# Figure 2: Granularity (PRIMARY)
# ---------------------------------------------------------------
def fig_granularity(raw: Path, figs: Path) -> None:
    data = _load(raw / "granularity_experiment.json")
    if not isinstance(data, list) or not data:
        return

    # Average across instances
    ch_affected = np.mean([d["channel_intervention"]["affected_evidence"] for d in data])
    ch_preserved = np.mean([d["channel_intervention"]["preserved_evidence"] for d in data])
    ch_collateral = np.mean([d["channel_intervention"]["collateral"] for d in data])
    se_affected = np.mean([d["source_event_intervention"]["affected_evidence"] for d in data])
    se_preserved = np.mean([d["source_event_intervention"]["preserved_evidence"] for d in data])
    se_collateral = np.mean([d["source_event_intervention"]["collateral"] for d in data])

    labels = ["Affected\nEvidence", "Preserved\nEvidence", "Collateral\nModification"]
    ch_vals = [ch_affected, ch_preserved, ch_collateral]
    se_vals = [se_affected, se_preserved, se_collateral]

    x = np.arange(len(labels))
    w = 0.35
    _fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - w / 2, ch_vals, w, label="Channel Intervention", color="#4CAF50")
    bars2 = ax.bar(x + w / 2, se_vals, w, label="Source-Event Intervention", color="#F44336")

    # Value labels
    for bar in bars1:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 0.05, f"{h:.1f}",
            ha="center", va="bottom", fontsize=10,
        )
    for bar in bars2:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 0.05, f"{h:.1f}",
            ha="center", va="bottom", fontsize=10,
        )

    ax.set_ylabel("Count")
    ax.set_title(
        "Channel vs Source-Event Intervention"
        "\n(BF-G Shared-Source, averaged across 5 seeds)"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    _save(figs, "fig_granularity")


# ---------------------------------------------------------------
# Figure 3: Collateral modification
# ---------------------------------------------------------------
def fig_collateral(raw: Path, figs: Path) -> None:
    data = _load(raw / "granularity_experiment.json")
    if not isinstance(data, list) or not data:
        return

    ch_rate = np.mean([d["granularity_metrics"]["channel_collateral_rate"] for d in data])
    se_rate = np.mean([d["granularity_metrics"]["source_event_collateral_rate"] for d in data])

    _fig, ax = plt.subplots(figsize=(6, 6))
    bars = ax.bar(
        ["Channel\nIntervention", "Source-Event\nIntervention"],
        [ch_rate, se_rate],
        color=["#4CAF50", "#F44336"],
    )
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 0.02, f"{h:.2f}",
            ha="center", va="bottom", fontsize=12,
        )

    ax.set_ylabel("Collateral Modification Rate")
    ax.set_title("Collateral Modification Rate Comparison")
    ax.set_ylim(0, max(ch_rate, se_rate) * 1.5 + 0.1)
    _save(figs, "fig_collateral")


# ---------------------------------------------------------------
# Figure 4: Replay convergence
# ---------------------------------------------------------------
def fig_convergence(raw: Path, figs: Path) -> None:
    data = _load(raw / "replay_convergence.json")
    rows = data.get("convergence", [])
    if not rows:
        return

    replays = [r["replay_count"] for r in rows]
    cees = [r["cee"] for r in rows]
    ci_lo = [r.get("ci_lower", r["cee"]) for r in rows]
    ci_hi = [r.get("ci_upper", r["cee"]) for r in rows]

    _fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(replays, cees, "o-", color="#2196F3", linewidth=2, markersize=8, label="CEE")
    ax.fill_between(replays, ci_lo, ci_hi, alpha=0.2, color="#2196F3")
    ax.set_xlabel("Replay Count")
    ax.set_ylabel("CEE Estimate")
    ax.set_title(
        "Replay Convergence: CEE vs Replays"
        "\n(Deterministic MockLLM)"
    )
    ax.legend()
    ax.set_xscale("log")
    _save(figs, "fig_convergence")


# ---------------------------------------------------------------
# Figure 5: Scalability
# ---------------------------------------------------------------
def fig_scalability(raw: Path, figs: Path) -> None:
    data = _load(raw / "scalability.json")
    rows = data.get("scalability", [])
    if not rows:
        return

    families = [r["family"] for r in rows]
    runtimes = [r["runtime_s"] for r in rows]

    _fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(families, runtimes, color="#9C27B0")
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("Scalability: Runtime per Benchmark Family")
    _save(figs, "fig_scalability")


# ---------------------------------------------------------------
# Figure 6: Negative controls
# ---------------------------------------------------------------
def fig_negative_controls(raw: Path, figs: Path) -> None:
    data = _load(raw / "negative_controls.json")
    if not isinstance(data, list) or not data:
        return

    labels = [f"{d['family']}\n{d['control_type']}" for d in data]
    cees = [d["observed_cee"] for d in data]
    colors = ["#4CAF50" if d["passed"] else "#F44336" for d in data]

    _fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, cees, color=colors)
    ax.set_ylabel("Observed CEE")
    ax.set_title("Negative Controls: Observed CEE\n(Green = passed, expected CEE = 0)")
    ax.axhline(y=0, color="white", linewidth=0.5, linestyle="--")
    _save(figs, "fig_negative_controls")


# ---------------------------------------------------------------
# Figure 7: Real-LLM validation
# ---------------------------------------------------------------
def fig_real_llm(raw: Path, figs: Path) -> None:
    data = _load(raw / "real_llm_validation.json")
    if not data:
        return

    conditions = ["Factual", "Channel\nIntervention", "Source-Event\nIntervention"]
    rates = [
        data.get("factual_failure_rate", 0),
        data.get("channel_failure_rate", 0),
        data.get("source_event_failure_rate", 0),
    ]
    colors = ["#F44336", "#4CAF50", "#FF9800"]

    _fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(conditions, rates, color=colors)
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 0.01, f"{h:.2f}",
            ha="center", va="bottom", fontsize=12,
        )

    model = data.get("model_version", data.get("model", "unknown"))
    ax.set_ylabel("Failure Keyword Rate")
    ax.set_title(f"Real-LLM Validation: {model}\nFailure Keyword Presence by Condition")
    ax.set_ylim(0, max(rates) * 1.5 + 0.1)
    _save(figs, "fig_real_llm")


# ---------------------------------------------------------------
# Figure 8: Seed robustness
# ---------------------------------------------------------------
def fig_seed_robustness(raw: Path, figs: Path) -> None:
    seeds = [42, 123, 456, 789, 1024]
    f1_vals: list[float] = []

    for s in seeds:
        data = _load(raw / f"benchmark_seed_{s}.json")
        agg = data.get("overall_aggregates", {}).get("A5", {})
        sums = agg.get("summaries", {}).get("f1", {})
        val = sums.get("mean", 0.0)
        f1_vals.append(val)

    if not any(v > 0 for v in f1_vals):
        return

    mean_f1 = float(np.mean(f1_vals))
    std_f1 = float(np.std(f1_vals))

    _fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar([str(s) for s in seeds], f1_vals, color="#2196F3", alpha=0.7)
    ax.axhline(
        y=mean_f1, color="#F44336", linewidth=2,
        linestyle="--", label=f"Mean={mean_f1:.3f}",
    )
    ax.fill_between(
        range(len(seeds)),
        [mean_f1 - std_f1] * len(seeds),
        [mean_f1 + std_f1] * len(seeds),
        alpha=0.15,
        color="#F44336",
    )
    ax.set_xlabel("Seed")
    ax.set_ylabel("F1 Score")
    ax.set_title(
        f"Seed Robustness: A5 F1 across 5 Seeds"
        f"\n(mean={mean_f1:.3f}, std={std_f1:.3f})"
    )
    ax.legend()
    _save(figs, "fig_seed_robustness")


def main() -> None:
    raw, figs = _base()
    print("Generating figures from frozen data...")
    fig_attribution(raw, figs)
    fig_granularity(raw, figs)
    fig_collateral(raw, figs)
    fig_convergence(raw, figs)
    fig_scalability(raw, figs)
    fig_negative_controls(raw, figs)
    fig_real_llm(raw, figs)
    fig_seed_robustness(raw, figs)
    print("Done.")


if __name__ == "__main__":
    main()
