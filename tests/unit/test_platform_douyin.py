"""
Unit tests for Douyin platform tool.

Tests cover:
- DouyinTool: init, authenticate(), publish(), get_analytics(), schedule()
- _format_description()
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
from src.tools.platform.douyin import DouyinTool


class TestDouyinToolInit:
    """Tests for DouyinTool initialization."""

    def test_default_init(self):
        tool = DouyinTool()
        assert tool.name == "douyin_publisher"
        assert tool.platform == "douyin"
        assert tool.version == "0.1.0"
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED

    def test_platform_constraints(self):
        tool = DouyinTool()
        assert tool.max_title_length == 100
        assert tool.max_body_length == 500
        assert tool.max_images == 0
        assert tool.max_tags == 5

    def test_supported_content_types(self):
        tool = DouyinTool()
        assert tool.supported_content_types == [ContentType.VIDEO]
        assert ContentType.TEXT not in tool.supported_content_types

    def test_rate_limits(self):
        tool = DouyinTool()
        assert tool.max_requests_per_minute == 1
        assert tool.min_interval_seconds == 300.0

    def test_urls(self):
        tool = DouyinTool()
        assert "creator.douyin.com" in tool.creator_url
        assert tool.home_url == "https://www.douyin.com"


class TestDouyinAuthenticate:
    """Tests for DouyinTool.authenticate()."""

    def test_authenticate_success(self):
        tool = DouyinTool()
        result = tool.authenticate()
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED
        assert result.platform == "douyin"


class TestDouyinPublish:
    """Tests for DouyinTool.publish()."""

    def test_publish_video_success(self):
        tool = DouyinTool()
        content = PublishContent(
            title="Dance Video",
            body="Check out this dance!",
            content_type=ContentType.VIDEO,
            video="/path/to/video.mp4",
            tags=["dance", "fun"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.platform == "douyin"
        assert result.content_id is not None
        assert result.content_url is not None
        assert result.published_at is not None
        assert result.data["tags"] == ["dance", "fun"]

    def test_publish_non_video_fails(self):
        tool = DouyinTool()
        content = PublishContent(
            title="Text post",
            body="Body",
            content_type=ContentType.TEXT,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "only supports video" in result.error.lower()

    def test_publish_image_type_fails(self):
        tool = DouyinTool()
        content = PublishContent(
            title="Image",
            body="Body",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        result = tool.publish(content)
        assert result.is_failed()

    def test_publish_no_video_file_fails(self):
        tool = DouyinTool()
        content = PublishContent(
            title="No video",
            body="Body",
            content_type=ContentType.VIDEO,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Video file path required" in result.error

    def test_publish_title_too_long(self):
        tool = DouyinTool()
        content = PublishContent(
            title="x" * 101,
            body="Body",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_publish_body_too_long(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="x" * 501,
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_tags(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
            tags=[f"tag{i}" for i in range(6)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many tags" in result.error

    def test_publish_auto_authenticates(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED

    def test_publish_already_authenticated(self):
        tool = DouyinTool()
        tool._auth_status = AuthStatus.AUTHENTICATED
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        result = tool.publish(content)
        assert result.is_success()


class TestDouyinFormatDescription:
    """Tests for DouyinTool._format_description()."""

    def test_format_with_tags(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="My video",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
            tags=["dance", "fun"],
        )
        desc = tool._format_description(content)
        assert "My video" in desc
        assert "#dance" in desc
        assert "#fun" in desc

    def test_format_with_topics(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="My video",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
            topics=["user1", "user2"],
        )
        desc = tool._format_description(content)
        assert "@user1" in desc
        assert "@user2" in desc

    def test_format_with_tags_and_topics(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="Body",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
            tags=["tag1"],
            topics=["person1"],
        )
        desc = tool._format_description(content)
        assert "#tag1" in desc
        assert "@person1" in desc
        assert "Body" in desc

    def test_format_no_tags_no_topics(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="Just body",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        desc = tool._format_description(content)
        assert desc == "Just body"


class TestDouyinGetAnalytics:
    """Tests for DouyinTool.get_analytics()."""

    def test_get_analytics(self):
        tool = DouyinTool()
        analytics = tool.get_analytics("douyin_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "douyin_123"
        assert analytics.views == 0
        assert analytics.favorites == 0


class TestDouyinSchedule:
    """Tests for DouyinTool.schedule()."""

    def test_schedule_future_time(self):
        tool = DouyinTool()
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
        tool = DouyinTool()
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

    def test_schedule_validates_content(self):
        tool = DouyinTool()
        content = PublishContent(
            title="x" * 101,
            body="B",
            content_type=ContentType.VIDEO,
            video="/video.mp4",
        )
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_schedule_validates_content_type(self):
        tool = DouyinTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.TEXT,
        )
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "not supported" in result.error


class TestDouyinGetConstraints:
    """Tests for DouyinTool.get_constraints()."""

    def test_get_constraints(self):
        tool = DouyinTool()
        c = tool.get_constraints()
        assert c["platform"] == "douyin"
        assert c["max_title_length"] == 100
        assert c["max_body_length"] == 500
        assert c["max_images"] == 0
        assert c["max_tags"] == 5
        assert c["supported_content_types"] == ["video"]
