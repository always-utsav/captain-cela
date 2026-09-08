# 18: Reproducibility

Full reproduction instructions for the evaluation campaign:

- **Software Commit**: `98e6366c6e47`
- **Seeds Used**: `42`, `123`, `456`, `789`, `1024`
- **Python Version**: >= 3.10
- **Configuration**: Managed via `config` block in `experiment_manifest.json`
- **Execution**: Run the benchmark suite via the core evaluation pipeline targeting the specified git commit. Dependencies are locked via the project's requirements manifesto.
