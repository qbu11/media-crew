"""
Unit tests for PublishEngineV2.

Tests platform publishers (Xiaohongshu, Weibo, Zhihu) and the unified publish interface.
No real Chrome MCP calls -- exercises validation, rate-limiting, and routing logic.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.services.publish_engine_v2 import (
    ChromeMCPPublisher,
    PublishEngineV2,
    WeiboPublisher,
    XiaohongshuPublisher,
    ZhihuPublisher,
    get_publish_engine_v2,
)


# ---------------------------------------------------------------------------
# ChromeMCPPublisher (base class)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChromeMCPPublisher:
    """Tests for the base ChromeMCPPublisher."""

    async def test_check_rate_limit_no_previous_publish(self):
        publisher = ChromeMCPPublisher()
        can, wait = await publisher.check_rate_limit("weibo", min_interval=60)

        assert can is True
        assert wait == 0.0

    async def test_check_rate_limit_under_interval(self):
        publisher = ChromeMCPPublisher()
        publisher.last_publish_time["weibo"] = datetime.now()

        can, wait = await publisher.check_rate_limit("weibo", min_interval=60)

        assert can is False
        assert wait > 0

    async def test_check_rate_limit_over_interval(self):
        publisher = ChromeMCPPublisher()
        publisher.last_publish_time["weibo"] = datetime.now() - timedelta(seconds=120)

        can, wait = await publisher.check_rate_limit("weibo", min_interval=60)

        assert can is True
        assert wait == 0.0

    def test_update_publish_time(self):
        publisher = ChromeMCPPublisher()

        assert "weibo" not in publisher.last_publish_time
        publisher.update_publish_time("weibo")
        assert "weibo" in publisher.last_publish_time
        assert isinstance(publisher.last_publish_time["weibo"], datetime)


# ---------------------------------------------------------------------------
# XiaohongshuPublisher
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestXiaohongshuPublisher:
    """Tests for XiaohongshuPublisher.publish validation paths."""

    async def test_publish_success(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="Short title",
            body="Body text",
            images=["img1.jpg"],
            tags=["#tag1"],
        )

        assert result.success is True
        data = result.data
        assert data["pending"] is True
        assert data["platform"] == "xiaohongshu"
        assert data["data"]["title"] == "Short title"

    async def test_title_too_long(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="A" * 21,  # > 20 chars
            body="Body",
            images=["img.jpg"],
        )

        assert result.success is False
        assert result.error_code == "XHS_TITLE_TOO_LONG"

    async def test_body_too_long(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="OK",
            body="A" * 1001,  # > 1000 chars
            images=["img.jpg"],
        )

        assert result.success is False
        assert result.error_code == "XHS_BODY_TOO_LONG"

    async def test_no_images(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(title="OK", body="Body", images=[])

        assert result.success is False
        assert result.error_code == "XHS_INVALID_IMAGE_COUNT"

    async def test_too_many_images(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="OK",
            body="Body",
            images=[f"img{i}.jpg" for i in range(19)],  # > 18
        )

        assert result.success is False
        assert result.error_code == "XHS_INVALID_IMAGE_COUNT"

    async def test_too_many_tags(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="OK",
            body="Body",
            images=["img.jpg"],
            tags=[f"#tag{i}" for i in range(11)],  # > 10
        )

        assert result.success is False
        assert result.error_code == "XHS_TOO_MANY_TAGS"

    async def test_rate_limited(self):
        pub = XiaohongshuPublisher()
        pub.last_publish_time["xiaohongshu"] = datetime.now()

        result = await pub.publish(
            title="OK", body="Body", images=["img.jpg"]
        )

        assert result.success is False
        assert result.error_code == "PUBLISH_RATE_LIMIT"

    async def test_publish_with_location(self):
        pub = XiaohongshuPublisher()
        result = await pub.publish(
            title="Title",
            body="Body",
            images=["img.jpg"],
            location="Beijing",
        )

        assert result.success is True
        assert result.data["data"]["location"] == "Beijing"


# ---------------------------------------------------------------------------
# WeiboPublisher
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWeiboPublisher:
    """Tests for WeiboPublisher.publish validation paths."""

    async def test_publish_success(self):
        pub = WeiboPublisher()
        result = await pub.publish(body="Hello Weibo")

        assert result.success is True
        assert result.data["platform"] == "weibo"

    async def test_publish_with_images(self):
        pub = WeiboPublisher()
        result = await pub.publish(
            body="With images",
            images=["img1.jpg", "img2.jpg"],
        )

        assert result.success is True
        assert len(result.data["data"]["images"]) == 2

    async def test_body_too_long(self):
        pub = WeiboPublisher()
        result = await pub.publish(body="A" * 2001)

        assert result.success is False
        assert result.error_code == "WEIBO_BODY_TOO_LONG"

    async def test_too_many_images(self):
        pub = WeiboPublisher()
        result = await pub.publish(
            body="OK",
            images=[f"img{i}.jpg" for i in range(10)],  # > 9
        )

        assert result.success is False
        assert result.error_code == "WEIBO_TOO_MANY_IMAGES"

    async def test_rate_limited(self):
        pub = WeiboPublisher()
        pub.last_publish_time["weibo"] = datetime.now()

        result = await pub.publish(body="Hello")

        assert result.success is False
        assert result.error_code == "PUBLISH_RATE_LIMIT"


# ---------------------------------------------------------------------------
# ZhihuPublisher
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestZhihuPublisher:
    """Tests for ZhihuPublisher.publish_article validation paths."""

    async def test_publish_article_success(self):
        pub = ZhihuPublisher()
        result = await pub.publish_article(
            title="Article Title",
            body="# Markdown\n\nContent here.",
            tags=["AI"],
        )

        assert result.success is True
        assert result.data["platform"] == "zhihu"
        assert result.data["content_type"] == "article"

    async def test_publish_article_rate_limited(self):
        pub = ZhihuPublisher()
        pub.last_publish_time["zhihu"] = datetime.now()

        result = await pub.publish_article(title="T", body="B")

        assert result.success is False
        assert result.error_code == "PUBLISH_RATE_LIMIT"


# ---------------------------------------------------------------------------
# PublishEngineV2 (unified interface)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublishEngineV2:
    """Tests for the unified PublishEngineV2.publish method."""

    async def test_unsupported_platform(self):
        engine = PublishEngineV2()
        result = await engine.publish(
            platform="tiktok",
            account=None,
            content={"body": "test"},
        )

        assert result.success is False
        assert result.error_code == "UNSUPPORTED_PLATFORM"

    async def test_publish_xiaohongshu_routes_correctly(self):
        engine = PublishEngineV2()
        result = await engine.publish(
            platform="xiaohongshu",
            account=None,
            content={
                "title": "XHS Title",
                "body": "Body",
                "images": ["img.jpg"],
                "tags": ["#tag"],
            },
        )

        assert result.success is True
        assert result.data["platform"] == "xiaohongshu"

    async def test_publish_weibo_routes_correctly(self):
        engine = PublishEngineV2()
        result = await engine.publish(
            platform="weibo",
            account=None,
            content={"body": "Weibo post", "images": []},
        )

        assert result.success is True
        assert result.data["platform"] == "weibo"

    async def test_publish_zhihu_article_routes_correctly(self):
        engine = PublishEngineV2()
        result = await engine.publish(
            platform="zhihu",
            account=None,
            content={
                "title": "Article",
                "body": "Body",
                "tags": [],
                "content_type": "article",
            },
        )

        assert result.success is True
        assert result.data["platform"] == "zhihu"

    async def test_publish_zhihu_unsupported_content_type(self):
        engine = PublishEngineV2()
        result = await engine.publish(
            platform="zhihu",
            account=None,
            content={"body": "Body", "content_type": "answer"},
        )

        assert result.success is False
        assert result.error_code == "UNSUPPORTED_CONTENT_TYPE"

    async def test_publish_catches_exception(self):
        """If the publisher raises, the engine should catch and return Error."""
        engine = PublishEngineV2()
        engine.xiaohongshu.publish = AsyncMock(side_effect=RuntimeError("boom"))

        result = await engine.publish(
            platform="xiaohongshu",
            account=None,
            content={
                "title": "T",
                "body": "B",
                "images": ["img.jpg"],
            },
        )

        assert result.success is False
        assert result.error_code == "PUBLISH_ERROR"

    def test_init_creates_publishers(self):
        engine = PublishEngineV2()

        assert isinstance(engine.xiaohongshu, XiaohongshuPublisher)
        assert isinstance(engine.weibo, WeiboPublisher)
        assert isinstance(engine.zhihu, ZhihuPublisher)
        assert "xiaohongshu" in engine.PLATFORMS
        assert "weibo" in engine.PLATFORMS
        assert "zhihu" in engine.PLATFORMS


# ---------------------------------------------------------------------------
# get_publish_engine_v2 singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetPublishEngineV2:
    """Tests for the module-level singleton accessor."""

    def test_returns_publish_engine_v2(self):
        import src.services.publish_engine_v2 as mod

        # Reset the singleton
        mod._publish_engine = None
        engine = mod.get_publish_engine_v2()

        assert isinstance(engine, PublishEngineV2)

    def test_returns_same_instance(self):
        import src.services.publish_engine_v2 as mod

        mod._publish_engine = None
        e1 = mod.get_publish_engine_v2()
        e2 = mod.get_publish_engine_v2()

        assert e1 is e2
