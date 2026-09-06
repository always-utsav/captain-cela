"""CELA experiment statistics -- Stage 17.

Statistical utilities for experimental validation:
- Aggregate metric summaries across scenario instances
- Bootstrap confidence intervals
- Paired statistical comparisons
- Multiple-comparison correction (Holm-Bonferroni)
- Effect sizes
- Sensitivity analysis summaries

All implementations use stdlib only (no numpy/scipy).

The scenario instance is the independent experimental unit.
Repeated replays within one scenario are NOT independent samples.
"""

from __future__ import annotations

import math
import random

from pydantic import BaseModel, Field

# ===================================================================
# Aggregate summary
# ===================================================================


class AggregateSummary(BaseModel):
    """Aggregate statistics for a metric across scenario instances."""

    metric_name: str
    values: list[float] = Field(default_factory=list)
    n: int = 0
    mean: float = 0.0
    std: float = 0.0
    median: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0


def compute_aggregate(metric_name: str, values: list[float]) -> AggregateSummary:
    """Compute aggregate statistics from a list of values."""
    n = len(values)
    if n == 0:
        return AggregateSummary(metric_name=metric_name)

    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
    std = math.sqrt(var)
    sorted_v = sorted(values)
    median = sorted_v[n // 2] if n % 2 == 1 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2

    return AggregateSummary(
        metric_name=metric_name,
        values=values,
        n=n,
        mean=mean,
        std=std,
        median=median,
        min_val=sorted_v[0],
        max_val=sorted_v[-1],
    )


# ===================================================================
# Bootstrap confidence interval
# ===================================================================


class ConfidenceInterval(BaseModel):
    """Bootstrap confidence interval for a metric."""

    metric_name: str
    point_estimate: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    confidence_level: float = 0.95
    n_bootstrap: int = 0
    n_samples: int = 0
    sufficient: bool = True


def bootstrap_ci(
    metric_name: str,
    values: list[float],
    *,
    confidence_level: float = 0.95,
    n_bootstrap: int = 2000,
    seed: int = 42,
    min_samples: int = 3,
) -> ConfidenceInterval:
    """Compute bootstrap percentile confidence interval.

    Uses deterministic seed for reproducibility.
    Returns insufficient status if n < min_samples.
    """
    n = len(values)
    if n < min_samples:
        point = sum(values) / max(n, 1) if values else 0.0
        return ConfidenceInterval(
            metric_name=metric_name,
            point_estimate=point,
            ci_lower=point,
            ci_upper=point,
            confidence_level=confidence_level,
            n_bootstrap=0,
            n_samples=n,
            sufficient=False,
        )

    rng = random.Random(seed)  # noqa: S311
    point = sum(values) / n

    # Bootstrap resampling
    bootstrap_means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(values) for _ in range(n)]
        bootstrap_means.append(sum(sample) / n)

    bootstrap_means.sort()
    alpha = 1 - confidence_level
    lo_idx = max(0, math.floor(alpha / 2 * n_bootstrap))
    hi_idx = min(n_bootstrap - 1, math.ceil((1 - alpha / 2) * n_bootstrap) - 1)

    return ConfidenceInterval(
        metric_name=metric_name,
        point_estimate=point,
        ci_lower=bootstrap_means[lo_idx],
        ci_upper=bootstrap_means[hi_idx],
        confidence_level=confidence_level,
        n_bootstrap=n_bootstrap,
        n_samples=n,
        sufficient=True,
    )


# ===================================================================
# Paired statistical comparison
# ===================================================================


class ComparisonResult(BaseModel):
    """Result of a paired statistical comparison between two methods."""

    method_a: str
    method_b: str
    metric_name: str
    test_name: str
    n_pairs: int = 0
    mean_diff: float = 0.0
    p_value: float = 1.0
    adjusted_p_value: float = 1.0
    correction_method: str = ""
    effect_size: float | None = None
    effect_size_name: str = ""
    significant: bool = False
    alpha: float = 0.05
    sufficient: bool = True


