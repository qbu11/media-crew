"""
Unit tests for CookieManager.

Tests cover:
- Save, load, delete cookies
- Cookie expiry detection
- List and cleanup operations
- Cookie info and status summary
- Platform helpers
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.services.cookie_manager import CookieManager, get_cookie_manager


@pytest.fixture
def cookie_mgr(tmp_path):
    """Create a CookieManager with a temp directory."""
    return CookieManager(storage_dir=str(tmp_path / "cookies"))


@pytest.fixture
def sample_cookies():
    """Sample cookie data."""
    return [
        {"name": "web_session", "value": "abc123", "domain": ".xiaohongshu.com"},
        {"name": "a1", "value": "def456", "domain": ".xiaohongshu.com"},
    ]


class TestCookieManagerInit:
    def test_creates_storage_dir(self, tmp_path):
        storage = tmp_path / "test_cookies"
        mgr = CookieManager(storage_dir=str(storage))
        assert storage.exists()
        assert (storage / ".gitignore").exists()

    def test_default_storage_dir(self):
        mgr = CookieManager()
        assert mgr.storage_dir.name == "cookies"


class TestSaveCookies:
    async def test_save_success(self, cookie_mgr, sample_cookies):
        result = await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        assert result.success is True
        assert result.data is True

        # Verify file was created
        cookie_file = cookie_mgr._get_cookie_file("xiaohongshu", "testuser")
        assert cookie_file.exists()

        # Verify content
        content = json.loads(cookie_file.read_text(encoding="utf-8"))
        assert content["platform"] == "xiaohongshu"
        assert content["username"] == "testuser"
        assert len(content["cookies"]) == 2

    async def test_save_with_custom_expiry(self, cookie_mgr, sample_cookies):
        result = await cookie_mgr.save_cookies(
            "weibo", "user2", sample_cookies, expires_days=7
        )
        assert result.success is True

        cookie_file = cookie_mgr._get_cookie_file("weibo", "user2")
        content = json.loads(cookie_file.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(content["created_at"])
        expires = datetime.fromisoformat(content["expires_at"])
        assert (expires - created).days == 7


class TestLoadCookies:
    async def test_load_success(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        result = await cookie_mgr.load_cookies("xiaohongshu", "testuser")
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["name"] == "web_session"

    async def test_load_not_found(self, cookie_mgr):
        result = await cookie_mgr.load_cookies("xiaohongshu", "nonexistent")
        assert result.success is False
        assert result.error_code == "COOKIE_NOT_FOUND"

    async def test_load_expired(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies(
            "xiaohongshu", "testuser", sample_cookies, expires_days=0
        )
        # Manually set expires_at to the past
        cookie_file = cookie_mgr._get_cookie_file("xiaohongshu", "testuser")
        content = json.loads(cookie_file.read_text(encoding="utf-8"))
        content["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
        cookie_file.write_text(json.dumps(content), encoding="utf-8")

        result = await cookie_mgr.load_cookies("xiaohongshu", "testuser")
        assert result.success is False
        assert result.error_code == "COOKIE_EXPIRED"


class TestDeleteCookies:
    async def test_delete_success(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        result = await cookie_mgr.delete_cookies("xiaohongshu", "testuser")
        assert result.success is True

        # Verify file was deleted
        cookie_file = cookie_mgr._get_cookie_file("xiaohongshu", "testuser")
        assert not cookie_file.exists()

    async def test_delete_not_found(self, cookie_mgr):
        result = await cookie_mgr.delete_cookies("xiaohongshu", "nonexistent")
        assert result.success is False
        assert result.error_code == "COOKIE_NOT_FOUND"


class TestListCookies:
    async def test_list_all(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "user1", sample_cookies)
        await cookie_mgr.save_cookies("weibo", "user2", sample_cookies)

        result = await cookie_mgr.list_cookies()
        assert result.success is True
        assert len(result.data) == 2

    async def test_list_by_platform(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "user1", sample_cookies)
        await cookie_mgr.save_cookies("weibo", "user2", sample_cookies)

        result = await cookie_mgr.list_cookies(platform="xiaohongshu")
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["platform"] == "xiaohongshu"

    async def test_list_empty(self, cookie_mgr):
        result = await cookie_mgr.list_cookies()
        assert result.success is True
        assert len(result.data) == 0


class TestCleanupExpired:
    async def test_cleanup(self, cookie_mgr, sample_cookies):
        # Save two cookies, one expired
        await cookie_mgr.save_cookies("xiaohongshu", "user1", sample_cookies)
        await cookie_mgr.save_cookies("weibo", "user2", sample_cookies)

        # Expire one
        cookie_file = cookie_mgr._get_cookie_file("weibo", "user2")
        content = json.loads(cookie_file.read_text(encoding="utf-8"))
        content["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
        cookie_file.write_text(json.dumps(content), encoding="utf-8")

        result = await cookie_mgr.cleanup_expired()
        assert result.success is True
        assert result.data == 1

        # Verify only expired was deleted
        assert cookie_mgr._get_cookie_file("xiaohongshu", "user1").exists()
        assert not cookie_mgr._get_cookie_file("weibo", "user2").exists()


class TestGetCookieInfo:
    async def test_get_info(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        result = await cookie_mgr.get_cookie_info("xiaohongshu", "testuser")
        assert result.success is True
        assert result.data["platform"] == "xiaohongshu"
        assert result.data["cookie_count"] == 2
        assert result.data["is_expired"] is False

    async def test_get_info_not_found(self, cookie_mgr):
        result = await cookie_mgr.get_cookie_info("xiaohongshu", "nonexistent")
        assert result.success is False


class TestGetCookiesDict:
    async def test_get_dict(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        result = await cookie_mgr.get_cookies_dict("xiaohongshu", "testuser")
        assert result.success is True
        assert result.data["web_session"] == "abc123"
        assert result.data["a1"] == "def456"


class TestGetStatusSummary:
    async def test_summary(self, cookie_mgr, sample_cookies):
        await cookie_mgr.save_cookies("xiaohongshu", "testuser", sample_cookies)
        result = await cookie_mgr.get_status_summary()
        assert result.success is True
        assert result.data["xiaohongshu"]["logged_in"] is True
        assert result.data["xiaohongshu"]["status"] == "valid"
        assert result.data["weibo"]["logged_in"] is False


class TestPlatformHelpers:
    def test_get_login_url(self, cookie_mgr):
        url = cookie_mgr.get_platform_login_url("xiaohongshu")
        assert "xiaohongshu" in url
        assert cookie_mgr.get_platform_login_url("unknown") is None

    def test_get_key_cookies(self, cookie_mgr):
        keys = cookie_mgr.get_key_cookies("xiaohongshu")
        assert "web_session" in keys
        assert cookie_mgr.get_key_cookies("unknown") == []


class TestSingleton:
    def test_get_cookie_manager(self):
        import src.services.cookie_manager as mod
        mod._cookie_manager = None  # Reset
        mgr = get_cookie_manager()
        assert isinstance(mgr, CookieManager)
        mgr2 = get_cookie_manager()
        assert mgr is mgr2
        mod._cookie_manager = None  # Cleanup
