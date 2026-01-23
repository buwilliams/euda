"""
Pattern Confidence Invariant Tests.

Spec: docs/3_system.md, spec/8_patterns.md

These tests verify pattern confidence thresholds for prompt inclusion.

Invariants tested:
- Only patterns with confidence >= 0.7 are included in prompts
- Pattern confidence decays without validation
- Pattern confidence increases with validation
"""

import pytest
from datetime import datetime


@pytest.mark.invariant
class TestPatternConfidenceThreshold:
    """Test that pattern confidence threshold is enforced."""

    def test_high_confidence_patterns_included(self, patch_data_dir):
        """Patterns with confidence >= 0.7 should be included in prompts.

        Spec: Pattern confidence > 0.7 for prompt inclusion.
        """
        from src.agent.cognition.metacognition.consolidation.patterns import (
            PatternStore, format_patterns_for_prompt
        )

        store = PatternStore()
        store.temporal = [
            {
                "id": "tmp-high",
                "description": "High confidence pattern",
                "granularity": "daily",
                "time_window": {"start": "09:00", "end": "10:00"},
                "confidence": 0.8,  # Above 0.7
                "evidence_count": 5,
                "first_observed": "2024-01-01",
                "last_observed": "2024-01-15"
            }
        ]

        # Using default 0.6 threshold for format_patterns_for_prompt
        # But testing with 0.7 explicitly
        result = format_patterns_for_prompt(store, min_confidence=0.7)

        assert "High confidence pattern" in result

    def test_low_confidence_patterns_excluded(self, patch_data_dir):
        """Patterns with confidence < 0.7 should be excluded from prompts.

        Spec: Only high-confidence patterns inform behavior.
        """
        from src.agent.cognition.metacognition.consolidation.patterns import (
            PatternStore, format_patterns_for_prompt
        )

        store = PatternStore()
        store.temporal = [
            {
                "id": "tmp-low",
                "description": "Low confidence pattern",
                "granularity": "daily",
                "time_window": {"start": "09:00", "end": "10:00"},
                "confidence": 0.5,  # Below 0.7
                "evidence_count": 2,
                "first_observed": "2024-01-01",
                "last_observed": "2024-01-05"
            }
        ]

        result = format_patterns_for_prompt(store, min_confidence=0.7)

        assert "Low confidence pattern" not in result

    def test_boundary_confidence_included(self):
        """Patterns with exactly 0.7 confidence should be included.

        Spec: Threshold is >= 0.7, not > 0.7.
        """
        from src.agent.cognition.metacognition.consolidation.patterns import (
            PatternStore, get_high_confidence_patterns
        )

        store = PatternStore()
        store.temporal = [
            {
                "id": "tmp-boundary",
                "description": "Boundary pattern",
                "granularity": "daily",
                "time_window": {},
                "confidence": 0.7,  # Exactly at threshold
                "evidence_count": 3,
                "first_observed": "2024-01-01",
                "last_observed": "2024-01-10"
            }
        ]

        result = get_high_confidence_patterns(store, min_confidence=0.7)

        assert len(result["temporal"]) == 1
        assert result["temporal"][0]["id"] == "tmp-boundary"


