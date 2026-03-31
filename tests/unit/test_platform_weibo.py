"""
Unit tests for Weibo platform tool.

Tests cover:
- WeiboTool: init, authenticate(), publish(), get_analytics(), schedule()
- publish_article(), repost(), _format_content()
- Validation edge cases
"""

from datetime import datetime, timedelta

import pytest

from src.tools.base_tool import ToolStatus
from src.tools.platform.base import (
    AnalyticsData,
    AuthStatus,
    ContentType,
    PublishContent,
    PublishResult,
)
from src.tools.platform.weibo import WeiboTool


class TestWeiboToolInit:
    """Tests for WeiboTool initialization."""

    def test_default_init(self):
        tool = WeiboTool()
        assert tool.name == "weibo_publisher"
        assert tool.platform == "weibo"
        assert tool.version == "0.1.0"
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED

    def test_platform_constraints(self):
        tool = WeiboTool()
        assert tool.max_title_length == 2000
        assert tool.max_body_length == 2000
        assert tool.max_images == 9
        assert tool.max_tags == 10

    def test_supported_content_types(self):
        tool = WeiboTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.ARTICLE in tool.supported_content_types
        assert ContentType.VIDEO not in tool.supported_content_types

    def test_rate_limits(self):
        tool = WeiboTool()
        assert tool.max_requests_per_minute == 5
        assert tool.min_interval_seconds == 10.0

    def test_urls(self):
        tool = WeiboTool()
        assert tool.home_url == "https://weibo.com"
        assert tool.article_url == "https://weibo.com/article/publish"


class TestWeiboAuthenticate:
    """Tests for WeiboTool.authenticate()."""

    def test_authenticate_success(self):
        tool = WeiboTool()
        result = tool.authenticate()
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED
        assert result.platform == "weibo"

    def test_authenticate_sets_status(self):
        tool = WeiboTool()
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED
        tool.authenticate()
        assert tool._auth_status == AuthStatus.AUTHENTICATED


class TestWeiboPublish:
    """Tests for WeiboTool.publish()."""

    def test_publish_text_success(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="Hello Weibo!",
            content_type=ContentType.TEXT,
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.platform == "weibo"
        assert result.content_id is not None
        assert result.content_url is not None
        assert result.published_at is not None

    def test_publish_image_success(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="Image post",
            content_type=ContentType.IMAGE,
            images=["img1.jpg", "img2.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.data["images_count"] == 2

    def test_publish_with_tags(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="Tagged post",
            content_type=ContentType.TEXT,
            tags=["AI", "tech"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.data["topics"] == ["AI", "tech"]

    def test_publish_unsupported_content_type(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="Video post",
            content_type=ContentType.VIDEO,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error

    def test_publish_body_too_long(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="x" * 2001,
            content_type=ContentType.TEXT,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_images(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="B",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(10)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_too_many_tags(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="B",
            content_type=ContentType.TEXT,
            tags=[f"tag{i}" for i in range(11)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many tags" in result.error

    def test_publish_auto_authenticates(self):
        tool = WeiboTool()
        content = PublishContent(title="", body="B", content_type=ContentType.TEXT)
        result = tool.publish(content)
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED

    def test_publish_already_authenticated(self):
        tool = WeiboTool()
        tool._auth_status = AuthStatus.AUTHENTICATED
        content = PublishContent(title="", body="B", content_type=ContentType.TEXT)
        result = tool.publish(content)
        assert result.is_success()


class TestWeiboPublishArticle:
    """Tests for WeiboTool.publish_article()."""

    def test_publish_article_success(self):
        tool = WeiboTool()
        result = tool.publish_article(title="Article Title", content="Article body content")
        assert result.is_success()

    def test_publish_article_with_cover(self):
        tool = WeiboTool()
        result = tool.publish_article(
            title="Title",
            content="Body",
            cover_image="cover.jpg",
        )
        assert result.is_success()


class TestWeiboRepost:
    """Tests for WeiboTool.repost()."""

    def test_repost_success(self):
        tool = WeiboTool()
        result = tool.repost("https://weibo.com/123456")
        assert result.is_success()
        assert result.data["type"] == "repost"
        assert result.data["original_url"] == "https://weibo.com/123456"

    def test_repost_with_comment(self):
        tool = WeiboTool()
        result = tool.repost("https://weibo.com/123456", comment="Great post!")
        assert result.is_success()
        assert result.data["comment"] == "Great post!"


class TestWeiboFormatContent:
    """Tests for WeiboTool._format_content()."""

    def test_format_with_tags(self):
        tool = WeiboTool()
        content = PublishContent(
            title="",
            body="Hello",
            content_type=ContentType.TEXT,
            tags=["AI", "tech"],
        )
        formatted = tool._format_content(content)
        assert "#AI#" in formatted
        assert "#tech#" in formatted
        assert "Hello" in formatted

    def test_format_without_tags(self):
        tool = WeiboTool()
        content = PublishContent(title="", body="Plain text", content_type=ContentType.TEXT)
        formatted = tool._format_content(content)
        assert formatted == "Plain text"


class TestWeiboGetAnalytics:
    """Tests for WeiboTool.get_analytics()."""

    def test_get_analytics(self):
        tool = WeiboTool()
        analytics = tool.get_analytics("weibo_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "weibo_123"
        assert analytics.views == 0


class TestWeiboSchedule:
    """Tests for WeiboTool.schedule()."""

    def test_schedule_past_time_fails(self):
        tool = WeiboTool()
        content = PublishContent(title="", body="B", content_type=ContentType.TEXT)
        past = datetime.now() - timedelta(hours=1)
        result = tool.schedule(content, past)
        assert result.is_failed()
        assert "future" in result.error.lower()

    def test_schedule_future_time_not_supported(self):
        tool = WeiboTool()
        content = PublishContent(title="", body="B", content_type=ContentType.TEXT)
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        # Weibo scheduling returns failure (not supported)
        assert result.is_failed()
        assert "not supported" in result.error.lower() or "scheduler" in result.error.lower()


class TestWeiboGetConstraints:
    """Tests for WeiboTool.get_constraints()."""

    def test_get_constraints(self):
        tool = WeiboTool()
        c = tool.get_constraints()
        assert c["platform"] == "weibo"
        assert c["max_title_length"] == 2000
        assert c["max_body_length"] == 2000
        assert c["max_images"] == 9
        assert c["max_tags"] == 10
        assert "text" in c["supported_content_types"]
        assert "image" in c["supported_content_types"]
        assert "article" in c["supported_content_types"]
