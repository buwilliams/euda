"""Tests for layered config loading."""

import json
import pytest
from pathlib import Path

from src.core.config import deep_merge, load_layered_config, save_config_overrides


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_simple_override(self):
        """Override values take precedence."""
        base = {"a": 1, "b": 2}
        overrides = {"b": 3}
        result = deep_merge(base, overrides)
        assert result == {"a": 1, "b": 3}

    def test_add_new_keys(self):
        """Overrides can add new keys."""
        base = {"a": 1}
        overrides = {"b": 2}
        result = deep_merge(base, overrides)
        assert result == {"a": 1, "b": 2}

    def test_nested_dict_merge(self):
        """Nested dicts are merged recursively."""
        base = {"outer": {"a": 1, "b": 2}}
        overrides = {"outer": {"b": 3, "c": 4}}
        result = deep_merge(base, overrides)
        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_deeply_nested_merge(self):
        """Deep nesting works correctly."""
        base = {"l1": {"l2": {"l3": {"a": 1}}}}
        overrides = {"l1": {"l2": {"l3": {"b": 2}}}}
        result = deep_merge(base, overrides)
        assert result == {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}}

    def test_array_replace_not_merge(self):
        """Arrays are replaced, not merged."""
        base = {"triggers": [{"event": "morning"}]}
        overrides = {"triggers": [{"event": "evening"}]}
        result = deep_merge(base, overrides)
        assert result == {"triggers": [{"event": "evening"}]}

    def test_empty_overrides(self):
        """Empty overrides returns base unchanged."""
        base = {"a": 1, "b": 2}
        result = deep_merge(base, {})
        assert result == {"a": 1, "b": 2}

    def test_empty_base(self):
        """Empty base returns overrides."""
        overrides = {"a": 1}
        result = deep_merge({}, overrides)
        assert result == {"a": 1}

    def test_override_dict_with_scalar(self):
        """Can replace a dict with a scalar value."""
        base = {"a": {"nested": 1}}
        overrides = {"a": "replaced"}
        result = deep_merge(base, overrides)
        assert result == {"a": "replaced"}

    def test_override_scalar_with_dict(self):
        """Can replace a scalar with a dict."""
        base = {"a": "scalar"}
        overrides = {"a": {"nested": 1}}
        result = deep_merge(base, overrides)
        assert result == {"a": {"nested": 1}}

    def test_base_not_modified(self):
        """Original base dict is not modified."""
        base = {"a": 1}
        overrides = {"a": 2}
        deep_merge(base, overrides)
        assert base == {"a": 1}


class TestLoadLayeredConfig:
    """Tests for load_layered_config function."""

    def test_defaults_only(self, tmp_path):
        """Load works with only defaults file."""
        defaults = {"id": "test", "name": "Test"}
        (tmp_path / "config.defaults.json").write_text(json.dumps(defaults))

        result = load_layered_config(tmp_path)
        assert result == defaults

    def test_overrides_only(self, tmp_path):
        """Load works with only overrides file."""
        overrides = {"id": "test", "triggers": []}
        (tmp_path / "config.json").write_text(json.dumps(overrides))

        result = load_layered_config(tmp_path)
        assert result == overrides

    def test_both_files_merged(self, tmp_path):
        """Both files are merged correctly."""
        defaults = {"id": "test", "name": "Test", "state": "enabled"}
        overrides = {"state": "disabled", "extra": "value"}

        (tmp_path / "config.defaults.json").write_text(json.dumps(defaults))
        (tmp_path / "config.json").write_text(json.dumps(overrides))

        result = load_layered_config(tmp_path)
        assert result == {
            "id": "test",
            "name": "Test",
            "state": "disabled",
            "extra": "value"
        }

    def test_no_config_files(self, tmp_path):
        """Returns None when no config files exist."""
        result = load_layered_config(tmp_path)
        assert result is None

    def test_nested_merge_in_files(self, tmp_path):
        """Nested structures are merged across files."""
        defaults = {
            "id": "test",
            "token_budget": {
                "frequency": "daily",
                "input_ratio": 0.8,
                "output_ratio": 0.2
            }
        }
        overrides = {
            "token_budget": {
                "frequency": "hourly"
            }
        }

        (tmp_path / "config.defaults.json").write_text(json.dumps(defaults))
        (tmp_path / "config.json").write_text(json.dumps(overrides))

        result = load_layered_config(tmp_path)
        assert result["token_budget"] == {
            "frequency": "hourly",
            "input_ratio": 0.8,
            "output_ratio": 0.2
        }

    def test_triggers_replaced_not_merged(self, tmp_path):
        """Triggers array is replaced, not merged."""
        defaults = {
            "id": "test",
            "triggers": [
                {"event": "morning", "action": "consolidate"}
            ]
        }
        overrides = {
            "triggers": [
                {"event": "evening", "action": "quote"}
            ]
        }

        (tmp_path / "config.defaults.json").write_text(json.dumps(defaults))
        (tmp_path / "config.json").write_text(json.dumps(overrides))

        result = load_layered_config(tmp_path)
        assert result["triggers"] == [{"event": "evening", "action": "quote"}]

    def test_custom_filenames(self, tmp_path):
        """Can use custom filenames."""
        defaults = {"a": 1}
        overrides = {"b": 2}

        (tmp_path / "base.json").write_text(json.dumps(defaults))
        (tmp_path / "user.json").write_text(json.dumps(overrides))

        result = load_layered_config(
            tmp_path,
            defaults_filename="base.json",
            overrides_filename="user.json"
        )
        assert result == {"a": 1, "b": 2}


class TestSaveConfigOverrides:
    """Tests for save_config_overrides function."""

    def test_save_creates_file(self, tmp_path):
        """Save creates the overrides file."""
        overrides = {"id": "test", "state": "disabled"}
        save_config_overrides(tmp_path, overrides)

        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved == overrides

    def test_save_overwrites_existing(self, tmp_path):
        """Save overwrites existing overrides file."""
        (tmp_path / "config.json").write_text('{"old": "data"}')

        overrides = {"new": "data"}
        save_config_overrides(tmp_path, overrides)

        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved == {"new": "data"}

    def test_save_preserves_defaults(self, tmp_path):
        """Save doesn't affect defaults file."""
        defaults = {"id": "test", "name": "Test"}
        (tmp_path / "config.defaults.json").write_text(json.dumps(defaults))

        overrides = {"state": "disabled"}
        save_config_overrides(tmp_path, overrides)

        # Defaults unchanged
        saved_defaults = json.loads((tmp_path / "config.defaults.json").read_text())
        assert saved_defaults == defaults

        # Overrides saved
        saved_overrides = json.loads((tmp_path / "config.json").read_text())
        assert saved_overrides == overrides

    def test_custom_filename(self, tmp_path):
        """Can use custom overrides filename."""
        overrides = {"custom": "data"}
        save_config_overrides(tmp_path, overrides, overrides_filename="custom.json")

        saved = json.loads((tmp_path / "custom.json").read_text())
        assert saved == {"custom": "data"}
