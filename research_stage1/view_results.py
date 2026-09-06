import json
d = json.load(open("research_stage1/raw/benchmark_smoke.json"))
for r in d[:18]:
    if r["f1"] is not None:
        print(f'{r["family"]}/{r["method"]}: F1={r["f1"]:.3f} R@1={r["recall_at_1"]:.3f} P={r["precision"]:.3f}')
