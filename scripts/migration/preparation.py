"""Freeze preparation evidence; never infer semantic correctness from readiness."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from jittor_harness.contracts import digest, file_hash, load_task
from jittor_harness.delivery import repository_manifest
from jittor_harness.runtime import build_env
from jittor_harness.verification import run_side

from .workspace import read, write


def resolve(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def inputs(root: Path) -> tuple[dict, dict]:
    task = load_task(root / "task.json")
    scope = read(root / "scope.json")
    for field in ("purpose", "preprocessing", "outputs", "state_and_mode", "acceptance_basis"):
        if not isinstance(scope.get(field), str) or not scope[field].strip():
            raise ValueError(f"scope.{field} 必须说明具体任务语义")
    entries = scope.get("public_entries")
    if (not isinstance(entries, list) or not entries
            or any(not isinstance(v, str) or not v.strip() for v in entries)
            or not isinstance(scope.get("limitations"), list)):
        raise ValueError("scope 需要 public_entries 和 limitations 列表")
    if not isinstance(scope.get("assets"), list) or not scope.get("environment_files"):
        raise ValueError("scope 需要 assets 列表及非空 environment_files 环境配方/锁文件列表")
    for item in scope["assets"]:
        path = resolve(root, item["path"])
        if not item.get("origin") or file_hash(path) != item.get("sha256"):
            raise ValueError(f"材料缺少来源或 SHA256 不匹配：{path}")
    scope = {**scope, "environment_hashes": {
        str(resolve(root, name)): file_hash(resolve(root, name))
        for name in scope["environment_files"]
    }}
    expected = read(root / "migration.json")["baseline_digest"]
    actual = repository_manifest(root / "baseline/repository")["content_digest"]
    if expected != actual or Path(task["source"]["repo"]) != root / "baseline/repository":
        raise ValueError("源端基线已改变；请从原始材料建立新 workspace")
    if Path(task["target"]["repo"]) != root / "candidate":
        raise ValueError("target.repo 必须指向当前 workspace/candidate")
    for side in ("source", "target"):
        config = task[side]
        entry = (Path(config["repo"]) / config["entry"]).resolve()
        if not entry.is_relative_to(Path(config["repo"])) or not entry.is_file():
            raise ValueError(f"{side} 入口不存在或越出仓库：{entry}")
        if not config["python"]:
            raise ValueError(f"{side}.python 必须显式设置")
    return task, scope


def environment(task: dict) -> dict:
    """Run probes in the same interpreters and environment used by capture."""
    doctor = Path(__file__).resolve().parents[2] / "src/doctor.py"
    result = {}
    for side in ("source", "target"):
        config = task[side]
        framework = "torch" if side == "source" else "jittor"
        # Cold Jittor imports compile native code. Use the task's execution
        # budget instead of doctor's short interactive import timeout.
        code = (
            "import runpy,json,importlib; m=runpy.run_path(" + repr(str(doctor)) + "); "
            "r=m['build_doctor_report'](); f=" + repr(framework) + "; "
            "v=importlib.import_module(f); "
            "r['runtime']={f:{'ok':True,'stdout':str(v.__version__)}}; "
            "print('HARNESS_PROBE='+json.dumps(r))"
        )
        env = build_env(config, Path(config["repo"]).parent / "probe-cache" / side)
        completed = subprocess.run(
            [config["python"], "-c", code], cwd=config["repo"], env=env,
            text=True, capture_output=True,
            timeout=max(240, int(task["protocol"]["timeout"])), check=False,
        )
        if completed.returncode:
            raise ValueError(f"{side} 框架导入失败：{completed.stderr[-4000:]}")
        lines = completed.stdout.splitlines()
        payloads = [line.removeprefix("HARNESS_PROBE=")
                    for line in lines if line.startswith("HARNESS_PROBE=")]
        if len(payloads) != 1:
            raise ValueError(f"{side} 框架探针未返回唯一环境报告")
        probe = json.loads(payloads[0])
        probe["runtime"][framework]["stderr"] = completed.stderr[-8000:]
        packages = subprocess.run(
            [config["python"], "-m", "pip", "list", "--format=json"], env=env,
            text=True, capture_output=True, timeout=120, check=True,
        )
        result[side] = {"probe": probe, "packages": json.loads(packages.stdout)}
    return result


def identity(task: dict, scope: dict, env: dict) -> str:
    # Target code evolves during migration. Its environment and call contract do not.
    stable_env = {}
    for side, record in env.items():
        if "probe" not in record:
            stable_env[side] = record
            continue
        probe = record["probe"]
        # Import logs contain timestamps and cache compilation progress. Keep raw
        # logs in preparation evidence, but do not treat them as environment identity.
        stable_env[side] = {**record, "probe": {
            **probe, "runtime": {
                name: {"ok": run["ok"],
                       "version": run.get("stdout", "").strip().split("\n")[-1]
                       if run["ok"] else None}
                for name, run in probe["runtime"].items()
            }
        }}
    return digest({"oracle": task["digest"], "protocol": task["protocol"], "target": {
        k: v for k, v in task["target"].items() if k != "repo"
    }, "scope": scope, "environment": stable_env})


def baseline(root: Path) -> dict:
    if (root / "prepared.json").exists():
        raise FileExistsError("基线已冻结；修改任务或环境需要新 workspace")
    task, scope = inputs(root)
    env = environment(task)
    report = run_side(task, "source", root / "evidence", trial="source-baseline")
    if not report.get("ok"):
        raise RuntimeError(f"源端基线执行失败：{report}")
    result = {"identity": identity(task, scope, env), "environment": env,
              "scope": scope, "source_run": report,
              "claim": "源端可运行；任务语义与覆盖范围仍须独立核对"}
    write(root / "prepared.json", result)
    return result


def check(root: Path) -> dict:
    task, scope = inputs(root)
    env = environment(task)
    prepared = read(root / "prepared.json")
    if prepared["identity"] != identity(task, scope, env):
        raise ValueError("任务、源端、材料或双端环境已变化；不能复用旧基线")
    return {"ready": True, "identity": prepared["identity"],
            "claim": "准备证据一致；不代表候选通过或任务覆盖充分"}
