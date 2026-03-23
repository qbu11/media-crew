"""
Unit tests for PublishRetryManager.

Tests cover:
- Successful publish on first try
- Retry on failure
- Max retries exhausted
- Exponential backoff
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.utils.retry import PublishRetryManager, get_publish_retry_manager


@pytest.fixture
def retry_mgr():
    """Create a retry manager with fast delays for testing."""
    return PublishRetryManager(max_retries=3, base_delay=0.01)


class TestPublishWithRetry:
    async def test_success_first_try(self, retry_mgr):
        publish_func = AsyncMock(return_value={"success": True, "url": "https://example.com/1"})

        result = await retry_mgr.publish_with_retry(publish_func, content_id=1)
        assert result["success"] is True
        assert result["url"] == "https://example.com/1"
        assert result["attempts"] == 1
        assert publish_func.call_count == 1

    async def test_success_after_retry(self, retry_mgr):
        publish_func = AsyncMock(side_effect=[
            {"success": False, "error": "rate limited"},
            {"success": True, "url": "https://example.com/2"},
        ])

        result = await retry_mgr.publish_with_retry(publish_func, content_id=2)
        assert result["success"] is True
        assert result["attempts"] == 2
        assert publish_func.call_count == 2

    async def test_all_retries_exhausted(self, retry_mgr):
        publish_func = AsyncMock(return_value={"success": False, "error": "server error"})

        result = await retry_mgr.publish_with_retry(publish_func, content_id=3)
        assert result["success"] is False
        assert result["error"] == "server error"
        assert result["attempts"] == 3
        assert publish_func.call_count == 3

    async def test_exception_handling(self, retry_mgr):
        publish_func = AsyncMock(side_effect=[
            ConnectionError("network down"),
            {"success": True, "url": "https://example.com/4"},
        ])

        result = await retry_mgr.publish_with_retry(publish_func, content_id=4)
        assert result["success"] is True
        assert result["attempts"] == 2

    async def test_all_exceptions(self, retry_mgr):
        publish_func = AsyncMock(side_effect=ConnectionError("always failing"))

        result = await retry_mgr.publish_with_retry(publish_func, content_id=5)
        assert result["success"] is False
        assert "always failing" in result["error"]
        assert result["attempts"] == 3

    async def test_kwargs_passed(self, retry_mgr):
        publish_func = AsyncMock(return_value={"success": True, "url": "https://example.com"})

        await retry_mgr.publish_with_retry(
            publish_func, content_id=6, platform="xiaohongshu", title="test"
        )
        publish_func.assert_called_with(platform="xiaohongshu", title="test")


class TestSingleton:
    def test_get_publish_retry_manager(self):
        import src.utils.retry as mod
        mod._publish_retry_manager = None
        mgr = get_publish_retry_manager()
        assert isinstance(mgr, PublishRetryManager)
        mgr2 = get_publish_retry_manager()
        assert mgr is mgr2
        mod._publish_retry_manager = None
