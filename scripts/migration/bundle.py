"""Export the standalone Agent tools and contract, excluding experiments and run data."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def export(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output.is_relative_to(ROOT):
        raise ValueError("Export outside the Harness source directory")
    files = [ROOT / name for name in (
        "README.md", "README_en.md", "LICENSE", "pyproject.toml",
        "scripts/migrate.py", "scripts/harness.py",
    )]
    files += sorted((ROOT / "src").rglob("*.py"))
    files += sorted(p for p in (ROOT / "scripts/migration").iterdir()
                    if p.is_file() and (p.suffix == ".py" or "Dockerfile" in p.name))
    hashes = {}
    for source in files:
        relative = source.relative_to(ROOT)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"kind": "jittor-harness.agent-bundle", "files": hashes,
                "entry": "README.md", "cli": "scripts/harness.py"}
    (output / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.output), indent=2))
