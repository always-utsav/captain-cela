"""Generate evidence package: checksums, manifest, and metadata for all raw result files."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256sum(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    raw_dir = Path("research/raw")
    evidence_dir = Path("research/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(raw_dir.glob("*.json"))
    checksums: dict[str, dict[str, str | int]] = {}

    for f in files:
        checksums[f.name] = {
            "sha256": sha256sum(f),
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }

    # Also checksum figures
    fig_dir = Path("research/figures")
    for f in sorted(fig_dir.glob("*")):
        key = f"figures/{f.name}"
        checksums[key] = {
            "sha256": sha256sum(f),
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }

    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "v1_tag": "CAPTAIN-CELA-RESEARCH-FREEZE-V1",
        "v1_commit": "27ed11a",
        "stage2_commit": "d5b4a2462f5ad95e9f132006a8fd870dc098ebe3",
        "total_files": len(checksums),
        "files": checksums,
    }

    out = evidence_dir / "evidence_checksums.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Evidence checksums written to {out}")
    print(f"  {len(checksums)} files checksummed")


if __name__ == "__main__":
    main()