@pytest.mark.invariant
class TestPatternConfidenceEvolution:
    """Test that pattern confidence evolves correctly."""

    def test_confidence_increases_on_validation(self):
        """Pattern confidence should increase when validated.

        Spec: confidence_boost_on_validation = 0.15 (default).
        """
        from src.agent.cognition.metacognition.consolidation.patterns import update_confidence

        pattern = {
            "id": "test-pattern",
            "confidence": 0.5,
            "evidence_count": 1,
            "last_observed": "2024-01-01"
        }

        update_confidence(pattern, validated=True)

        # Default boost is 0.15
        assert pattern["confidence"] == pytest.approx(0.65, abs=0.01)
        assert pattern["evidence_count"] == 2

    def test_confidence_decreases_without_validation(self):
        """Pattern confidence should decay when not validated.

        Spec: confidence_decay_rate = 0.1 (default).
        """
        from src.agent.cognition.metacognition.consolidation.patterns import update_confidence

        pattern = {
            "id": "test-pattern",
            "confidence": 0.5,
            "evidence_count": 3,
            "last_observed": "2024-01-01"
        }

        update_confidence(pattern, validated=False)

        # Default decay is 0.1
        assert pattern["confidence"] == pytest.approx(0.4, abs=0.01)

    def test_confidence_capped_at_1(self):
        """Confidence should not exceed 1.0.

        Spec: Confidence is a probability, max is 1.0.
        """
        from src.agent.cognition.metacognition.consolidation.patterns import update_confidence

        pattern = {
            "id": "test-pattern",
            "confidence": 0.95,
            "evidence_count": 10,
            "last_observed": "2024-01-01"
        }

        update_confidence(pattern, validated=True)

        assert pattern["confidence"] <= 1.0

    def test_confidence_floored_at_0(self):
        """Confidence should not go below 0.0.

        Spec: Confidence is a probability, min is 0.0.
        """
        from src.agent.cognition.metacognition.consolidation.patterns import update_confidence

        pattern = {
            "id": "test-pattern",
            "confidence": 0.05,
            "evidence_count": 1,
            "last_observed": "2024-01-01"
        }

        update_confidence(pattern, validated=False)

        assert pattern["confidence"] >= 0.0


@pytest.mark.invariant
class TestPatternPromptIntegration:
    """Test pattern integration into agent prompts."""

    def test_chat_agent_uses_07_threshold(self, patch_data_dir):
        """Chat agent should use 0.7 threshold for user patterns.

        Spec: Pattern confidence > 0.7 for prompt inclusion.
        """
        from src.agent.agent import Agent
        from src.agent.cognition.metacognition.consolidation.patterns import (
            PatternStore, save_patterns
        )
        from unittest.mock import patch
        import json

        # Create user patterns directory and file
        user_patterns_dir = patch_data_dir / "agents" / "user" / "patterns"
        user_patterns_dir.mkdir(parents=True)

        # Create a pattern store with patterns at different confidence levels
        store = PatternStore()
        store.temporal = [
            {
                "id": "tmp-high",
                "description": "Morning routine at 8am",
                "granularity": "daily",
                "time_window": {"start": "08:00", "end": "09:00"},
                "confidence": 0.85,
                "evidence_count": 10,
                "first_observed": "2024-01-01",
                "last_observed": "2024-01-15"
            },
            {
                "id": "tmp-low",
                "description": "Evening pattern at 6pm",
                "granularity": "daily",
                "time_window": {"start": "18:00", "end": "19:00"},
                "confidence": 0.4,  # Below 0.7
                "evidence_count": 2,
                "first_observed": "2024-01-10",
                "last_observed": "2024-01-12"
            }
        ]

        # Save patterns
        with patch('src.agent.cognition.metacognition.consolidation.patterns.AGENTS_DIR',
                   patch_data_dir / "agents"):
            save_patterns("user", store)

        # Create chat agent
        chat_dir = patch_data_dir / "agents" / "chat"
        chat_dir.mkdir(parents=True)
        (chat_dir / "identity.md").write_text("Chat agent identity")

        with patch('src.agent.agent.AGENTS_DIR', patch_data_dir / "agents"):
            with patch('src.agent.cognition.metacognition.consolidation.patterns.AGENTS_DIR',
                       patch_data_dir / "agents"):
                agent = Agent("chat", config={
                    "id": "chat",
                    "name": "Chat",
                    "enabled": True,
                    "tools": [],
                    "triggers": []
                })

                prompt = agent._build_system_prompt()

                # High confidence pattern should be included
                assert "Morning routine" in prompt or "8am" in prompt or "85%" in prompt

                # Low confidence pattern should NOT be included
                # (It might appear if threshold is lower, so we check specifically)
                if "Evening pattern" in prompt:
                    # If it appears, it should only be because we're not filtering correctly
                    # This would be a bug
                    assert False, "Low confidence pattern should not appear in prompt"
