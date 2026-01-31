from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_shared_cli() -> None:
    if "shared_cli" in sys.modules:
        return
    shared_path = Path(__file__).resolve().parents[3] / "shared-cli.py"
    if not shared_path.exists():
        return
    spec = importlib.util.spec_from_file_location("shared_cli", shared_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_cli"] = module
    spec.loader.exec_module(module)


_load_shared_cli()
del _load_shared_cli
