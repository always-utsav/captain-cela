"""CELA experimental validation -- Stage 17.

Multi-instance experiments, statistical analysis, reproducibility.

Re-exports::

    from captain.experiments import (
        # Statistics
        AggregateSummary,
        ComparisonResult,
        ConfidenceInterval,
        FailureAccount,
        SensitivityPoint,
        SensitivityResult,
        AblationStep,
        bootstrap_ci,
        compute_aggregate,
        compute_ablation_ladder,
        compute_sensitivity,
        holm_bonferroni,
        paired_comparison,
        # Runner
        ExperimentConfig,
        ExperimentResult,
        ExperimentRunner,
        FamilyAggregate,
        MethodAggregate,
        ReproducibilityMetadata,
    )
"""

from captain.experiments.runner import (
    ExperimentConfig,
    ExperimentResult,
    ExperimentRunner,
    FamilyAggregate,
    MethodAggregate,
    ReproducibilityMetadata,
)
from captain.experiments.statistics import (
    AblationStep,
    AggregateSummary,
    ComparisonResult,
    ConfidenceInterval,
    FailureAccount,
    SensitivityPoint,
    SensitivityResult,
    bootstrap_ci,
    compute_ablation_ladder,
    compute_aggregate,
    compute_sensitivity,
    holm_bonferroni,
    paired_comparison,
)

__all__ = [
    "AblationStep",
    "AggregateSummary",
    "ComparisonResult",
    "ConfidenceInterval",
    "ExperimentConfig",
    "ExperimentResult",
    "ExperimentRunner",
    "FailureAccount",
    "FamilyAggregate",
    "MethodAggregate",
    "ReproducibilityMetadata",
    "SensitivityPoint",
    "SensitivityResult",
    "bootstrap_ci",
    "compute_ablation_ladder",
    "compute_aggregate",
    "compute_sensitivity",
    "holm_bonferroni",
    "paired_comparison",
]
