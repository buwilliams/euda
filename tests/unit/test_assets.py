"""
Unit tests for assets module.

Tests for src/tools/data/assets.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch


class TestWriteAssetNewlineNormalization:
    """Test that write_asset normalizes escaped newlines from LLM output."""

    @pytest.fixture
    def assets_dir(self, tmp_path):
        """Create a temporary assets directory."""
        assets_path = tmp_path / "data" / "topics" / "assets"
        assets_path.mkdir(parents=True)
        return assets_path

    @pytest.fixture
    def patch_assets_dir(self, assets_dir):
        """Patch ASSETS_DIR to use temp directory."""
        from plugins.core.data import assets
        with patch.object(assets, 'ASSETS_DIR', assets_dir):
            yield assets_dir

    def test_write_asset_normalizes_escaped_newlines(self, patch_assets_dir):
        """Literal \\n sequences should be converted to actual newlines."""
        from plugins.core.data.assets import write_asset

        # Content with literal \n (as LLMs sometimes output)
        content = "# Header\\n\\nParagraph 1\\n\\nParagraph 2"

        result = write_asset("topic-123", "test.md", content)

        # Read back the file
        asset_path = patch_assets_dir / "topic-123" / "test.md"
        assert asset_path.exists()

        actual_content = asset_path.read_text()

        # Should have actual newlines, not literal \n
        assert "\\n" not in actual_content
        assert "\n" in actual_content
        assert actual_content == "# Header\n\nParagraph 1\n\nParagraph 2"

    def test_write_asset_preserves_actual_newlines(self, patch_assets_dir):
        """Actual newlines in content should be preserved."""
        from plugins.core.data.assets import write_asset

        # Content with actual newlines
        content = "# Header\n\nParagraph 1\n\nParagraph 2"

        write_asset("topic-456", "normal.md", content)

        asset_path = patch_assets_dir / "topic-456" / "normal.md"
        actual_content = asset_path.read_text()

        assert actual_content == "# Header\n\nParagraph 1\n\nParagraph 2"

    def test_write_asset_handles_mixed_newlines(self, patch_assets_dir):
        """Content with both literal \\n and actual newlines should be handled."""
        from plugins.core.data.assets import write_asset

        # Mix of literal \n and actual newlines
        content = "Line 1\\nLine 2\nLine 3\\nLine 4"

        write_asset("topic-789", "mixed.md", content)

        asset_path = patch_assets_dir / "topic-789" / "mixed.md"
        actual_content = asset_path.read_text()

        # All should become actual newlines
        assert "\\n" not in actual_content
        assert actual_content == "Line 1\nLine 2\nLine 3\nLine 4"

    def test_write_asset_handles_empty_content(self, patch_assets_dir):
        """Empty content should be handled gracefully."""
        from plugins.core.data.assets import write_asset

        result = write_asset("topic-empty", "empty.md", "")

        asset_path = patch_assets_dir / "topic-empty" / "empty.md"
        assert asset_path.exists()
        assert asset_path.read_text() == ""

    def test_write_asset_handles_none_content(self, patch_assets_dir):
        """None content should be handled gracefully."""
        from plugins.core.data.assets import write_asset

        # This tests the conditional: content.replace(...) if content else content
        # Since None is falsy, it should pass through
        try:
            result = write_asset("topic-none", "none.md", None)
            # If it doesn't raise, check the file wasn't created with "None"
            asset_path = patch_assets_dir / "topic-none" / "none.md"
            if asset_path.exists():
                assert asset_path.read_text() != "None"
        except (TypeError, AttributeError):
            # Expected - can't write None to file
            pass

    def test_write_asset_creates_directory(self, patch_assets_dir):
        """Asset directory should be created if it doesn't exist."""
        from plugins.core.data.assets import write_asset

        result = write_asset("new-topic", "new.md", "content")

        asset_path = patch_assets_dir / "new-topic" / "new.md"
        assert asset_path.exists()
        assert asset_path.read_text() == "content"


class TestReadAsset:
    """Test asset reading functionality."""

    @pytest.fixture
    def assets_dir(self, tmp_path):
        """Create a temporary assets directory with test files."""
        assets_path = tmp_path / "data" / "topics" / "assets"
        assets_path.mkdir(parents=True)

        # Create a test asset
        topic_dir = assets_path / "topic-read"
        topic_dir.mkdir()
        (topic_dir / "test.md").write_text("# Test\n\nContent here")

        return assets_path

    @pytest.fixture
    def patch_assets_dir(self, assets_dir):
        """Patch ASSETS_DIR to use temp directory."""
        from plugins.core.data import assets
        with patch.object(assets, 'ASSETS_DIR', assets_dir):
            yield assets_dir

    def test_read_asset_returns_content(self, patch_assets_dir):
        """read_asset should return file content."""
        from plugins.core.data.assets import read_asset

        result = read_asset("topic-read", "test.md")

        assert result is not None
        assert result["filename"] == "test.md"
        assert result["content"] == "# Test\n\nContent here"

    def test_read_asset_not_found(self, patch_assets_dir):
        """read_asset should return error for non-existent file."""
        from plugins.core.data.assets import read_asset

        result = read_asset("topic-read", "nonexistent.md")

        assert "error" in result


class TestListRecentAssets:
    """Test listing recent assets across all topics."""

    @pytest.fixture
    def assets_dir(self, tmp_path):
        """Create a temporary assets directory with multiple topic assets."""
        assets_path = tmp_path / "data" / "topics" / "assets"
        assets_path.mkdir(parents=True)

        # Create assets in multiple topics
        for i, topic_id in enumerate(["topic-a", "topic-b", "topic-c"]):
            topic_dir = assets_path / topic_id
            topic_dir.mkdir()
            (topic_dir / f"file{i}.md").write_text(f"Content {i}")

        return assets_path

    @pytest.fixture
    def patch_assets_dir(self, assets_dir):
        """Patch ASSETS_DIR to use temp directory."""
        from plugins.core.data import assets
        with patch.object(assets, 'ASSETS_DIR', assets_dir):
            yield assets_dir

    def test_list_recent_assets_returns_all(self, patch_assets_dir):
        """list_recent_assets should return assets from all topics."""
        from plugins.core.data.assets import list_recent_assets

        result = list_recent_assets()

        assert len(result) == 3
        topic_ids = {a["topic_id"] for a in result}
        assert topic_ids == {"topic-a", "topic-b", "topic-c"}

    def test_list_recent_assets_respects_limit(self, patch_assets_dir):
        """list_recent_assets should respect the limit parameter."""
        from plugins.core.data.assets import list_recent_assets

        result = list_recent_assets(limit=2)

        assert len(result) == 2

    def test_list_recent_assets_includes_topic_id(self, patch_assets_dir):
        """Each asset should include its topic_id for navigation."""
        from plugins.core.data.assets import list_recent_assets

        result = list_recent_assets()

        for asset in result:
            assert "topic_id" in asset
            assert "filename" in asset
            assert asset["topic_id"].startswith("topic-")
