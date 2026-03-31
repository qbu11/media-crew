"""
Unit tests for Bilibili platform tool.

Tests cover:
- BilibiliTool: init, authenticate(), publish(), get_analytics(), schedule()
- publish_with_category()
- Validation: non-video content, missing video file
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
from src.tools.platform.bilibili import BilibiliTool


class TestBilibiliToolInit:
    """Tests for BilibiliTool initialization."""

    def test_default_init(self):
        tool = BilibiliTool()
        assert tool.name == "bilibili_publisher"
        assert tool.platform == "bilibili"
        assert tool.version == "0.1.0"
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED

    def test_platform_constraints(self):
        tool = BilibiliTool()
        assert tool.max_title_length == 80
        assert tool.max_body_length == 2000
        assert tool.max_images == 1
        assert tool.max_tags == 12

    def test_supported_content_types(self):
        tool = BilibiliTool()
        assert tool.supported_content_types == [ContentType.VIDEO]
        assert ContentType.TEXT not in tool.supported_content_types
        assert ContentType.IMAGE not in tool.supported_content_types

    def test_rate_limits(self):
        tool = BilibiliTool()
        assert tool.max_requests_per_minute == 2
        assert tool.min_interval_seconds == 60.0

    def test_urls(self):
        tool = BilibiliTool()
        assert "member.bilibili.com" in tool.upload_url
        assert tool.home_url == "https://www.bilibili.com"


class TestBilibiliAuthenticate:
    """Tests for BilibiliTool.authenticate()."""

    def test_authenticate_success(self):
        tool = BilibiliTool()
        result = tool.authenticate()
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED
        assert result.platform == "bilibili"


class TestBilibiliPublish:
    """Tests for BilibiliTool.publish()."""

    def test_publish_video_success(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Test Video",
            body="Video description",
            content_type=ContentType.VIDEO,
            video="/path/to/video.mp4",
            tags=["gaming", "tutorial"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.platform == "bilibili"
        assert result.content_id is not None
        assert result.content_url is not None
        assert result.published_at is not None
        assert result.data["title"] == "Test Video"
        assert result.data["tags"] == ["gaming", "tutorial"]

    def test_publish_non_video_fails(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Text post",
            body="Body",
            content_type=ContentType.TEXT,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "only supports video" in result.error.lower()

    def test_publish_image_type_fails(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Image",
            body="Body",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        result = tool.publish(content)
        assert result.is_failed()

    def test_publish_no_video_file_fails(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="No video",
            body="Body",
            content_type=ContentType.VIDEO,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Video file path required" in result.error

    def test_publish_title_too_long(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="x" * 81,
            body="Body",
            content_type=ContentType.VIDEO,
            video="/path/to/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_publish_body_too_long(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="T",
            body="x" * 2001,
            content_type=ContentType.VIDEO,
            video="/path/to/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_tags(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
            video="/path/to/video.mp4",
            tags=[f"tag{i}" for i in range(13)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many tags" in result.error

    def test_publish_auto_authenticates(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
            video="/path.mp4",
        )
        result = tool.publish(content)
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED

    def test_publish_with_cover_and_custom_fields(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Custom",
            body="Description",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
            cover_image="cover.jpg",
            custom_fields={"category": "gaming"},
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.data["category"] == "gaming"


class TestBilibiliPublishWithCategory:
    """Tests for BilibiliTool.publish_with_category()."""

    def test_publish_with_category_success(self):
        tool = BilibiliTool()
        result = tool.publish_with_category(
            title="Gaming Video",
            video_path="/path/to/video.mp4",
            description="A cool gaming video",
            tags=["gaming", "fps"],
            category="gaming",
        )
        assert result.is_success()

    def test_publish_with_category_defaults(self):
        tool = BilibiliTool()
        result = tool.publish_with_category(
            title="Video",
            video_path="/video.mp4",
        )
        assert result.is_success()

    def test_publish_with_category_as_draft(self):
        tool = BilibiliTool()
        result = tool.publish_with_category(
            title="Draft Video",
            video_path="/video.mp4",
            draft=True,
        )
        assert result.is_success()


class TestBilibiliGetAnalytics:
    """Tests for BilibiliTool.get_analytics()."""

    def test_get_analytics(self):
        tool = BilibiliTool()
        analytics = tool.get_analytics("bv_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "bv_123"
        assert analytics.views == 0
        assert analytics.favorites == 0


class TestBilibiliSchedule:
    """Tests for BilibiliTool.schedule()."""

    def test_schedule_future_time(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Scheduled",
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        future = datetime.now() + timedelta(hours=2)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "scheduled_for" in result.data

    def test_schedule_past_time_fails(self):
        tool = BilibiliTool()
        content = PublishContent(
            title="Past",
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        past = datetime.now() - timedelta(hours=1)
        result = tool.schedule(content, past)
        assert result.is_failed()
        assert "future" in result.error.lower()


class TestBilibiliGetConstraints:
    """Tests for BilibiliTool.get_constraints()."""

    def test_get_constraints(self):
        tool = BilibiliTool()
        c = tool.get_constraints()
        assert c["platform"] == "bilibili"
        assert c["max_title_length"] == 80
        assert c["max_body_length"] == 2000
        assert c["max_images"] == 1
        assert c["max_tags"] == 12
        assert c["supported_content_types"] == ["video"]
