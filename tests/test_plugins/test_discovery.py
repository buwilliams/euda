"""
Plugin Discovery Tests.

Tests for plugin discovery, validation, and caching.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    def test_discover_plugins_finds_valid_plugins(self):
        """Should find all valid plugins in the plugins directory."""
        from src.plugins import discover_plugins

        plugins = discover_plugins()

        # Should find our built-in plugins
        plugin_names = [p.name for p in plugins]
        assert "core" in plugin_names
        assert "nextcloud" in plugin_names
        assert "speech" in plugin_names
        assert "mastodon" in plugin_names

    def test_discover_plugins_returns_plugin_info(self):
        """Should return PluginInfo objects with correct attributes."""
        from src.plugins import discover_plugins, PluginInfo

        plugins = discover_plugins()

        for plugin in plugins:
            assert isinstance(plugin, PluginInfo)
            assert plugin.name
            assert plugin.path.is_dir()

    def test_discover_plugins_extracts_descriptions(self):
        """Should extract descriptions from plugin docstrings."""
        from src.plugins import discover_plugins

        plugins = discover_plugins()
        core_plugin = next(p for p in plugins if p.name == "core")

        # Core plugin should have a description from its docstring
        assert core_plugin.description
        assert "Core" in core_plugin.description or "Euno" in core_plugin.description

    def test_discover_plugins_skips_hidden_directories(self, tmp_path):
        """Should skip directories starting with . or _."""
        from src.plugins.discovery import discover_plugins, PLUGINS_DIR, invalidate_cache

        # Create a mock plugins directory
        mock_plugins = tmp_path / "plugins"
        mock_plugins.mkdir()

        # Create valid plugin
        valid_plugin = mock_plugins / "valid"
        valid_plugin.mkdir()
        (valid_plugin / "cli.py").write_text('"""Valid plugin."""\ndef main(): pass')

        # Create hidden/private directories
        hidden = mock_plugins / ".hidden"
        hidden.mkdir()
        (hidden / "cli.py").write_text('def main(): pass')

        private = mock_plugins / "_private"
        private.mkdir()
        (private / "cli.py").write_text('def main(): pass')

        with patch('src.plugins.discovery.PLUGINS_DIR', mock_plugins):
            invalidate_cache()
            plugins = discover_plugins()

        plugin_names = [p.name for p in plugins]
        assert "valid" in plugin_names
        assert ".hidden" not in plugin_names
        assert "_private" not in plugin_names


class TestPluginValidation:
    """Test plugin validation functionality."""

    def test_validate_plugin_requires_cli_py(self, tmp_path):
        """Should return False if cli.py doesn't exist."""
        from src.plugins.discovery import validate_plugin, PLUGINS_DIR

        # Create plugin dir without cli.py
        plugin_dir = tmp_path / "plugins" / "no_cli"
        plugin_dir.mkdir(parents=True)

        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path / "plugins"):
            assert validate_plugin("no_cli") is False

    def test_validate_plugin_requires_main_function(self, tmp_path):
        """Should return False if main() function doesn't exist."""
        from src.plugins.discovery import validate_plugin, PLUGINS_DIR

        # Create plugin with cli.py but no main()
        plugin_dir = tmp_path / "plugins" / "no_main"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "cli.py").write_text('def other_function(): pass')

        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path / "plugins"):
            assert validate_plugin("no_main") is False

    def test_validate_plugin_accepts_valid_plugin(self, tmp_path):
        """Should return True for valid plugin structure."""
        from src.plugins.discovery import validate_plugin

        # Create valid plugin
        plugin_dir = tmp_path / "plugins" / "valid"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "cli.py").write_text('"""Plugin."""\ndef main(): pass')

        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path / "plugins"):
            assert validate_plugin("valid") is True

    def test_validate_plugin_returns_false_for_nonexistent(self):
        """Should return False for nonexistent plugin."""
        from src.plugins.discovery import validate_plugin

        assert validate_plugin("nonexistent_plugin_xyz") is False


class TestGetPluginInfo:
    """Test getting info for specific plugins."""

    def test_get_plugin_info_returns_info(self):
        """Should return PluginInfo for valid plugin."""
        from src.plugins import get_plugin_info, PluginInfo

        info = get_plugin_info("core")

        assert isinstance(info, PluginInfo)
        assert info.name == "core"
        assert info.path.is_dir()

    def test_get_plugin_info_raises_for_nonexistent(self):
        """Should raise PluginNotFoundError for nonexistent plugin."""
        from src.plugins import get_plugin_info, PluginNotFoundError

        with pytest.raises(PluginNotFoundError):
            get_plugin_info("nonexistent_plugin_xyz")

    def test_get_plugin_info_raises_for_invalid(self, tmp_path):
        """Should raise PluginValidationError for invalid plugin."""
        from src.plugins.discovery import get_plugin_info, PLUGINS_DIR
        from src.plugins import PluginValidationError

        # Create invalid plugin (no main function)
        plugin_dir = tmp_path / "plugins" / "invalid"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "cli.py").write_text('x = 1')

        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path / "plugins"):
            with pytest.raises(PluginValidationError):
                get_plugin_info("invalid")


class TestPluginCache:
    """Test plugin discovery caching."""

    def test_invalidate_cache_clears_cache(self):
        """Should clear the plugin cache."""
        from src.plugins.discovery import discover_plugins, invalidate_cache, _plugin_cache

        # First call populates cache
        plugins1 = discover_plugins()

        # Invalidate
        invalidate_cache()

        # Import again to check cache is None
        from src.plugins import discovery
        assert discovery._plugin_cache is None

    def test_discover_plugins_uses_cache(self):
        """Should return cached results on subsequent calls."""
        from src.plugins.discovery import discover_plugins, invalidate_cache

        invalidate_cache()

        # First call
        plugins1 = discover_plugins()

        # Second call should return same objects
        plugins2 = discover_plugins()

        assert plugins1 is plugins2
