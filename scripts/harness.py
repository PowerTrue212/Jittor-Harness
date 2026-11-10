"""Run the core CLI from a checkout or Agent bundle without an editable install."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Reuse the preparation entry's binding to this copy of the core package.
import scripts.migrate  # noqa: E402,F401
from jittor_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
