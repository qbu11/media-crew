"""Tests for Publish Pipeline — PublishLog creation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tastecraft.core.agent_loop import AgentResult


@pytest.fixture
def mock_agent_result_success():
    return AgentResult(
        success=True,
        output="Published successfully to xiaohongshu and wechat.",
        turns=3,
        tool_calls=4,
        elapsed_seconds=12.5,
        messages=[],
    )


@pytest.fixture
def mock_agent_result_failure():
    return AgentResult(
        success=False,
        output="Failed to publish: authentication error",
        turns=2,
        tool_calls=1,
        elapsed_seconds=5.0,
        messages=[],
    )


@pytest.fixture
def mock_content():
    content = MagicMock()
    content.id = 42
    content.title = "Test Content Title"
    content.body = "Test content body for publishing."
    content.metadata_json = {"hashtags": ["test", "ai"]}
    return content


@pytest.fixture
def mock_profile():
    profile = MagicMock()
    profile.platforms = {"xiaohongshu": {}, "wechat": {}}
    return profile


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.project_dir.return_value = "/tmp/test-project"
    settings.default_model = "claude-sonnet-4-20250514"
    settings.max_tokens = 4096
    settings.anthropic_api_key = "test-key"
    return settings


class TestPublishPipelinePublishLog:
    """Verify that _publish_one creates PublishLog records."""

    @pytest.mark.asyncio
    @patch("tastecraft.pipelines.publish.agent_loop")
    @patch("tastecraft.pipelines.publish.get_session")
    async def test_success_creates_publish_logs(
        self, mock_get_session, mock_agent_loop,
        mock_settings, mock_profile, mock_content, mock_agent_result_success,
    ):
        """On success, PublishLog rows are created for each platform."""
        mock_agent_loop.return_value = mock_agent_result_success

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_session

        from tastecraft.pipelines.publish import _publish_one

        with patch("tastecraft.pipelines.publish.build_pipeline_prompt", return_value="prompt"):
            result = await _publish_one(mock_settings, mock_profile, "test-project", mock_content)

        assert result["success"] is True
        assert result["platforms"] == ["xiaohongshu", "wechat"]
        # session.add should be called for each platform's PublishLog
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("tastecraft.pipelines.publish.agent_loop")
    @patch("tastecraft.pipelines.publish.get_session")
    async def test_failure_creates_failed_publish_log(
        self, mock_get_session, mock_agent_loop,
        mock_settings, mock_profile, mock_content, mock_agent_result_failure,
    ):
        """On failure, a single PublishLog with status='failed' is created."""
        mock_agent_loop.return_value = mock_agent_result_failure

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_session

        from tastecraft.pipelines.publish import _publish_one

        with patch("tastecraft.pipelines.publish.build_pipeline_prompt", return_value="prompt"):
            result = await _publish_one(mock_settings, mock_profile, "test-project", mock_content)

        assert result["success"] is False
        # On failure, platforms_published is empty, so ["unknown"] is used
        assert mock_session.add.call_count == 1

    @pytest.mark.asyncio
    @patch("tastecraft.pipelines.publish.agent_loop")
    @patch("tastecraft.pipelines.publish.get_session")
    async def test_publish_log_has_correct_content_id(
        self, mock_get_session, mock_agent_loop,
        mock_settings, mock_profile, mock_content, mock_agent_result_success,
    ):
        """PublishLog entries reference the correct content_id."""
        mock_agent_loop.return_value = mock_agent_result_success

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_session

        from tastecraft.pipelines.publish import _publish_one

        with patch("tastecraft.pipelines.publish.build_pipeline_prompt", return_value="prompt"):
            await _publish_one(mock_settings, mock_profile, "test-project", mock_content)

        # Check that all added PublishLog objects have content_id=42
        for call in mock_session.add.call_args_list:
            pub_log = call[0][0]
            assert pub_log.content_id == 42
            assert pub_log.status == "success"
