"""
Unit tests for platform base module.

Tests cover:
- PublishContent: to_dict(), from_dict()
- PublishResult: to_dict()
- AnalyticsData: to_dict()
- BasePlatformTool: validate_content(), check_auth_status(), execute(), get_constraints()
"""

from datetime import datetime
from typing import Any

import pytest

from src.tools.base_tool import ToolResult, ToolStatus
from src.tools.platform.base import (
    AnalyticsData,
    AuthStatus,
    BasePlatformTool,
    ContentType,
    PublishContent,
    PublishResult,
)


# ---------------------------------------------------------------------------
# Concrete subclass of BasePlatformTool for testing
# ---------------------------------------------------------------------------
class StubPlatformTool(BasePlatformTool):
    """Minimal concrete subclass for testing BasePlatformTool."""

    name = "stub_platform"
    description = "Stub platform for tests"
    platform = "stub"
    version = "0.1.0"

    max_title_length = 50
    max_body_length = 500
    max_images = 5
    max_tags = 3
    supported_content_types = [ContentType.TEXT, ContentType.IMAGE]

    def __init__(self, config: dict[str, Any] | None = None, auth_error: str | None = None):
        super().__init__(config)
        self._auth_error = auth_error  # allow tests to inject auth failures

    def authenticate(self) -> ToolResult:
        if self._auth_error:
            return ToolResult(status=ToolStatus.FAILED, error=self._auth_error, platform=self.platform)
        return ToolResult(status=ToolStatus.SUCCESS, data={"status": "ok"}, platform=self.platform)

    def publish(self, content: PublishContent) -> PublishResult:
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id="stub_123",
            content_url="https://stub.example.com/123",
            published_at=datetime.now(),
        )

    def get_analytics(self, content_id: str) -> AnalyticsData:
        return AnalyticsData(content_id=content_id, views=100, likes=10)

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        return PublishResult(status=ToolStatus.SUCCESS, platform=self.platform)


# ===========================================================================
# PublishContent tests
# ===========================================================================
class TestPublishContent:
    """Tests for the PublishContent dataclass."""

    def test_to_dict_all_fields(self):
        pc = PublishContent(
            title="Hello",
            body="World",
            content_type=ContentType.ARTICLE,
            images=["img1.jpg"],
            video="/path/to/video.mp4",
            cover_image="cover.jpg",
            tags=["tag1"],
            topics=["topic1"],
            location="Beijing",
            mentions=["@user"],
            custom_fields={"key": "val"},
        )
        d = pc.to_dict()
        assert d["title"] == "Hello"
        assert d["body"] == "World"
        assert d["content_type"] == "article"
        assert d["images"] == ["img1.jpg"]
        assert d["video"] == "/path/to/video.mp4"
        assert d["cover_image"] == "cover.jpg"
        assert d["tags"] == ["tag1"]
        assert d["topics"] == ["topic1"]
        assert d["location"] == "Beijing"
        assert d["mentions"] == ["@user"]
        assert d["custom_fields"] == {"key": "val"}

    def test_to_dict_defaults(self):
        pc = PublishContent(title="T", body="B")
        d = pc.to_dict()
        assert d["content_type"] == "text"
        assert d["images"] == []
        assert d["video"] is None
        assert d["tags"] == []

    def test_from_dict_with_string_content_type(self):
        data = {
            "title": "T",
            "body": "B",
            "content_type": "image",
        }
        pc = PublishContent.from_dict(data)
        assert pc.content_type == ContentType.IMAGE
        assert pc.title == "T"

    def test_from_dict_with_enum_content_type(self):
        data = {
            "title": "T",
            "body": "B",
            "content_type": ContentType.VIDEO,
        }
        pc = PublishContent.from_dict(data)
        assert pc.content_type == ContentType.VIDEO

    def test_from_dict_roundtrip(self):
        original = PublishContent(
            title="RT",
            body="Roundtrip body",
            content_type=ContentType.IMAGE_TEXT,
            images=["a.png", "b.png"],
            tags=["t1", "t2"],
        )
        d = original.to_dict()
        restored = PublishContent.from_dict(d)
        assert restored.title == original.title
        assert restored.content_type == original.content_type
        assert restored.images == original.images
        assert restored.tags == original.tags


# ===========================================================================
# PublishResult tests
# ===========================================================================
class TestPublishResult:
    """Tests for the PublishResult dataclass."""

    def test_to_dict_extends_parent(self):
        now = datetime.now()
        pr = PublishResult(
            status=ToolStatus.SUCCESS,
            platform="xhs",
            content_id="xhs_001",
            content_url="https://xhs.com/001",
            preview_url="https://xhs.com/preview/001",
            published_at=now,
            status_detail="published",
            data={"extra": True},
        )
        d = pr.to_dict()
        # Parent fields
        assert d["status"] == "success"
        assert d["platform"] == "xhs"
        assert d["data"] == {"extra": True}
        # Child fields
        assert d["content_id"] == "xhs_001"
        assert d["content_url"] == "https://xhs.com/001"
        assert d["preview_url"] == "https://xhs.com/preview/001"
        assert d["published_at"] == now.isoformat()
        assert d["status_detail"] == "published"

    def test_to_dict_null_published_at(self):
        pr = PublishResult(status=ToolStatus.FAILED, error="e")
        d = pr.to_dict()
        assert d["published_at"] is None
        assert d["content_url"] is None

    def test_inherits_is_success(self):
        pr = PublishResult(status=ToolStatus.SUCCESS)
        assert pr.is_success() is True

    def test_inherits_is_failed(self):
        pr = PublishResult(status=ToolStatus.FAILED, error="x")
        assert pr.is_failed() is True


