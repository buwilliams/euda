"""
Unit tests for deletion tombstones.

Tests for src/core/data/deletions.py
"""

from unittest.mock import patch


def test_record_topic_deletion_idempotent(tmp_path):
    """Topic tombstones are created once and not overwritten."""
    from src.core.data import deletions as deletions_module

    deletions_path = tmp_path / "data" / "system" / "deletions.json"
    deletions_path.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(deletions_module, "DELETIONS_PATH", deletions_path):
        deletions_module.record_topic_deletion("topic-1")
        first = deletions_module.get_deletions()["topics"]["topic-1"]
        deletions_module.record_topic_deletion("topic-1")
        second = deletions_module.get_deletions()["topics"]["topic-1"]

    assert first == second


def test_record_memory_deletion_idempotent(tmp_path):
    """Memory tombstones are created once and not overwritten."""
    from src.core.data import deletions as deletions_module

    deletions_path = tmp_path / "data" / "system" / "deletions.json"
    deletions_path.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(deletions_module, "DELETIONS_PATH", deletions_path):
        deletions_module.record_memory_deletion("user", "mem-1")
        first = deletions_module.get_deletions()["memory"]["user"]["mem-1"]
        deletions_module.record_memory_deletion("user", "mem-1")
        second = deletions_module.get_deletions()["memory"]["user"]["mem-1"]

    assert first == second


def test_record_memory_deletions_batch(tmp_path):
    """Batch tombstone creation records multiple entries."""
    from src.core.data import deletions as deletions_module

    deletions_path = tmp_path / "data" / "system" / "deletions.json"
    deletions_path.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(deletions_module, "DELETIONS_PATH", deletions_path):
        deletions_module.record_memory_deletions("chat", ["mem-1", "mem-2"])
        deletions = deletions_module.get_deletions()["memory"]["chat"]

    assert set(deletions.keys()) == {"mem-1", "mem-2"}
