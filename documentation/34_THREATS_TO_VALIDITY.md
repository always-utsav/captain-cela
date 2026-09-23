# 34: Threats to Validity

## Internal Validity
- **Deterministic Mocks**: The reliance on MockLLM for the benchmark campaign ensures reproducibility but artificially inflates the stability of counterfactual replay. It guarantees CEE=1.0 for true causes, masking the volatility inherent in real stochastic models.
- **Confounding Variables**: In BF-G (Granularity), the tool outputs are perfectly cleanly separable. In practice, tool outputs may be entangled, meaning channel-level intervention might inadvertently act as a source-event intervention.

## External Validity
- **Generalization to Real LLMs**: The primary results are derived from a synthetic agent framework. The Real-LLM validation is a narrow sanity check and does not guarantee that CELA will scale to complex, real-world tasks involving state-of-the-art models with diverse prompt structures.
- **Applicability to Unseen Topologies**: The 11 benchmark families cover a wide range of structures, but real-world failure trajectories may exhibit dynamic or recursive topologies not captured in this suite.

## Construct Validity
- **Benchmark Conceptual Mismatches**: As documented, some benchmarks evaluate slightly different constructs than initially named (e.g., BF-H testing convergence rather than branching; BF-J testing parallel sources rather than circularity). This threatens the claim that CELA resolves specific theoretical graph structures like cycles.
- **Intervention Definition**: The distinction between `ARTIFACT_REPLACEMENT` and `TOOL_RESULT_OVERRIDE` cleanly maps to channel vs. event in our framework, but this definition may not map perfectly to other agent architectures.

## Statistical Validity
- **Sample Size**: While 275 instances is sufficient for non-parametric tests, the reliance on permutation and Wilcoxon tests limits the statistical power compared to parametric alternatives, though it ensures fewer distributional assumptions.
- **Multiple Comparisons**: The use of Holm-Bonferroni correction is appropriate, but the lack of statistical significance in the A5 vs B1 comparison (p=0.1156) highlights that the effect size might be smaller than anticipated, or the variance higher, demanding either more instances or a more sensitive metric.
