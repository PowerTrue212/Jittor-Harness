# Jittor Harness

[中文使用说明与完整接口契约](README.md)

Reproducible execution, verification and diagnostics for PyTorch-to-Jittor migrations.
A code agent inspects the source project, prepares dependencies and implements the port.
Harness runs both frameworks against an explicit task and records outputs, training updates
and verification evidence.

**Use a local environment, virtual environments, a remote server or a container. Docker is optional.**
Provide the source repository, both framework environments, inputs, weights and a defined
acceptance scope. The agent can fetch the source, or you can provide a local copy.

## Install

Run these commands from the repository root. Examples use a Linux/WSL shell.
The control interpreter requires Python >= 3.10:

```bash
python3 -m venv .venvs/control
source .venvs/control/bin/activate
python -m pip install .
python scripts/harness.py --help
python scripts/migrate.py --help
```

The installed core CLI is also available as `python -m jittor_harness` or `jittor-harness`.
`scripts/harness.py` binds to the current source tree. Keep the repository directory to use
preparation scripts and examples; the wheel provides the core CLI only.
On Windows, create the control environment with `py -3 -m venv .venvs/control` and use
`.venvs/control/Scripts/python.exe`. Configure model execution separately for the selected frameworks.
Real dual-framework smoke checks have run in a Linux container; this does not establish support
for every operating system or GPU configuration.

Use separate environments for the two frameworks if needed:

```bash
python3 -m venv .venvs/source
python3 -m venv .venvs/target
.venvs/source/bin/python -m pip install 'numpy>=1.24,<2' 'PyYAML>=6.0'
.venvs/target/bin/python -m pip install 'numpy>=1.24,<2' 'PyYAML>=6.0'
```

Install PyTorch, Jittor and model dependencies with versions appropriate to the project and hardware.
Set `source.python` and `target.python` to actual absolute interpreter paths in `task.json`.
Select `cpu` or `cuda` explicitly. Model environments need NumPy/PyYAML but do not need a separate
Harness installation. Record installation steps, system dependencies and lock files in
`scope.environment_files`; a Dockerfile is one possible environment recipe.

## Migration workflow

Replace the URL and commit below with the actual project, or provide a local directory:

```bash
python scripts/migrate.py init ../migration-work/model --source https://github.com/ORG/REPO.git --revision COMMIT
# Alternative: --source ../provided-repository
```

Initialization freezes the source in `baseline/repository`, creates an editable `candidate`,
and writes `task.json` and `scope.json` drafts. Prepare any thin source adapter before initialization.
The adapter should call the original implementation. Source snapshots are immutable after initialization.

Fill in model constructors, interpreter paths, fixed inputs, weights, execution protocol,
acceptance scope and environment recipes. See the [complete adapter contract](README.md#adapter-调用契约).
Then run:

```bash
python scripts/harness.py inspect ../migration-work/model/task.json
python scripts/migrate.py baseline ../migration-work/model
python scripts/migrate.py check ../migration-work/model
python scripts/harness.py verify ../migration-work/model/task.json --root ../migration-work/model/evidence --trial repair-0
python scripts/migrate.py finalize ../migration-work/model --output ../migration-work/model-delivery-0
```

During migration, the agent reads feedback and chooses its next repair. Use a new trial name for
each iteration and a new output directory for each delivery. `finalize` verifies the frozen candidate
and writes `result.json`. A passed result applies to the declared task and scope, not every function
in the original project. Execution failures and incomplete checks are not automatically numerical failures.

## Agent and remote use

Give the agent this directory, a concrete migration objective, source materials and execution access.
Ask it to read README, configure both environments, implement the port, invoke checks during migration,
and return verification evidence with the completed and untested scope. Paths are configurable;
local use does not require `/opt/harness` or `/work` mounts.

For SSH execution, copy the tools and workspace to the runtime host and invoke Harness there.
The core executor starts local subprocesses; interpreter fields are not SSH addresses.
Retrieve the workspace, inputs, weights and evidence as well as candidate code.

## Optional Docker environment

```bash
docker build -f scripts/migration/Dockerfile -t jittor-harness:base .
mkdir -p ../migration-work
docker run --rm -it --mount type=bind,src="$(cd ../migration-work && pwd)",dst=/work jittor-harness:base
```

The image contains the tools at `/opt/harness`, a control environment and two model environments
at `/opt/source` and `/opt/target`. Install the selected frameworks and project dependencies separately.
Use the same migration commands inside the container. The [Chinese guide](README.md#检查工具链路)
includes the Docker smoke procedure for positive, negative and fresh-environment checks.
It checks the toolchain, not autonomous migration of an unfamiliar project.

## Contents

- `src/`: task contracts, execution, capture, comparison, verification and diagnostics.
- `scripts/harness.py`: core CLI from source.
- `scripts/migrate.py`: workspaces, preparation evidence and frozen delivery.
- `scripts/migration/`: export tool, optional Dockerfiles and CPU smoke example.

No experiment controller or private research directory is required. Export a standalone copy with
`python scripts/migration/bundle.py ../agent-harness`. If present, `bundle.json` records exported file
hashes; it is not a migration verification result.

Licensed under [Apache-2.0](LICENSE).
