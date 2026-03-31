"""Tests for WechatTool real API integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.tools.base_tool import ToolStatus
from src.tools.platform.base import ContentType, PublishContent
from src.tools.platform.wechat import WechatTool, PublishMethod


@pytest.fixture
def tool():
    return WechatTool(config={
        "app_id": "wx_test_id",
        "app_secret": "test_secret",
    })


@pytest.fixture
def article_content():
    return PublishContent(
        title="测试文章标题",
        body="<p>这是测试内容</p>",
        content_type=ContentType.ARTICLE,
    )


class TestWechatToolInit:
    def test_loads_credentials_from_config(self):
        tool = WechatTool(config={"app_id": "wx123", "app_secret": "sec456"})
        assert tool._app_id == "wx123"
        assert tool._app_secret == "sec456"

    def test_has_api_credentials(self, tool):
        assert tool._has_api_credentials() is True

    def test_no_credentials(self):
        t = WechatTool(config={"app_id": "", "app_secret": ""})
        t._app_id = None
        t._app_secret = None
        assert t._has_api_credentials() is False

    def test_default_publish_method_is_api(self, tool):
        assert tool._publish_method == PublishMethod.API


class TestWechatToolAuthenticate:
    def test_api_auth_with_credentials(self, tool):
        result = tool.authenticate()
        assert result.is_success()
        assert result.data["method"] == "api"

    def test_api_auth_without_credentials(self):
        t = WechatTool(config={"app_id": "", "app_secret": ""})
        t._app_id = None
        t._app_secret = None
        result = t.authenticate()
        assert result.is_failed()
        assert "credentials" in result.error.lower()


class TestWechatToolPublishViaApi:
    @patch("src.tools.platform.wechat.urllib.request.urlopen")
    def test_publish_success(self, mock_urlopen, tool, article_content):
        # Mock access token response
        token_resp = MagicMock()
        token_resp.read.return_value = json.dumps({
            "access_token": "test_token_123",
            "expires_in": 7200,
        }).encode()
        token_resp.__enter__ = lambda s: s
        token_resp.__exit__ = MagicMock(return_value=False)

        # Mock draft/add response
        draft_resp = MagicMock()
        draft_resp.read.return_value = json.dumps({
            "media_id": "MEDIA_ID_12345",
        }).encode()
        draft_resp.__enter__ = lambda s: s
        draft_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [token_resp, draft_resp]

        result = tool._publish_via_api(article_content)
        assert result.is_success()
        assert result.content_id == "MEDIA_ID_12345"
        assert result.data["method"] == "api"
        assert result.status_detail == "草稿已保存"

    @patch("src.tools.platform.wechat.urllib.request.urlopen")
    def test_publish_token_error(self, mock_urlopen, tool, article_content):
        token_resp = MagicMock()
        token_resp.read.return_value = json.dumps({
            "errcode": 40164,
            "errmsg": "invalid ip, not in whitelist",
        }).encode()
        token_resp.__enter__ = lambda s: s
        token_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = token_resp

        result = tool._publish_via_api(article_content)
        assert result.is_failed()
        assert "40164" in result.error

    @patch("src.tools.platform.wechat.urllib.request.urlopen")
    def test_publish_wraps_plain_text(self, mock_urlopen, tool):
        content = PublishContent(
            title="纯文本测试",
            body="第一段\n\n第二段\n\n第三段",
            content_type=ContentType.ARTICLE,
        )

        token_resp = MagicMock()
        token_resp.read.return_value = json.dumps({"access_token": "tok"}).encode()
        token_resp.__enter__ = lambda s: s
        token_resp.__exit__ = MagicMock(return_value=False)

        draft_resp = MagicMock()
        draft_resp.read.return_value = json.dumps({"media_id": "M1"}).encode()
        draft_resp.__enter__ = lambda s: s
        draft_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [token_resp, draft_resp]

        result = tool._publish_via_api(content)
        assert result.is_success()

        # Verify the draft/add call had HTML-wrapped content
        call_args = mock_urlopen.call_args_list[1]
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        html = body["articles"][0]["content"]
        assert "<p>" in html

    def test_publish_no_credentials(self):
        t = WechatTool(config={"app_id": "", "app_secret": ""})
        t._app_id = None
        t._app_secret = None
        content = PublishContent(title="t", body="b", content_type=ContentType.ARTICLE)
        result = t._publish_via_api(content)
        assert result.is_failed()
        assert "credentials" in result.error.lower()


class TestWechatToolValidation:
    def test_title_too_long(self, tool):
        content = PublishContent(
            title="x" * 65,
            body="body",
            content_type=ContentType.ARTICLE,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "title" in result.error.lower()

    def test_unsupported_content_type(self, tool):
        content = PublishContent(
            title="test",
            body="body",
            content_type=ContentType.VIDEO,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error.lower()


class TestAccessTokenCaching:
    @patch("src.tools.platform.wechat.urllib.request.urlopen")
    def test_caches_token(self, mock_urlopen, tool):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "access_token": "cached_token",
            "expires_in": 7200,
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        token1 = tool._get_access_token()
        token2 = tool._get_access_token()

        assert token1 == "cached_token"
        assert token2 == "cached_token"
        # Should only call API once due to caching
        assert mock_urlopen.call_count == 1
