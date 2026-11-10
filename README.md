# Jittor Harness

[English](README_en.md)

Jittor Harness 为 PyTorch → Jittor 代码迁移提供可复现执行、验证和诊断。
代码 Agent 负责理解源仓库、准备环境与修改代码；Harness 按明确的任务契约运行两端，
比较输出或训练更新，并保存可检查的证据。

**可以在本机、虚拟环境、远端服务器或容器中使用。Docker 是可选的隔离方式。**
需要提供源仓库、双端框架环境，以及任务所需的输入、权重和验收范围。
源仓库可以由 Agent 获取，也可以由使用者提前下载后提供。

## 安装与运行环境

以下命令从本仓库根目录执行。示例采用 Linux/WSL Shell；所有目录均可按实际部署修改。
控制端需要 Python 3.10 或以上，负责读取任务、启动子进程和汇总证据：

```bash
python3 -m venv .venvs/control
source .venvs/control/bin/activate
python -m pip install .
python scripts/harness.py --help
python scripts/migrate.py --help
```

安装后也可用 `python -m jittor_harness` 或 `jittor-harness` 调用核心 CLI。
`scripts/harness.py` 直接使用当前目录的源码，便于 Agent 获取工具后立即调用。
仅安装 wheel 可使用核心 CLI；迁移准备脚本和示例需要保留本仓库目录。
Windows 控制端可使用 `py -3 -m venv .venvs/control` 创建环境，再直接运行
`.venvs/control/Scripts/python.exe`；模型执行环境另按所选框架的要求配置。
目前已做的真实双端 smoke 验证使用 Linux 容器；这不代表所有操作系统或 GPU 配置均已验证。

PyTorch 与 Jittor 可以放在两个独立环境中：

```bash
python3 -m venv .venvs/source
python3 -m venv .venvs/target
.venvs/source/bin/python -m pip install 'numpy>=1.24,<2' 'PyYAML>=6.0'
.venvs/target/bin/python -m pip install 'numpy>=1.24,<2' 'PyYAML>=6.0'
```

随后按目标仓库和硬件安装匹配的 PyTorch、Jittor 及模型依赖，运行真实模型探针。
本工具不替使用者选择框架/CUDA 版本，也不预装模型、权重或数据。
在 `task.json` 中填写两个解释器的**实际绝对路径**，例如各虚拟环境的 `bin/python`，
并显式设置 `device: cpu` 或 `cuda`。双端环境需要 NumPy/PyYAML，执行器从工具源码启动采集，
无需分别安装 Harness 包。

记录可重复执行的安装步骤、框架版本、系统编译工具和两端锁文件。
`scope.environment_files` 引用这些文件；不使用 Docker 时可以提供安装脚本和锁文件。
`pip list` 可作为实际版本清单，但还需要记录系统依赖和安装步骤。

## 开始一次迁移

在仓库外建立工作区。用真实仓库 URL 和提交替换下面的占位值：

```bash
python scripts/migrate.py init ../migration-work/model --source https://github.com/ORG/REPO.git --revision COMMIT
# 人工已下载源码时，用本地目录替代 URL：
# python scripts/migrate.py init ../migration-work/model --source ../provided-repository
```

初始化保留来源、Git commit/状态和交付文件哈希，建立 `baseline/repository` 源端快照、
带 Git 初始提交的独立 `candidate`、`task.json` 和 `scope.json` 草稿。不会修改输入目录或覆盖已有工作区。
URL 获取失败可改用人工提供目录；本地输入按当前内容接收，不支持 `--revision`。
交付复用现有忽略目录规则，weights、datasets、缓存等不复制；这些外部材料必须另行提供并记录。
源码中若需要薄适配入口，可先在独立接收目录准备好再 init，保留其差异和来源；
适配入口只构造/调用仓库实现，不用另写模型替代原仓库。

Agent 接下来必须完成：

1. 阅读原仓库的正常使用和测试路径，确定推理/训练目标及模型依赖；配置两端环境。
2. 补齐 `task.json`：两端 entry/model/args/kwargs、解释器、device、固定输入或输入形状、
   权重和协议。`entry` 是仓库相对路径，`model` 是其中可调用的构造器名。
   source 固定为 `baseline/repository`，target 固定为 `candidate`；相对路径以 task 所在目录解析。
3. 补齐 `scope.json`：任务目的、公开入口、预处理、输出含义、状态/模式、验收依据、未覆盖范围，
   外部材料的来源与 SHA256，以及 安装脚本、两端锁文件或 Dockerfile 等环境配方路径。
4. 运行源端基线，核对它与原仓库语义一致，再开始迭代候选。框架导入或随机输入通过不能代替这项核对。

任务草稿故意不可直接通过检查，不替 Agent 猜测入口或宣称完成迁移。例如：