# ===========================================================================
# AnalyticsData tests
# ===========================================================================
class TestAnalyticsData:
    """Tests for the AnalyticsData dataclass."""

    def test_to_dict_all_fields(self):
        now = datetime.now()
        ad = AnalyticsData(
            content_id="c1",
            views=1000,
            likes=100,
            comments=50,
            shares=25,
            favorites=75,
            forwards=10,
            engagement_rate=0.15,
            reach=5000,
            impressions=8000,
            click_through_rate=0.03,
            period_start=now,
            period_end=now,
            raw_data={"source": "api"},
        )
        d = ad.to_dict()
        assert d["content_id"] == "c1"
        assert d["views"] == 1000
        assert d["likes"] == 100
        assert d["comments"] == 50
        assert d["shares"] == 25
        assert d["favorites"] == 75
        assert d["forwards"] == 10
        assert d["engagement_rate"] == 0.15
        assert d["reach"] == 5000
        assert d["impressions"] == 8000
        assert d["click_through_rate"] == 0.03
        assert d["period_start"] == now.isoformat()
        assert d["period_end"] == now.isoformat()
        assert d["raw_data"] == {"source": "api"}

    def test_to_dict_defaults(self):
        ad = AnalyticsData(content_id="c2")
        d = ad.to_dict()
        assert d["views"] == 0
        assert d["likes"] == 0
        assert d["period_start"] is None
        assert d["period_end"] is None
        assert d["raw_data"] == {}


# ===========================================================================
# BasePlatformTool tests (via StubPlatformTool)
# ===========================================================================
class TestBasePlatformTool:
    """Tests for BasePlatformTool methods."""

    # -- validate_content --
    def test_validate_content_valid(self):
        tool = StubPlatformTool()
        content = PublishContent(title="Hi", body="Hello", content_type=ContentType.TEXT)
        is_valid, err = tool.validate_content(content)
        assert is_valid is True
        assert err is None

    def test_validate_content_unsupported_type(self):
        tool = StubPlatformTool()
        content = PublishContent(title="T", body="B", content_type=ContentType.VIDEO)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "not supported" in err

    def test_validate_content_title_too_long(self):
        tool = StubPlatformTool()
        content = PublishContent(title="x" * 51, body="B", content_type=ContentType.TEXT)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "Title exceeds" in err

    def test_validate_content_body_too_long(self):
        tool = StubPlatformTool()
        content = PublishContent(title="T", body="x" * 501, content_type=ContentType.TEXT)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "Body exceeds" in err

    def test_validate_content_too_many_images(self):
        tool = StubPlatformTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(6)],
        )
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "Too many images" in err

    def test_validate_content_too_many_tags(self):
        tool = StubPlatformTool()
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.TEXT,
            tags=["t1", "t2", "t3", "t4"],
        )
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "Too many tags" in err

    def test_validate_content_edge_exact_limits(self):
        tool = StubPlatformTool()
        content = PublishContent(
            title="x" * 50,
            body="y" * 500,
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(5)],
            tags=["t1", "t2", "t3"],
        )
        is_valid, err = tool.validate_content(content)
        assert is_valid is True

    # -- check_auth_status --
    def test_check_auth_status_authenticated(self):
        tool = StubPlatformTool()
        status = tool.check_auth_status()
        assert status == AuthStatus.AUTHENTICATED

    def test_check_auth_status_expired(self):
        tool = StubPlatformTool(auth_error="Token expired please re-login")
        status = tool.check_auth_status()
        assert status == AuthStatus.EXPIRED

    def test_check_auth_status_not_authenticated(self):
        tool = StubPlatformTool(auth_error="User not authenticated")
        status = tool.check_auth_status()
        assert status == AuthStatus.NOT_AUTHENTICATED

    def test_check_auth_status_generic_error(self):
        tool = StubPlatformTool(auth_error="Something went wrong")
        status = tool.check_auth_status()
        assert status == AuthStatus.ERROR

    # -- execute (default implementation) --
    def test_execute_with_dict_content(self):
        tool = StubPlatformTool()
        content_dict = {"title": "T", "body": "B", "content_type": "text"}
        result = tool.execute(content=content_dict)
        assert result.is_success()
        assert result.content_id == "stub_123"

    def test_execute_with_publish_content(self):
        tool = StubPlatformTool()
        pc = PublishContent(title="T", body="B")
        result = tool.execute(content=pc)
        assert result.is_success()

    def test_execute_with_invalid_content(self):
        tool = StubPlatformTool()
        result = tool.execute(content="not a dict or PublishContent")
        assert result.is_failed()
        assert "Invalid content" in result.error

    def test_execute_with_no_content(self):
        tool = StubPlatformTool()
        result = tool.execute()
        assert result.is_failed()
        assert "Invalid content" in result.error

    # -- get_constraints --
    def test_get_constraints(self):
        tool = StubPlatformTool()
        c = tool.get_constraints()
        assert c["platform"] == "stub"
        assert c["max_title_length"] == 50
        assert c["max_body_length"] == 500
        assert c["max_images"] == 5
        assert c["max_tags"] == 3
        assert "text" in c["supported_content_types"]
        assert "image" in c["supported_content_types"]
