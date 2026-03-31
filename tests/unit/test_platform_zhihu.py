"""
Unit tests for Zhihu platform tool.

Tests cover:
- ZhihuTool: init, authenticate(), publish(), get_analytics(), schedule()
- publish_answer(), publish_article(), publish_thought()
- Validation: short answer, short article
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
from src.tools.platform.zhihu import ZhihuTool


class TestZhihuToolInit:
    """Tests for ZhihuTool initialization."""

    def test_default_init(self):
        tool = ZhihuTool()
        assert tool.name == "zhihu_publisher"
        assert tool.platform == "zhihu"
        assert tool.version == "0.1.0"
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED

    def test_platform_constraints(self):
        tool = ZhihuTool()
        assert tool.max_title_length == 100
        assert tool.max_body_length == 10000
        assert tool.max_images == 20
        assert tool.max_tags == 5

    def test_supported_content_types(self):
        tool = ZhihuTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.ARTICLE in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.VIDEO not in tool.supported_content_types

    def test_rate_limits(self):
        tool = ZhihuTool()
        assert tool.max_requests_per_minute == 2
        assert tool.min_interval_seconds == 30.0

    def test_urls(self):
        tool = ZhihuTool()
        assert tool.home_url == "https://www.zhihu.com"
        assert tool.article_write_url == "https://zhuanlan.zhihu.com/write"


class TestZhihuAuthenticate:
    """Tests for ZhihuTool.authenticate()."""

    def test_authenticate_success(self):
        tool = ZhihuTool()
        result = tool.authenticate()
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED
        assert result.platform == "zhihu"


class TestZhihuPublish:
    """Tests for ZhihuTool.publish() - delegates to publish_article."""

    def test_publish_delegates_to_article(self):
        tool = ZhihuTool()
        content = PublishContent(
            title="Test Article",
            body="x" * 500,
            content_type=ContentType.ARTICLE,
            images=["img.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.data["type"] == "article"

    def test_publish_short_body_fails(self):
        tool = ZhihuTool()
        content = PublishContent(
            title="Short",
            body="Too short",
            content_type=ContentType.TEXT,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "too short" in result.error.lower() or "minimum" in result.error.lower()


class TestZhihuPublishAnswer:
    """Tests for ZhihuTool.publish_answer()."""

    def test_publish_answer_success(self):
        tool = ZhihuTool()
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="x" * 100,
        )
        assert result.is_success()
        assert result.data["type"] == "answer"
        assert result.data["question_url"] == "https://www.zhihu.com/question/12345"
        assert result.data["length"] == 100

    def test_publish_answer_too_short(self):
        tool = ZhihuTool()
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="too short",
        )
        assert result.is_failed()
        assert "too short" in result.error.lower() or "minimum" in result.error.lower()

    def test_publish_answer_exact_minimum(self):
        tool = ZhihuTool()
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="x" * 100,
        )
        assert result.is_success()

    def test_publish_answer_auto_authenticates(self):
        tool = ZhihuTool()
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="x" * 100,
        )
        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED

    def test_publish_answer_already_authenticated(self):
        tool = ZhihuTool()
        tool._auth_status = AuthStatus.AUTHENTICATED
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="x" * 100,
        )
        assert result.is_success()

    def test_publish_answer_with_question_id(self):
        tool = ZhihuTool()
        result = tool.publish_answer(
            question_url="https://www.zhihu.com/question/12345",
            answer="x" * 100,
            question_id="12345",
        )
        assert result.is_success()


class TestZhihuPublishArticle:
    """Tests for ZhihuTool.publish_article()."""

    def test_publish_article_success(self):
        tool = ZhihuTool()
        result = tool.publish_article(
            title="Article Title",
            content="x" * 500,
        )
        assert result.is_success()
        assert result.data["type"] == "article"
        assert result.data["title"] == "Article Title"
        assert result.content_url is not None

    def test_publish_article_with_images(self):
        tool = ZhihuTool()
        result = tool.publish_article(
            title="With Images",
            content="x" * 500,
            images=["img1.jpg", "img2.jpg"],
        )
        assert result.is_success()
        assert result.data["images_count"] == 2

    def test_publish_article_too_short(self):
        tool = ZhihuTool()
        result = tool.publish_article(
            title="Short",
            content="too short",
        )
        assert result.is_failed()
        assert "too short" in result.error.lower() or "minimum" in result.error.lower()

    def test_publish_article_exact_minimum(self):
        tool = ZhihuTool()
        result = tool.publish_article(
            title="Exact min",
            content="x" * 500,
        )
        assert result.is_success()

    def test_publish_article_auto_authenticates(self):
        tool = ZhihuTool()
        result = tool.publish_article(title="T", content="x" * 500)
        assert tool._auth_status == AuthStatus.AUTHENTICATED

    def test_publish_article_no_images(self):
        tool = ZhihuTool()
        result = tool.publish_article(title="T", content="x" * 500)
        assert result.data["images_count"] == 0


class TestZhihuPublishThought:
    """Tests for ZhihuTool.publish_thought()."""

    def test_publish_thought_success(self):
        tool = ZhihuTool()
        result = tool.publish_thought("This is a thought")
        assert result.is_success()
        assert result.data["type"] == "thought"

    def test_publish_thought_with_images(self):
        tool = ZhihuTool()
        result = tool.publish_thought("Thought with images", images=["img.jpg"])
        assert result.is_success()
        assert result.data["images_count"] == 1

    def test_publish_thought_no_images(self):
        tool = ZhihuTool()
        result = tool.publish_thought("Bare thought")
        assert result.data["images_count"] == 0

    def test_publish_thought_auto_authenticates(self):
        tool = ZhihuTool()
        result = tool.publish_thought("Test")
        assert tool._auth_status == AuthStatus.AUTHENTICATED


class TestZhihuGetAnalytics:
    """Tests for ZhihuTool.get_analytics()."""

    def test_get_analytics(self):
        tool = ZhihuTool()
        analytics = tool.get_analytics("zhihu_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "zhihu_123"
        assert analytics.views == 0


class TestZhihuSchedule:
    """Tests for ZhihuTool.schedule()."""

    def test_schedule_not_supported(self):
        tool = ZhihuTool()
        content = PublishContent(title="T", body="B", content_type=ContentType.TEXT)
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "not supported" in result.error.lower() or "scheduler" in result.error.lower()


class TestZhihuGetConstraints:
    """Tests for ZhihuTool.get_constraints()."""

    def test_get_constraints(self):
        tool = ZhihuTool()
        c = tool.get_constraints()
        assert c["platform"] == "zhihu"
        assert c["max_title_length"] == 100
        assert c["max_body_length"] == 10000
        assert c["max_images"] == 20
        assert c["max_tags"] == 5
        assert "text" in c["supported_content_types"]
        assert "article" in c["supported_content_types"]
        assert "image_text" in c["supported_content_types"]
