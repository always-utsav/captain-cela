# Claim Evidence Matrix

This matrix classifies each claim by its fundamental type: STRUCTURAL, INTERVENTIONAL, CAUSAL, QUANTITATIVE, DESCRIPTIVE, COMPARATIVE.

| Claim ID | Statement | Classification | Status |
|---|---|---|---|
| **C1** | Channel intervention provides more selective localization than source-event intervention | INTERVENTIONAL / QUANTITATIVE | Supported |
| **C2** | Channel intervention preserves unrelated evidence | INTERVENTIONAL / QUANTITATIVE | Supported |
| **C3** | CELA A5 achieves higher F1 than random baseline B1 | COMPARATIVE | NOT SUPPORTED |
| **C4** | Negative controls show CEE=0 for irrelevant channels | INTERVENTIONAL / QUANTITATIVE | Supported |
| **C5** | Results are stable across seeds | DESCRIPTIVE / QUANTITATIVE | Supported |
| **C6** | CEE converges with replay count | DESCRIPTIVE | Supported (trivially true) |
| **C7** | Real-LLM intervention produces non-zero CEE | INTERVENTIONAL / QUANTITATIVE | Supported (sanity check) |
