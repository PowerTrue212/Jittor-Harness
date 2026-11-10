"""Materialize repositories using the existing repository delivery implementation."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from jittor_harness.delivery import finalize_candidate, initialize_git_workspace


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8", timeout=180
    ).strip()


def initialize(root: Path, source: str, revision: str | None) -> dict:
    if root.exists():
        raise FileExistsError(f"工作目录已存在，请使用新目录：{root}")
    local = Path(source).expanduser()
    if local.exists() and revision:
        raise ValueError("本地目录按当前内容接收；请先自行 checkout，不能指定 --revision")
    if local.exists() and (root == local.resolve() or local.resolve() in root.parents):
        raise ValueError("工作目录必须在输入源码之外")
    root.mkdir(parents=True)
    origin = local.resolve() if local.exists() else root / "download"
    if not local.exists():
        subprocess.run(["git", "clone", "--", source, str(origin)], check=True, timeout=600)
    if revision:
        git(origin, "checkout", "--detach", revision)
    provenance = {"input": source, "revision": None, "git_status": None}
    if (origin / ".git").exists():
        provenance.update(revision=git(origin, "rev-parse", "HEAD"),
                          git_status=git(origin, "status", "--porcelain"))
    frozen = finalize_candidate(origin, root / "baseline")
    shutil.copytree(frozen["snapshot"], root / "candidate", symlinks=True)
    initialize_git_workspace(root / "candidate")
    write(root / "migration.json", {"schema_version": 1, "source": provenance,
                                    "baseline_digest": frozen["content_digest"]})
    # Deliberately incomplete: the Agent must identify the real constructor and inputs.
    write(root / "task.json", {
        "schema_version": 1, "task_id": root.name, "seed": 7, "inputs": [],
        "source": {"repo": "baseline/repository", "entry": "", "model": "",
                   "python": "/opt/source/bin/python", "device": "cpu"},
        "target": {"repo": "candidate", "entry": "", "model": "",
                   "python": "/opt/target/bin/python", "device": "cpu"},
        "protocol": {"repeats": 3, "timeout": 600},
    })
    write(root / "scope.json", {
        "purpose": "", "public_entries": [], "preprocessing": "", "outputs": "",
        "state_and_mode": "", "acceptance_basis": "", "limitations": [],
        "assets": [], "environment_files": [],
    })
    return {"workspace": str(root), "next": "填写 task.json、scope.json 并准备双端环境"}
