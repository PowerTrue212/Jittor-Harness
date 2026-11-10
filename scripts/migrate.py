"""Ordinary Docker/local migration entry; no experiment plan or Agent launcher required."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Bind checked-out source without importing the experiment controller.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_source = Path(__file__).resolve().parents[1] / "src"
_spec = importlib.util.spec_from_file_location(
    "jittor_harness", _source / "__init__.py", submodule_search_locations=[str(_source)]
)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
sys.modules["jittor_harness"] = _module
_spec.loader.exec_module(_module)

from jittor_harness.contracts import load_task  # noqa: E402
from jittor_harness.delivery import finalize_candidate  # noqa: E402
from jittor_harness.verification import verify  # noqa: E402
from scripts.migration.preparation import baseline, check  # noqa: E402
from scripts.migration.workspace import initialize, read, write  # noqa: E402


def finalize(root: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"交付目录已存在：{output}")
    readiness = check(root)
    task = load_task(root / "task.json")
    snapshot = finalize_candidate(root / "candidate", output,
                                  required_entry=task["target"]["entry"])
    prepared = read(root / "prepared.json")
    write(output / "preparation.json", prepared)
    write(output / "provenance.json", read(root / "migration.json"))
    recipes = output / "environment"
    recipes.mkdir()
    for number, path in enumerate(prepared["scope"]["environment_hashes"]):
        shutil.copy2(path, recipes / f"{number}-{Path(path).name}")
    # Preserve relative material paths by normalizing before writing the delivery task.
    task["target"]["repo"] = snapshot["snapshot"]
    write(output / "task.json", task)
    report = verify(load_task(output / "task.json"), output / "evidence", trial="delivery")
    result = {"candidate": snapshot, "preparation": readiness,
              "scope": prepared["scope"],
              "verify": report, "passed": bool(report.get("passed")),
              "claim": "仅对冻结任务与已列覆盖范围给出验证结果；非隐藏认证"}
    write(output / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="从 URL 或人工提供的本地目录创建独立工作区")
    init.add_argument("workspace", type=Path)
    init.add_argument("--source", required=True)
    init.add_argument("--revision")
    for name in ("baseline", "check", "finalize"):
        command = commands.add_parser(name)
        command.add_argument("workspace", type=Path)
        if name == "finalize":
            command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    root = args.workspace.expanduser().resolve()
    try:
        if args.command == "init":
            result = initialize(root, args.source, args.revision)
        elif args.command == "baseline":
            result = baseline(root)
        elif args.command == "check":
            result = check(root)
        else:
            result = finalize(root, args.output.expanduser().resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result.get("passed") is False else 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
