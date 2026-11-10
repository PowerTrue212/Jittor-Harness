"""Run installed Harness or its source directory in a model environment."""
from __future__ import annotations

if not __package__:
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "jittor_harness", root / "__init__.py", submodule_search_locations=[str(root)],
    )
    assert spec is not None and spec.loader is not None
    package = importlib.util.module_from_spec(spec)
    sys.modules["jittor_harness"] = package
    spec.loader.exec_module(package)

from jittor_harness.cli import main  # noqa: E402

raise SystemExit(main())
