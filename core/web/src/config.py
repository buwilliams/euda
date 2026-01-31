import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

CONFIG_ENV_VAR = "WEB_CONFIG_DIR"
DEFAULT_CONFIG_FILENAME = "config.default.json"
OVERRIDE_CONFIG_FILENAME = "config.json"


def config_dir() -> Path:
    env_dir = os.environ.get(CONFIG_ENV_VAR)
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    base_dir = config_dir()
    default_path = base_dir / DEFAULT_CONFIG_FILENAME
    if not default_path.exists():
        raise FileNotFoundError(f"Missing {DEFAULT_CONFIG_FILENAME} in {base_dir}")
    default_config = load_json(default_path)
    override_path = base_dir / OVERRIDE_CONFIG_FILENAME
    override_config = load_json(override_path)
    merged = deep_merge(default_config, override_config)
    return merged, override_config


def write_override(override: Dict[str, Any]) -> None:
    base_dir = config_dir()
    save_json(base_dir / OVERRIDE_CONFIG_FILENAME, override)


def get_value(data: Dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(key)
        current = current[part]
    return current


def set_value(data: Dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    current: Dict[str, Any] = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
