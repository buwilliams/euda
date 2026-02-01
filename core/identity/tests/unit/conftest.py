import json
from pathlib import Path

import pytest


DEFAULT_TRAITS = [
    {"name": "Purpose", "instruction": "Why the agent exists."},
    {"name": "Behavioral Rules", "instruction": "Must/must-not constraints."},
    {"name": "Voice", "instruction": "Communication style."},
]


def write_prompts(data_dir: Path) -> None:
    (data_dir / "consolidate-system-prompt.md").write_text(
        "system", encoding="utf-8"
    )
    (data_dir / "consolidate-prompt.md").write_text(
        "Schema: {schema_name} v{schema_version}\n{traits_markdown}\n{current_identity}\n{source_label}\n{source_metadata}\n{source_content}\n",
        encoding="utf-8",
    )


def write_schema(data_dir: Path, schema: str = "cognitive-core", version: int = 1) -> Path:
    schema_dir = data_dir / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": schema,
        "schema_id": "schema-123",
        "version": version,
        "created_at": "2026-02-01T00:00:00+00:00",
        "traits": DEFAULT_TRAITS,
    }
    path = schema_dir / f"{schema}-{version}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def identity_env(tmp_path, monkeypatch):
    config_dir = tmp_path / "identity"
    config_dir.mkdir(parents=True)
    data_dir = config_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "schema").mkdir(parents=True, exist_ok=True)
    write_prompts(data_dir)
    (config_dir / "config.default.json").write_text(
        json.dumps(
            {
                "default_schema": "cognitive-core",
                "prompts": {
                    "system": "consolidate-system-prompt.md",
                    "user": "consolidate-prompt.md",
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
