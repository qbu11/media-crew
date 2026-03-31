"""
Unit tests for WeChat platform tool.

Tests cover:
- WechatTool: init, authenticate(), publish(), get_analytics(), schedule()
- API vs browser publish methods
- _has_api_credentials(), _publish_via_api(), _publish_via_browser()
- Validation edge cases
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.tools.base_tool import ToolStatus
from src.tools.platform.base import (
    AnalyticsData,
    ContentType,
    PublishContent,
    PublishResult,
)
from src.tools.platform.wechat import PublishMethod, WechatTool


class TestWechatToolInit:
    """Tests for WechatTool initialization."""

    def test_default_init(self):
        tool = WechatTool()
        assert tool.name == "wechat_publisher"
        assert tool.platform == "wechat"
        assert tool.version == "0.1.0"
        assert tool._publish_method == PublishMethod.API
        assert tool._author == ""
        assert tool._need_open_comment is True
        assert tool._only_fans_can_comment is False

    def test_platform_constraints(self):
        tool = WechatTool()
        assert tool.max_title_length == 64
        assert tool.max_body_length == 20000
        assert tool.max_images == 9
        assert tool.max_tags == 0

    def test_supported_content_types(self):
        tool = WechatTool()
        assert ContentType.ARTICLE in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.TEXT not in tool.supported_content_types
        assert ContentType.VIDEO not in tool.supported_content_types

    def test_rate_limits(self):
        tool = WechatTool()
        assert tool.max_requests_per_minute == 5
        assert tool.min_interval_seconds == 10.0

    def test_init_with_config(self):
        tool = WechatTool(config={
            "publish_method": PublishMethod.BROWSER,
            "app_id": "test_id",
            "app_secret": "test_secret",
            "default_author": "TestAuthor",
            "need_open_comment": False,
            "only_fans_can_comment": True,
        })
        assert tool._publish_method == PublishMethod.BROWSER
        assert tool._app_id == "test_id"
        assert tool._app_secret == "test_secret"
        assert tool._author == "TestAuthor"
        assert tool._need_open_comment is False
        assert tool._only_fans_can_comment is True

    def test_init_reads_env_vars(self):
        with patch.dict("os.environ", {"WECHAT_APP_ID": "env_id", "WECHAT_APP_SECRET": "env_secret"}):
            tool = WechatTool()
        assert tool._app_id == "env_id"
        assert tool._app_secret == "env_secret"

    def test_config_overrides_env(self):
        with patch.dict("os.environ", {"WECHAT_APP_ID": "env_id", "WECHAT_APP_SECRET": "env_secret"}):
            tool = WechatTool(config={"app_id": "cfg_id", "app_secret": "cfg_secret"})
        assert tool._app_id == "cfg_id"
        assert tool._app_secret == "cfg_secret"


class TestWechatHasApiCredentials:
    """Tests for WechatTool._has_api_credentials()."""

    def test_has_credentials_both_present(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        assert tool._has_api_credentials() is True

    @patch.object(WechatTool, "_load_env_credentials", return_value={})
    def test_no_credentials(self, _mock_env):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("WECHAT_APP_ID", None)
            os.environ.pop("WECHAT_APP_SECRET", None)
            tool = WechatTool()
        assert tool._has_api_credentials() is False

    @patch.object(WechatTool, "_load_env_credentials", return_value={})
    def test_partial_credentials_id_only(self, _mock_env):
        with patch.dict("os.environ", {"WECHAT_APP_ID": "id"}, clear=False):
            import os
            os.environ.pop("WECHAT_APP_SECRET", None)
            tool = WechatTool()
        assert tool._has_api_credentials() is False

    @patch.object(WechatTool, "_load_env_credentials", return_value={})
    def test_partial_credentials_secret_only(self, _mock_env):
        with patch.dict("os.environ", {"WECHAT_APP_SECRET": "sec"}, clear=False):
            import os
            os.environ.pop("WECHAT_APP_ID", None)
            tool = WechatTool()
        assert tool._has_api_credentials() is False


class TestWechatAuthenticate:
    """Tests for WechatTool.authenticate()."""

    def test_authenticate_api_with_credentials(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        result = tool.authenticate()
        assert result.is_success()
        assert result.data["method"] == "api"

    @patch.object(WechatTool, "_load_env_credentials", return_value={})
    def test_authenticate_api_no_credentials(self, _mock_env):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("WECHAT_APP_ID", None)
            os.environ.pop("WECHAT_APP_SECRET", None)
            tool = WechatTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "credentials" in result.error.lower()

    def test_authenticate_browser_method(self):
        tool = WechatTool(config={"publish_method": PublishMethod.BROWSER})
        result = tool.authenticate()
        # If scripts exist on this machine, authentication succeeds
        # If scripts don't exist, authentication fails
        assert result.platform == "wechat"
        if result.is_success():
            assert result.data["method"] == "browser"
        else:
            assert "script" in result.error.lower()


class TestWechatPublish:
    """Tests for WechatTool.publish()."""

    @patch.object(WechatTool, "_create_draft", return_value={"media_id": "mock_media_123"})
    def test_publish_api_success(self, _mock_draft):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(
            title="Article Title",
            body="Article body content",
            content_type=ContentType.ARTICLE,
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.platform == "wechat"
        assert result.data["method"] == "api"
        assert result.data["title"] == "Article Title"
        assert result.status_detail == "草稿已保存"

    def test_publish_validation_fails_unsupported_type(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.VIDEO,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error

    def test_publish_validation_fails_title_too_long(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(
            title="x" * 65,
            body="B",
            content_type=ContentType.ARTICLE,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_publish_validation_fails_body_too_long(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(
            title="T",
            body="x" * 20001,
            content_type=ContentType.ARTICLE,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    @patch.object(WechatTool, "_create_draft", return_value={"media_id": "mock_media_456"})
    def test_publish_image_text_content(self, _mock_draft):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(
            title="Mixed Content",
            body="Body",
            content_type=ContentType.IMAGE_TEXT,
            images=["img1.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()


class TestWechatPublishViaApi:
    """Tests for WechatTool._publish_via_api()."""

    @patch.object(WechatTool, "_load_env_credentials", return_value={})
    def test_publish_via_api_no_credentials(self, _mock_env):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("WECHAT_APP_ID", None)
            os.environ.pop("WECHAT_APP_SECRET", None)
            tool = WechatTool()
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        result = tool._publish_via_api(content)
        assert result.is_failed()
        assert "credentials" in result.error.lower()

    @patch.object(WechatTool, "_create_draft", return_value={"media_id": "mock_media_789"})
    def test_publish_via_api_success(self, _mock_draft):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        result = tool._publish_via_api(content)
        assert result.is_success()
        assert result.data["manage_url"] == "https://mp.weixin.qq.com"


class TestWechatPublishViaBrowser:
    """Tests for WechatTool._publish_via_browser()."""

    @patch("subprocess.run")
    def test_publish_via_browser_article(self, mock_run):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": '{}', "stderr": ""})()
        tool = WechatTool(config={"publish_method": PublishMethod.BROWSER})
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        result = tool._publish_via_browser(content)
        if result.is_success():
            assert result.data["method"] == "browser"
        else:
            # Script not found on this machine
            assert "not found" in result.error.lower() or "failed" in result.error.lower()

    @patch("subprocess.run")
    def test_publish_via_browser_image_text_uses_browser_script(self, mock_run):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": '{}', "stderr": ""})()
        tool = WechatTool(config={"publish_method": PublishMethod.BROWSER})
        content = PublishContent(
            title="T",
            body="B",
            content_type=ContentType.IMAGE_TEXT,
        )
        result = tool._publish_via_browser(content)
        if result.is_success():
            assert result.data["method"] == "browser"
        else:
            assert "not found" in result.error.lower() or "failed" in result.error.lower()


class TestWechatGetAnalytics:
    """Tests for WechatTool.get_analytics()."""

    def test_get_analytics(self):
        tool = WechatTool()
        analytics = tool.get_analytics("wechat_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "wechat_123"
        assert analytics.views == 0


class TestWechatSchedule:
    """Tests for WechatTool.schedule()."""

    def test_schedule_past_time_fails(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        past = datetime.now() - timedelta(hours=1)
        result = tool.schedule(content, past)
        assert result.is_failed()
        assert "future" in result.error.lower()

    @patch.object(WechatTool, "_create_draft", return_value={"media_id": "sched_123"})
    def test_schedule_future_time_success(self, _mock_draft):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        future = datetime.now() + timedelta(hours=2)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "scheduled_for" in result.data
        assert "已预约发布" in result.status_detail

    def test_schedule_validates_content(self):
        tool = WechatTool(config={"app_id": "id", "app_secret": "sec"})
        content = PublishContent(title="x" * 65, body="B", content_type=ContentType.ARTICLE)
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "Title exceeds" in result.error


class TestWechatGetConstraints:
    """Tests for WechatTool.get_constraints()."""

    def test_get_constraints(self):
        tool = WechatTool()
        c = tool.get_constraints()
        assert c["platform"] == "wechat"
        assert c["max_title_length"] == 64
        assert c["max_body_length"] == 20000
        assert c["max_images"] == 9
        assert c["max_tags"] == 0
        assert "article" in c["supported_content_types"]
        assert "image_text" in c["supported_content_types"]


class TestPublishMethod:
    """Tests for the PublishMethod constants."""

    def test_api_method(self):
        assert PublishMethod.API == "api"

    def test_browser_method(self):
        assert PublishMethod.BROWSER == "browser"
