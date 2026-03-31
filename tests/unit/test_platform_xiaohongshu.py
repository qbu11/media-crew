"""
Unit tests for Xiaohongshu platform tool.

Tests cover:
- XiaohongshuTool: init, authenticate(), publish(), get_analytics(), schedule()
- Compatibility helpers: _find_tab, _send_cdp, _js
- Validation: title too long, too many images, content_type restrictions
- Playwright automation flow (mocked page/browser)
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.tools.platform.base import (
    AnalyticsData,
    AuthStatus,
    ContentType,
    PublishContent,
)
from src.tools.platform.xiaohongshu import XiaohongshuTool


def _make_page(url="https://creator.xiaohongshu.com/publish/publish"):
    page = MagicMock()
    page.url = url
    page.goto = MagicMock()
    page.wait_for_timeout = MagicMock()
    page.wait_for_selector = MagicMock()
    page.query_selector = MagicMock(return_value=None)
    page.evaluate = MagicMock(return_value="clicked")
    page.keyboard = MagicMock()
    return page


def _make_browser(page=None):
    if page is None:
        page = _make_page()
    context = MagicMock()
    context.pages = [page]
    browser = MagicMock()
    browser.contexts = [context]
    browser.close = MagicMock()
    return browser


class TestXiaohongshuToolInit:
    def test_default_init(self):
        tool = XiaohongshuTool()
        assert tool.name == "xiaohongshu_publisher"
        assert tool.platform == "xiaohongshu"
        assert tool.version == "0.3.0"
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED
        assert tool._auth_checked is False
        assert tool._cdp_port == 9222

    def test_platform_constraints(self):
        tool = XiaohongshuTool()
        assert tool.max_title_length == 20
        assert tool.max_body_length == 1000
        assert tool.max_images == 18
        assert tool.max_tags == 10

    def test_supported_content_types(self):
        tool = XiaohongshuTool()
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.VIDEO in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.TEXT not in tool.supported_content_types
        assert ContentType.ARTICLE not in tool.supported_content_types

    def test_rate_limits(self):
        tool = XiaohongshuTool()
        assert tool.max_requests_per_minute == 1
        assert tool.min_interval_seconds == 60.0

    def test_init_with_custom_cdp_port(self):
        tool = XiaohongshuTool(config={"cdp_port": 9333})
        assert tool._cdp_port == 9333


class TestCompatibilityHelpers:
    def test_find_tab_success(self):
        tool = XiaohongshuTool()
        fake_tabs = [
            {"url": "https://google.com", "id": "1"},
            {
                "url": "https://www.xiaohongshu.com/explore",
                "id": "2",
                "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/2",
            },
        ]
        with patch("urllib.request.urlopen") as mock_urlopen:
            import json
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(fake_tabs).encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            tab = tool._find_tab("xiaohongshu")
            assert tab is not None
            assert tab["id"] == "2"

    def test_send_cdp(self):
        tool = XiaohongshuTool()
        ws = MagicMock()
        ws.recv.return_value = '{"id": 1, "result": {"ok": true}}'

        result = tool._send_cdp(ws, "Page.navigate", {"url": "https://example.com"})
        assert result["id"] == 1
        ws.send.assert_called_once()

    def test_js_helper(self):
        tool = XiaohongshuTool()
        ws = MagicMock()
        ws.recv.return_value = '{"id": 1, "result": {"result": {"type": "string", "value": "hello"}}}'

        val = tool._js(ws, "document.title")
        assert val == "hello"


class TestXiaohongshuAuthenticate:
    def test_authenticate_logged_in(self):
        tool = XiaohongshuTool()
        page = _make_page("https://creator.xiaohongshu.com/publish/publish")
        browser = _make_browser(page)
        pw = MagicMock()

        with patch.object(tool, "_connect_browser", return_value=(browser, pw)):
            result = tool.authenticate()

        assert result.is_success()
        assert tool._auth_status == AuthStatus.AUTHENTICATED
        assert tool._auth_checked is True
        browser.close.assert_called_once()
        pw.stop.assert_called_once()

    def test_authenticate_not_logged_in(self):
        tool = XiaohongshuTool()
        page = _make_page("https://creator.xiaohongshu.com/login")
        browser = _make_browser(page)
        pw = MagicMock()

        with patch.object(tool, "_connect_browser", return_value=(browser, pw)):
            result = tool.authenticate()

        assert result.is_failed()
        assert "Not logged into Xiaohongshu" in result.error
        assert tool._auth_status == AuthStatus.NOT_AUTHENTICATED

    def test_authenticate_connection_error(self):
        tool = XiaohongshuTool()
        with patch.object(tool, "_connect_browser", side_effect=RuntimeError("connect failed")):
            result = tool.authenticate()

        assert result.is_failed()
        assert tool._auth_status == AuthStatus.ERROR


class TestXiaohongshuPublish:
    def _make_content(self, **overrides):
        defaults = {
            "title": "AI编程工具测试",
            "body": "测试内容",
            "content_type": ContentType.IMAGE,
            "images": ["img1.jpg"],
            "tags": ["AI", "编程"],
        }
        defaults.update(overrides)
        return PublishContent(**defaults)

    def test_publish_validation_invalid_type(self):
        tool = XiaohongshuTool()
        content = self._make_content(content_type=ContentType.TEXT, images=[])
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error

    def test_publish_validation_title_too_long(self):
        tool = XiaohongshuTool()
        content = self._make_content(title="x" * 21)
        result = tool.publish(content)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_publish_validation_body_too_long(self):
        tool = XiaohongshuTool()
        content = self._make_content(body="x" * 1001)
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_validation_too_many_images(self):
        tool = XiaohongshuTool()
        content = self._make_content(images=[f"img{i}.jpg" for i in range(19)])
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_validation_too_many_tags(self):
        tool = XiaohongshuTool()
        content = self._make_content(tags=[f"tag{i}" for i in range(11)])
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many tags" in result.error

    def test_publish_no_page(self):
        tool = XiaohongshuTool()
        content = self._make_content()
        browser = MagicMock()
        browser.contexts = []
        browser.close = MagicMock()
        pw = MagicMock()

        with patch.object(tool, "_connect_browser", return_value=(browser, pw)):
            result = tool.publish(content)

        assert result.is_failed()
        assert "No page in Chrome" in result.error

    def test_publish_not_logged_in(self):
        tool = XiaohongshuTool()
        content = self._make_content()
        page = _make_page("https://creator.xiaohongshu.com/login")
        browser = _make_browser(page)
        pw = MagicMock()

        with patch.object(tool, "_connect_browser", return_value=(browser, pw)):
            result = tool.publish(content)

        assert result.is_failed()
        assert "Not logged in" in result.error

    @patch("src.tools.platform.xiaohongshu.time.sleep")
    def test_publish_success_full_flow(self, _mock_sleep):
        tool = XiaohongshuTool()
        content = self._make_content()
        page = _make_page()
        browser = _make_browser(page)
        pw = MagicMock()

        with patch.object(tool, "_connect_browser", return_value=(browser, pw)):
            with patch.object(tool, "_pw_wait_for_editor") as mock_wait:
                with patch.object(tool, "_pw_upload_images") as mock_upload:
                    with patch.object(tool, "_pw_fill_title") as mock_title:
                        with patch.object(tool, "_pw_fill_body") as mock_body:
                            with patch.object(tool, "_pw_add_tags") as mock_tags:
                                with patch.object(tool, "_pw_save_draft", return_value=True) as mock_save:
                                    result = tool.publish(content)

        assert result.is_success()
        assert result.platform == "xiaohongshu"
        assert result.content_id.startswith("xhs_")
        assert result.published_at is not None
        assert result.data["title"] == "AI编程工具测试"
        assert result.data["images_count"] == 1
        assert result.data["tags"] == ["AI", "编程"]
        assert result.data["draft_saved"] is True
        mock_wait.assert_called_once()
        mock_upload.assert_called_once()
        mock_title.assert_called_once()
        mock_body.assert_called_once()
        mock_tags.assert_called_once()
        mock_save.assert_called_once()
        browser.close.assert_called_once()
        pw.stop.assert_called_once()

    @patch("src.tools.platform.xiaohongshu.time.sleep")
    def test_publish_connection_error(self, _mock_sleep):
        tool = XiaohongshuTool()
        content = self._make_content()

        with patch.object(tool, "_connect_browser", side_effect=RuntimeError("connection refused")):
            result = tool.publish(content)

        assert result.is_failed()
        assert "Publishing failed" in result.error


class TestXiaohongshuGetAnalytics:
    def test_get_analytics(self):
        tool = XiaohongshuTool()
        analytics = tool.get_analytics("xhs_123")
        assert isinstance(analytics, AnalyticsData)
        assert analytics.content_id == "xhs_123"
        assert analytics.views == 0
        assert analytics.likes == 0
        assert analytics.raw_data is not None


class TestXiaohongshuSchedule:
    def test_schedule_future_time(self):
        tool = XiaohongshuTool()
        content = PublishContent(
            title="Scheduled",
            body="Content",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "scheduled_for" in result.data

    def test_schedule_past_time(self):
        tool = XiaohongshuTool()
        content = PublishContent(
            title="Past",
            body="Content",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        past = datetime.now() - timedelta(hours=1)
        result = tool.schedule(content, past)
        assert result.is_failed()
        assert "future" in result.error.lower()

    def test_schedule_validates_content(self):
        tool = XiaohongshuTool()
        content = PublishContent(
            title="x" * 21,
            body="B",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_schedule_validates_content_type(self):
        tool = XiaohongshuTool()
        content = PublishContent(title="T", body="B", content_type=ContentType.TEXT)
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "not supported" in result.error


class TestXiaohongshuGetConstraints:
    def test_get_constraints(self):
        tool = XiaohongshuTool()
        c = tool.get_constraints()
        assert c["platform"] == "xiaohongshu"
        assert c["max_title_length"] == 20
        assert c["max_body_length"] == 1000
        assert c["max_images"] == 18
        assert c["max_tags"] == 10
        assert "image" in c["supported_content_types"]
        assert "video" in c["supported_content_types"]
        assert "image_text" in c["supported_content_types"]