def _wilcoxon_signed_rank(diffs: list[float]) -> float:
    """Wilcoxon signed-rank test p-value (two-sided).

    Stdlib implementation for small samples.
    Returns approximate p-value using normal approximation.
    For very small n (<10), returns conservative p=1.0.
    """
    # Remove zeros
    nonzero = [(abs(d), 1 if d > 0 else -1) for d in diffs if d != 0.0]
    n = len(nonzero)

    if n < 6:
        return 1.0

    # Rank by absolute value
    ranked = sorted(nonzero, key=lambda x: x[0])

    # Handle ties by averaging ranks
    ranks: list[tuple[float, int]] = []
    i = 0
    while i < n:
        j = i
        while j < n and ranked[j][0] == ranked[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks.append((avg_rank, ranked[k][1]))
        i = j

    # Compute W+
    w_plus = sum(r for r, s in ranks if s > 0)

    # Normal approximation
    mean_w = n * (n + 1) / 4
    var_w = n * (n + 1) * (2 * n + 1) / 24
    if var_w == 0:
        return 1.0

    z = (w_plus - mean_w) / math.sqrt(var_w)

    # Two-sided p-value from standard normal (approximation)
    p = 2 * _standard_normal_cdf(-abs(z))
    return min(p, 1.0)


def _permutation_test(diffs: list[float], *, n_perms: int = 5000, seed: int = 42) -> float:
    """Paired permutation test p-value (two-sided).

    Tests whether the mean difference is significantly different from zero.
    """
    n = len(diffs)
    if n < 3:
        return 1.0

    observed = abs(sum(diffs) / n)
    rng = random.Random(seed)  # noqa: S311

    count_extreme = 0
    for _ in range(n_perms):
        perm = [d * rng.choice([-1, 1]) for d in diffs]
        perm_mean = abs(sum(perm) / n)
        if perm_mean >= observed:
            count_extreme += 1

    return count_extreme / n_perms


def _standard_normal_cdf(z: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def paired_comparison(
    method_a: str,
    method_b: str,
    metric_name: str,
    values_a: list[float],
    values_b: list[float],
    *,
    test: str = "auto",
    alpha: float = 0.05,
    min_pairs: int = 3,
    seed: int = 42,
) -> ComparisonResult:
    """Paired comparison between two methods on the same scenario instances.

    test: "auto" (picks based on metric), "wilcoxon", "permutation"
    """
    n = min(len(values_a), len(values_b))
    if n < min_pairs:
        return ComparisonResult(
            method_a=method_a,
            method_b=method_b,
            metric_name=metric_name,
            test_name="none",
            n_pairs=n,
            sufficient=False,
        )

    diffs = [values_a[i] - values_b[i] for i in range(n)]
    mean_diff = sum(diffs) / n

    # Select test
    if test == "auto":
        # Use permutation for binary/bounded metrics, wilcoxon for continuous
        unique_vals = set(values_a) | set(values_b)
        test_name = "permutation" if len(unique_vals) <= 3 else "wilcoxon"
    else:
        test_name = test

    if test_name == "wilcoxon":
        p_val = _wilcoxon_signed_rank(diffs)
    else:
        p_val = _permutation_test(diffs, seed=seed)

    # Effect size: paired Cohen's d
    effect = _paired_effect_size(diffs)
    effect_name = "paired_cohens_d" if effect is not None else ""

    return ComparisonResult(
        method_a=method_a,
        method_b=method_b,
        metric_name=metric_name,
        test_name=test_name,
        n_pairs=n,
        mean_diff=mean_diff,
        p_value=p_val,
        adjusted_p_value=p_val,  # Will be corrected later
        effect_size=effect,
        effect_size_name=effect_name,
        significant=p_val < alpha,
        alpha=alpha,
        sufficient=True,
    )


def _paired_effect_size(diffs: list[float]) -> float | None:
    """Paired Cohen's d = mean(diffs) / std(diffs)."""
    n = len(diffs)
    if n < 2:
        return None

    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    std_d = math.sqrt(var_d)

    if std_d == 0:
        return 0.0 if mean_d == 0 else float("inf") if mean_d > 0 else float("-inf")

    return mean_d / std_d


# ===================================================================
# Multiple comparison correction
# ===================================================================


def holm_bonferroni(
    results: list[ComparisonResult],
    *,
    alpha: float = 0.05,
) -> list[ComparisonResult]:
    """Apply Holm-Bonferroni correction to multiple comparison results.

    Returns new ComparisonResult objects with adjusted p-values.
    """
    if not results:
        return []

    # Sort by raw p-value
    indexed = list(enumerate(results))
    indexed.sort(key=lambda x: x[1].p_value)

    m = len(results)
    corrected: list[tuple[int, ComparisonResult]] = []

    for rank, (orig_idx, res) in enumerate(indexed):
        adjusted_p = min(res.p_value * (m - rank), 1.0)
        # Enforce monotonicity: adjusted p must be >= previous
        if corrected:
            prev_p = corrected[-1][1].adjusted_p_value
            adjusted_p = max(adjusted_p, prev_p)

        new_res = res.model_copy(
            update={
                "adjusted_p_value": adjusted_p,
                "correction_method": "holm_bonferroni",
                "significant": adjusted_p < alpha,
                "alpha": alpha,
            }
        )
        corrected.append((orig_idx, new_res))

    # Restore original order
    corrected.sort(key=lambda x: x[0])
    return [r for _, r in corrected]


# ===================================================================
# Sensitivity analysis
# ===================================================================


class SensitivityPoint(BaseModel):
    """One point in a sensitivity analysis."""

    parameter_name: str
    parameter_value: float | int | str
    metric_name: str
    metric_value: float = 0.0
    n_instances: int = 0


class SensitivityResult(BaseModel):
    """Sensitivity analysis for one parameter-metric combination."""

    parameter_name: str
    metric_name: str
    method_name: str
    points: list[SensitivityPoint] = Field(default_factory=list)
    is_stable: bool = True
    variation_coefficient: float = 0.0


def compute_sensitivity(
    parameter_name: str,
    metric_name: str,
    method_name: str,
    points: list[SensitivityPoint],
    *,
    stability_threshold: float = 0.2,
) -> SensitivityResult:
    """Assess metric stability across parameter values.

    stability_threshold: coefficient of variation threshold below which
    the metric is considered stable.
    """
    if not points:
        return SensitivityResult(
            parameter_name=parameter_name,
            metric_name=metric_name,
            method_name=method_name,
        )

    values = [p.metric_value for p in points]
    mean = sum(values) / len(values)
    if len(values) < 2:
        return SensitivityResult(
            parameter_name=parameter_name,
            metric_name=metric_name,
            method_name=method_name,
            points=points,
            is_stable=True,
            variation_coefficient=0.0,
        )

    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    std = math.sqrt(var)
    cv = std / abs(mean) if abs(mean) > 1e-10 else 0.0

    return SensitivityResult(
        parameter_name=parameter_name,
        metric_name=metric_name,
        method_name=method_name,
        points=points,
        is_stable=cv < stability_threshold,
        variation_coefficient=cv,
    )


# ===================================================================
# Ablation summary
# ===================================================================


class AblationStep(BaseModel):
    """Comparison between adjacent CELA levels."""

    from_config: str
    to_config: str
    metric_name: str
    from_value: float = 0.0
    to_value: float = 0.0
    delta: float = 0.0
    comparison: ComparisonResult | None = None


def compute_ablation_ladder(
    metric_name: str,
    level_values: dict[str, list[float]],
    *,
    alpha: float = 0.05,
    seed: int = 42,
) -> list[AblationStep]:
    """Compute ablation analysis across A1-A5 ladder.

    level_values: {"A1_cela": [...], "A2_cela": [...], ...}
    """
    levels = ["A1_cela", "A2_cela", "A3_cela", "A4_cela", "A5_cela"]
    available = [lv for lv in levels if level_values.get(lv)]
    steps: list[AblationStep] = []

    for i in range(len(available) - 1):
        from_cfg = available[i]
        to_cfg = available[i + 1]
        va = level_values[from_cfg]
        vb = level_values[to_cfg]

        mean_a = sum(va) / len(va) if va else 0.0
        mean_b = sum(vb) / len(vb) if vb else 0.0

        comp = None
        if len(va) >= 3 and len(vb) >= 3 and len(va) == len(vb):
            comp = paired_comparison(from_cfg, to_cfg, metric_name, va, vb, alpha=alpha, seed=seed)

        steps.append(
            AblationStep(
                from_config=from_cfg,
                to_config=to_cfg,
                metric_name=metric_name,
                from_value=mean_a,
                to_value=mean_b,
                delta=mean_b - mean_a,
                comparison=comp,
            )
        )

    return steps


# ===================================================================
# Failure accounting
# ===================================================================


class FailureAccount(BaseModel):
    """Failure classification for experiment outcomes."""

    total_evaluations: int = 0
    successful: int = 0
    replay_failure: int = 0
    unsupported_intervention: int = 0
    evaluator_failure: int = 0
    insufficient_candidates: int = 0
    invalid_scenario: int = 0
    budget_exhausted: int = 0
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
