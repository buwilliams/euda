from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_shared_router() -> None:
    if "shared_router" in sys.modules:
        return
    shared_path = Path(__file__).resolve().parents[3] / "shared-router.py"
    if not shared_path.exists():
        return
    spec = importlib.util.spec_from_file_location("shared_router", shared_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_router"] = module
    spec.loader.exec_module(module)


_load_shared_router()
del _load_shared_router