```json
{
  "schema_version": 1,
  "task_id": "example-inference",
  "inputs": [{"shape": [2, 8], "dtype": "float32"}],
  "source": {"repo": "baseline/repository", "entry": "main.py", "model": "TinyNet", "python": "/absolute/path/to/source/python", "device": "cpu"},
  "target": {"repo": "candidate", "entry": "main.py", "model": "TinyNet", "python": "/absolute/path/to/target/python", "device": "cpu"},
  "protocol": {"repeats": 3, "timeout": 600}
}
```

这是小模型的契约格式示例；真实任务应提供真实输入、checkpoint 和对应语义。训练任务使用
`protocol.profile=train-step`，显式指定 `protocol.train.optimizer`、`protocol.train.step` 和模型模式，输入第 0 维为步号；
两端入口提供同名优化器工厂与训练单步函数。具体字段层级和函数签名见下文 Adapter 调用契约。

`scope.json` 示例（SHA256 必须替换成实际文件摘要；无外部材料时显式填 `assets: []`）：

```json
{
  "purpose": "迁移指定 checkpoint 的公开推理入口",
  "public_entries": ["main.TinyNet"],
  "preprocessing": "固定 NPY 已按原仓库规则归一化，形状与 task 一致",
  "outputs": "按原入口顺序比较输出张量",
  "state_and_mode": "eval；加载相同 checkpoint；无训练更新",
  "acceptance_basis": "核对原仓库测试，并使用预先固定的重复验证协议",
  "limitations": ["未验证训练及其他输入分辨率"],
  "assets": [{"path": "checkpoint.pth", "origin": "原仓库发布地址或人工提供记录", "sha256": "实际SHA256"}],
  "environment_files": ["setup-environment.sh", "source.lock.txt", "target.lock.txt"]
}
```

scope 是可审查的语义说明，不是自动证明。没有可靠参考、真实数据或验收依据时，要明确记录缺口。

### 基线、迁移、冻结交付

```bash
python scripts/migrate.py baseline ../migration-work/model
python scripts/migrate.py check ../migration-work/model
python scripts/harness.py verify ../migration-work/model/task.json --root ../migration-work/model/evidence --trial repair-0
# Agent 根据 verify/trace/localize 的证据修改 candidate，按需继续迭代。
python scripts/migrate.py finalize ../migration-work/model --output ../migration-work/model-delivery-0
```

`baseline` 在实际双端解释器及执行环境下做框架导入探针、记录包版本，并运行核心 source 采集；
失败不生成 prepared.json。该文件冻结任务、材料、环境配方和源端身份。`check` 允许候选代码变化，
拒绝复用已变化的基线、任务、材料和双端环境。需要调整冻结条件时建立新工作区，保留旧记录。
修复环境及任务草稿后可以重试 baseline；已成功冻结的基线不会被覆盖。

`finalize` 复查准备证据，复用共享交付实现冻结完整候选和 Git diff，再将冻结快照交给现有完整 `verify`。
它不对仍在编辑的 candidate 给最终结果。`result.json` 保留范围说明、候选身份和原始 verify 报告；
退出码 0 表示该命令成功（finalize 还要求 verify 通过），2 表示准备/执行异常，3 表示验证未通过。
交付目录已存在时拒绝覆盖，重试使用新目录。

日常交付结果属于公开任务的验证，**不等于实验隐藏认证**，也不自动证明所有仓库功能等价。
准备检查通过、数值通过、真实任务指标保持应分别报告。任务定义由 Agent 编写时，应结合原仓库测试、
独立参考或人工语义复核；缺少依据则保留未判定。最终交付同时保存来源、环境配方、材料摘要、
scope、冻结候选和验证证据；在新环境按配方重建并对同一快照验证，才能确认环境可重建。
使用容器时另记录基础镜像身份；使用虚拟环境或远端环境时记录对应安装步骤与系统依赖。
交付目录另外保存 preparation.json、provenance.json 和环境配方副本；源码基线、权重和数据仍按 task
中的外部路径引用，重建时需保留工作区挂载或显式重新定位，交付目录不打包大体积第三方材料。

## Adapter 调用契约

字段定义由 `src/contracts/task.py` 实现，以下说明对应实际采集器调用。
`inspect` 解析和检查任务，不运行模型；它通过也不代表 adapter 可以执行。

| 配置 | 实际含义 |
| --- | --- |
| `source/target.entry` | 各自 repo 内的 Python 文件，例如 `adapter.py` |
| `source/target.model` | 文件内的构造器名，例如 `build_model` |
| `source/target.args`、`kwargs` | 只传给构造器：`build_model(*args, **kwargs)` |
| `inputs` | 模型推理或训练 step 的张量参数，不是构造参数 |
| `weights` | task 顶层的源端 checkpoint 文件路径；不是 `checkpoint` 字段 |
| `protocol.profile` | 推理默认 `fp32-inference`；训练填 `train-step`，不放在 task 顶层 |
| `protocol.train` | 训练函数名与模型模式等训练配置，仅用于 train-step |

