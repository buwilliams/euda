import json
from pathlib import Path

import pytest

DEFAULT_GUIDE = """# guide

## Purpose
- Instruct consolidation behavior.
"""

DEFAULT_IDENTITY = """# neo

## Purpose
- Seed.
"""


def write_prompts(data_dir: Path) -> None:
    (data_dir / "consolidate-system-prompt.md").write_text(
        "system", encoding="utf-8"
    )
    (data_dir / "consolidate-prompt.md").write_text(
        "Guide:\n{guide}\n\nIdentity:\n{identity}\n\nData:\n{data}\n\nVariance: {variance}\n",
        encoding="utf-8",
    )


def write_guide(data_dir: Path, version: int = 1, content: str | None = None) -> Path:
    guide_dir = data_dir / "guide"
    guide_dir.mkdir(parents=True, exist_ok=True)
    body = content or DEFAULT_GUIDE
    path = guide_dir / f"guide-{version}.md"
    path.write_text(body, encoding="utf-8")
    meta = guide_dir / f"guide-{version}.json"
    meta.write_text(
        json.dumps(
            {"version": version, "created_at": "2026-02-02T00:00:00+00:00", "source": {"type": "seed"}},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_identity(data_dir: Path, name: str = "neo", version: int = 1, content: str | None = None) -> Path:
    identity_dir = data_dir / "identity" / name
    identity_dir.mkdir(parents=True, exist_ok=True)
    body = content or DEFAULT_IDENTITY
    path = identity_dir / f"identity-{version}.md"
    path.write_text(body, encoding="utf-8")
    meta = identity_dir / f"identity-{version}.json"
    meta.write_text(
        json.dumps(
            {"name": name, "version": version, "created_at": "2026-02-02T00:00:00+00:00", "source": {"type": "seed"}},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def identity_env(tmp_path, monkeypatch):
    config_dir = tmp_path / "identity"
    config_dir.mkdir(parents=True)
    data_dir = config_dir / "data"
    data_dir.mkdir(parents=True)
    write_prompts(data_dir)
    (config_dir / "config.default.json").write_text(
        json.dumps(
            {
                "guide": {"max_versions": 20},
                "identity": {"max_chars": 1000, "max_versions": 20},
                "consolidate": {
                    "variance": "medium",
                    "max_change_ratio": 0.5,
                    "llm_timeout": 5.0,
                    "provider": None,
                    "model": None,
                },
                "prompts": {
                    "consolidate_system": "consolidate-system-prompt.md",
                    "consolidate_user": "consolidate-prompt.md",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IDENTITY_CONFIG_DIR", str(config_dir))
    return config_dir
