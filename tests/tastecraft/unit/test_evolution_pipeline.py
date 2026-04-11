"""Tests for Evolution Pipeline — TasteProfile.learned compatibility."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tastecraft.core.agent_loop import AgentResult
from tastecraft.pipelines.evolution import EXPLICIT_FIELDS, _evolve
from tastecraft.taste.profile import TasteProfile


@pytest.fixture
def mock_profile(tmp_path):
    """Create a real TasteProfile with learned dict."""
    profile = TasteProfile(
        project="test-project",
        identity="AI startup founder",
        tone="professional",
        audience="tech enthusiasts",
    )
    profile.learned = {
        "preferred_length": "medium",
        "hook_style": "question",
        "_confidence": 0.6,
        "_generation_count": 10,
    }
    profile.confidence = 0.6
    return profile


@pytest.fixture
def mock_settings(tmp_path):
    settings = MagicMock()
    settings.project_dir.return_value = tmp_path
    settings.default_model = "claude-sonnet-4-20250514"
    settings.max_tokens = 4096
    settings.anthropic_api_key = "test-key"
    return settings


class TestEvolutionExplicitFields:
    """Verify EXPLICIT_FIELDS guard prevents modifying explicit dimensions."""

    def test_explicit_fields_contains_core_dimensions(self):
        assert "identity" in EXPLICIT_FIELDS
        assert "tone" in EXPLICIT_FIELDS
        assert "audience" in EXPLICIT_FIELDS
        assert "taboos" in EXPLICIT_FIELDS
        assert "catchphrases" in EXPLICIT_FIELDS
        assert "content_goal" in EXPLICIT_FIELDS

    def test_learned_dimensions_not_in_explicit(self):
        assert "preferred_length" not in EXPLICIT_FIELDS
        assert "hook_style" not in EXPLICIT_FIELDS


class TestEvolutionProfileCompat:
    """Verify evolution uses profile.learned, not profile.implicit."""

    def test_profile_has_learned_not_implicit(self):
        """TasteProfile has .learned but not .implicit."""
        profile = TasteProfile()
        assert hasattr(profile, "learned")
        assert not hasattr(profile, "implicit")
        assert not hasattr(profile, "explicit")

    @pytest.mark.asyncio
    @patch("tastecraft.pipelines.evolution.agent_loop")
    @patch("tastecraft.pipelines.evolution.get_session")
    async def test_evolve_updates_learned_dict(
        self, mock_get_session, mock_agent_loop, mock_settings, mock_profile, tmp_path,
    ):
        """_evolve() writes changes to profile.learned."""
        evolution_output = json.dumps({
            "changes": [
                {
                    "dimension": "emoji_density",
                    "old_value": None,
                    "new_value": "moderate",
                    "confidence": 0.7,
                }
            ],
            "confidence_delta": 0.05,
        })
        mock_agent_loop.return_value = AgentResult(
            success=True,
            output=f"```json\n{evolution_output}\n```",
            turns=2,
            tool_calls=0,
            elapsed_seconds=5.0,
            messages=[],
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_session

        signals = {"edit_diffs": [], "performance": [], "trending": []}

        with (
            patch("tastecraft.pipelines.evolution.build_pipeline_prompt", return_value="prompt"),
            patch.object(mock_profile, "save_learned"),
        ):
            result = await _evolve(mock_settings, "test-project", mock_profile, signals, "weekly")

        assert result["changed"] is True
        assert "emoji_density" in result["changes"]
        assert mock_profile.learned["emoji_density"] == "moderate"

    @pytest.mark.asyncio
    @patch("tastecraft.pipelines.evolution.agent_loop")
    @patch("tastecraft.pipelines.evolution.get_session")
    async def test_evolve_blocks_explicit_dimension_changes(
        self, mock_get_session, mock_agent_loop, mock_settings, mock_profile, tmp_path,
    ):
        """_evolve() refuses to modify explicit dimensions like 'identity'."""
        evolution_output = json.dumps({
            "changes": [
                {
                    "dimension": "identity",
                    "old_value": "AI startup founder",
                    "new_value": "crypto bro",
                    "confidence": 0.9,
                }
            ],
            "confidence_delta": 0.0,
        })
        mock_agent_loop.return_value = AgentResult(
            success=True,
            output=f"```json\n{evolution_output}\n```",
            turns=2,
            tool_calls=0,
            elapsed_seconds=3.0,
            messages=[],
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_session

        signals = {"edit_diffs": [], "performance": [], "trending": []}

        with (
            patch("tastecraft.pipelines.evolution.build_pipeline_prompt", return_value="prompt"),
            patch.object(mock_profile, "save_learned"),
        ):
            result = await _evolve(mock_settings, "test-project", mock_profile, signals, "weekly")

        # identity should NOT be changed
        assert result["changed"] is False
        assert "identity" not in mock_profile.learned