构造器返回 PyTorch `nn.Module` 或 Jittor `nn.Module`。推理时 Harness 设置 eval，
按 inputs 组装参数调用 `model(*args, **kwargs)`；Jittor 模块实现 `execute`。
返回张量或由张量组成的 dict/list/tuple，两端输出的名称、结构和形状需要一致。
不要把打印 JSON 的命令行脚本当作模型入口。

输入每项都必须有 `shape`，建议显式设置 `dtype`。固定数据使用 `path` 指向 `.npy`，
文件实际 shape/dtype 必须与声明一致；路径相对于 task 文件解析。没有 path 时生成固定种子输入，
适合接口 smoke，不能替代真实预处理。无 `arg/key/pack` 时按列表顺序作为位置参数；
`arg` 指定关键字参数；`key` 将张量放入字典（同时有 arg 时作为该关键字的字典）；
`pack: list/tuple` 配合从 0 开始连续的 `item` 将张量组装成序列。

例如双输入推理的固定数据声明：

```json
"inputs": [
  {"path": "inputs/rays_o.npy", "shape": [1, 1024, 3], "dtype": "float32"},
  {"path": "inputs/rays_d.npy", "shape": [1, 1024, 3], "dtype": "float32"}
]
```

Harness 在 source 加载 weights（若未设置则使用构造出的状态），冻结输入和状态，
再把同一状态交给 target；不会调用 adapter 中自定义的 `load_checkpoint` 函数。
目标模型需暴露可匹配的参数名与形状。特殊 checkpoint 格式可在源端构造器中用原仓库 loader
读取，并在 scope 中记录路径、来源和摘要；不能只依赖两端设置相同随机种子获得同一权重。

训练按以下配置调用，两端 adapter 提供同名函数：

```json
"protocol": {
  "profile": "train-step", "repeats": 2, "timeout": 1800,
  "train": {
    "optimizer": "build_optimizer", "step": "train_step",
    "model_mode": "as_loaded", "sketch_dim": 4096
  }
}
```

```python
def build_optimizer(model):
    # 返回本框架 optimizer，或 (optimizer, scheduler, ...)；首项为 optimizer。
    ...

def train_step(model, optimizer_state, audio, targets, lengths):
    # 完成一次 zero_grad/backward/裁剪/更新及必要的 scheduler step。
    # 返回单元素 loss 张量或数值；不要在这里循环整个训练序列。
    ...
```

Harness 调用 `build_optimizer(model)`，将其完整返回值传给每次 `train_step`。
优化器要暴露 `param_groups` 和可读取的学习率，参数属于构造器返回的模型。
输入第 0 维是步号，每次切掉这一维：两步、每步音频 `[1,16000]` 时，
文件与 shape 均为 `[2,1,16000]`，targets 可为 `[2,3]`，lengths 为 `[2,1]`。
`model_mode` 可为 `train`、`eval`、`as_loaded`；后者保留构造器设定的冻结与训练状态。
`sketch_dim` 比较参数更新摘要，与选取参数名的 `observe` 二选一；省略两者时比较全部可训练参数。
训练验收还检查更新等证据，仅比较两次 loss 不足以代替 verify。

## 在迁移过程中使用反馈

```bash
python scripts/harness.py inspect ../migration-work/model/task.json
python scripts/harness.py run ../migration-work/model/task.json source --root ../migration-work/model/evidence --trial source-probe
python scripts/harness.py verify ../migration-work/model/task.json --root ../migration-work/model/evidence --trial repair-0
```

`run source` 可在完整 target 实现完成前探测源端；task 仍需有效的双端声明。
`migrate.py baseline` 则要求双端环境可导入、入口文件存在和 scope 完整。
`init` 已冻结 source，因此需要新增源端薄 adapter 时，先在独立接收目录准备好再 init；
已初始化的旧工作可以保留，把原始材料加 adapter 作为新的接收目录初始化，再搬入候选改动。
不要手改 migration.json 的摘要使旧冻结记录看起来仍然有效。

读取 verify 的 `passed`、`failure_code`、`summary` 和关联 manifest/日志。
退出码 3 表示本次检查没有通过，其中也可能包含源端或执行故障，不能一概写成迁移数值失败。
任务解析异常可能直接输出 stderr；准备入口的退出码 2 则输出 JSON error。
错误返回后 Agent 可继续检查环境、代码与实际接口，修复后换新的 trial 名运行；
Harness CLI 不负责终止或管理 Agent 会话。推理可进一步调用 `trace` 和 `localize`，
训练内部 trace 当前不支持，应使用实际运行日志或独立探针调查。

