"""
Unit tests for platform __init__.py module.

Tests cover:
- get_platform_tool() with valid and invalid platform names
- list_platforms() with different flags
- PLATFORM_REGISTRY contains expected entries
"""

import pytest

from src.tools.platform import (
    ALL_PLATFORMS,
    DOMESTIC_PLATFORMS,
    OVERSEAS_AVAILABLE,
    OVERSEAS_PLATFORMS,
    PLATFORM_REGISTRY,
    BasePlatformTool,
    BilibiliTool,
    DouyinTool,
    WechatTool,
    WeiboTool,
    XiaohongshuTool,
    ZhihuTool,
    get_platform_tool,
    list_platforms,
)


class TestPlatformRegistry:
    """Tests for PLATFORM_REGISTRY dict."""

    def test_contains_domestic_english_names(self):
        for name in ["xiaohongshu", "wechat", "weibo", "zhihu", "douyin", "bilibili"]:
            assert name in PLATFORM_REGISTRY, f"{name} missing from registry"

    def test_contains_domestic_chinese_names(self):
        for name in ["小红书", "微信公众号", "微博", "知乎", "抖音", "b站"]:
            assert name in PLATFORM_REGISTRY, f"{name} missing from registry"

    def test_chinese_aliases_map_to_correct_tools(self):
        assert PLATFORM_REGISTRY["小红书"] is XiaohongshuTool
        assert PLATFORM_REGISTRY["微信公众号"] is WechatTool
        assert PLATFORM_REGISTRY["微博"] is WeiboTool
        assert PLATFORM_REGISTRY["知乎"] is ZhihuTool
        assert PLATFORM_REGISTRY["抖音"] is DouyinTool
        assert PLATFORM_REGISTRY["b站"] is BilibiliTool

    def test_english_names_map_to_correct_tools(self):
        assert PLATFORM_REGISTRY["xiaohongshu"] is XiaohongshuTool
        assert PLATFORM_REGISTRY["wechat"] is WechatTool
        assert PLATFORM_REGISTRY["weibo"] is WeiboTool
        assert PLATFORM_REGISTRY["zhihu"] is ZhihuTool
        assert PLATFORM_REGISTRY["douyin"] is DouyinTool
        assert PLATFORM_REGISTRY["bilibili"] is BilibiliTool


class TestGetPlatformTool:
    """Tests for get_platform_tool() factory function."""

    @pytest.mark.parametrize("name,expected_cls", [
        ("xiaohongshu", XiaohongshuTool),
        ("wechat", WechatTool),
        ("weibo", WeiboTool),
        ("zhihu", ZhihuTool),
        ("douyin", DouyinTool),
        ("bilibili", BilibiliTool),
    ])
    def test_valid_platform_name(self, name, expected_cls):
        tool = get_platform_tool(name)
        assert isinstance(tool, expected_cls)
        assert isinstance(tool, BasePlatformTool)

    def test_case_insensitive(self):
        tool = get_platform_tool("XiaoHongShu")
        assert isinstance(tool, XiaohongshuTool)

    def test_with_chinese_name(self):
        tool = get_platform_tool("小红书")
        assert isinstance(tool, XiaohongshuTool)

    def test_with_config(self):
        config = {"api_key": "test123"}
        tool = get_platform_tool("weibo", config=config)
        assert isinstance(tool, WeiboTool)
        assert tool.config == config

    def test_invalid_platform_raises(self):
        with pytest.raises(ValueError) as exc_info:
            get_platform_tool("nonexistent_platform")
        assert "Unsupported platform" in str(exc_info.value)
        assert "nonexistent_platform" in str(exc_info.value)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            get_platform_tool("")

    def test_returns_new_instance_each_time(self):
        tool1 = get_platform_tool("weibo")
        tool2 = get_platform_tool("weibo")
        assert tool1 is not tool2


class TestListPlatforms:
    """Tests for list_platforms() function."""

    def test_domestic_only(self):
        platforms = list_platforms(domestic=True, overseas=False)
        assert platforms == DOMESTIC_PLATFORMS
        assert "xiaohongshu" in platforms
        assert "wechat" in platforms
        assert "weibo" in platforms
        assert "zhihu" in platforms
        assert "douyin" in platforms
        assert "bilibili" in platforms

    def test_domestic_default_true(self):
        platforms = list_platforms(overseas=False)
        assert len(platforms) == 6

    def test_no_platforms(self):
        platforms = list_platforms(domestic=False, overseas=False)
        assert platforms == []

    def test_overseas_only(self):
        platforms = list_platforms(domestic=False, overseas=True)
        if OVERSEAS_AVAILABLE:
            assert len(platforms) > 0
            assert "reddit" in platforms
        else:
            assert platforms == []

    def test_all_platforms(self):
        platforms = list_platforms(domestic=True, overseas=True)
        assert "xiaohongshu" in platforms
        if OVERSEAS_AVAILABLE:
            assert "reddit" in platforms


class TestAllPlatforms:
    """Tests for ALL_PLATFORMS list."""

    def test_all_platforms_is_list(self):
        assert isinstance(ALL_PLATFORMS, list)

    def test_all_platforms_contains_domestic(self):
        for p in DOMESTIC_PLATFORMS:
            assert p in ALL_PLATFORMS

    def test_domestic_platforms_constant(self):
        assert DOMESTIC_PLATFORMS == ["xiaohongshu", "wechat", "weibo", "zhihu", "douyin", "bilibili"]