验收结果只覆盖冻结任务。缺失依赖时重新实现 source 模型，会改变参考依据；
即使 source/target 相符，也不能直接证明与原仓库一致。记录这类变化及独立核对结果，
不要为了得到通过结果而静默改变任务范围或验收标准。

## 交给代码 Agent 使用

将本仓库完整目录、目标仓库信息、执行环境访问方式和迁移目标一起交给 Agent。
工具路径与迁移工作区可以任意选择；本地使用不需要 `/opt/harness` 或 `/work` 挂载。
可以直接使用这段任务说明，补入实际路径和具体模型目标：

> Harness 位于 <工具目录>。先阅读 README.md，按实际环境安装控制端和双端依赖。
> 自主获取或接收源仓库、理解原始入口、准备任务、实现迁移，并在过程中调用 Harness。
> 使用 scripts/harness.py inspect/run/verify 获取反馈，用 scripts/migrate.py
> baseline/check/finalize 保存准备证据和冻结交付。根据实际反馈自行选择修复方式。
> 保留参考依据、运行命令、结果路径和未解决问题；最后提供 result.json，说明已验证范围。
> 未完成时保留当前工作与证据，明确尚未执行或无法判断的部分。

若通过 SSH 使用远端机器，将工具目录与工作区复制过去，**在远端执行 Harness**。
核心执行器启动调用所在机器的子进程，`source.python` / `target.python` 不是 SSH 地址。
远端控制解释器也需要 Python >= 3.10、NumPy < 2 和 PyYAML。
完成后取回输入、权重、任务、候选代码与证据，并保留路径映射；仅取回 candidate 不构成完整交付。

## 可选：Docker 隔离环境

仓库提供 Dockerfile，方便在本机隔离编译依赖与模型运行环境。
需要 Docker 的 Linux/WSL 环境中可执行：

```bash
docker build -f scripts/migration/Dockerfile -t jittor-harness:base .
mkdir -p ../migration-work
docker run --rm -it --mount type=bind,src="$(cd ../migration-work && pwd)",dst=/work jittor-harness:base
```

镜像内工具位于 `/opt/harness`，工作区位于 `/work`，控制环境位于 `/opt/control`，
双端解释器分别为 `/opt/source/bin/python` 和 `/opt/target/bin/python`。
镜像提供编译工具、NumPy/PyYAML；需要另外安装所选框架和模型依赖。
GPU 场景可用 `--build-arg BASE_IMAGE=<含所需 nvcc 的 CUDA devel 镜像>` 构建，
运行时配置宿主机驱动和容器 GPU 访问；具体配置取决于所选框架与硬件。
容器内使用同一套 init/baseline/check/verify/finalize 接口。

## 检查工具链路

`scripts/migration/smoke.py` 提供已知小模型的双端正例、输出加 1 的负例，
以及在新环境重验冻结快照的流程。配套 Docker 命令：

```bash
docker build -f scripts/migration/Dockerfile -t jittor-harness:standalone-check .
docker build -f scripts/migration/Smoke.Dockerfile -t jittor-harness:standalone-smoke .
docker volume create jittor-harness-smoke
docker run --rm --mount type=volume,src=jittor-harness-smoke,dst=/work jittor-harness:standalone-smoke python /opt/harness/scripts/migration/smoke.py setup /work/smoke
docker run --rm --mount type=volume,src=jittor-harness-smoke,dst=/work jittor-harness:standalone-smoke python /opt/harness/scripts/migration/smoke.py recheck /work/smoke
```

这项 smoke 验证工具执行与交付链路，不代表已验证任意仓库的自主迁移。
脚本默认使用上述容器解释器路径；在其他环境使用时需先调整该示例中的路径。

## 目录与结果范围

```text
src/                    任务契约、执行、采集、比较、验证与诊断
scripts/harness.py      从源码运行核心 CLI
scripts/migrate.py      迁移工作区、基线检查与冻结交付
scripts/migration/      打包工具、可选 Dockerfile 与 CPU smoke 示例
```

`bundle.json` 若存在，记录导出时工具文件的 SHA256；它不包含模型迁移成功的结论。
可以用 `python scripts/migration/bundle.py ../agent-harness` 导出独立工具目录。
公开使用无需实验控制器、隐藏任务或本地研究材料。

验证通过表示候选在已声明的任务、输入、权重与协议下通过检查。
它不会自动证明原仓库所有功能等价，也不自动证明真实任务指标保持。
任务范围由 Agent 编写时，应结合原仓库测试、独立参考或人工语义复核。
源端错误、执行故障和未完成检查都需要保留证据，不能直接当作候选数值失败。
训练内部定位与陌生仓库的通用环境准备仍需由外部 Agent 结合实际项目处理。

## 许可

[Apache-2.0](LICENSE)。
