"""
Extra tests for data_collector module.

Covers:
- PlatformMetricsExtractor.extract_number (all formats)
- XiaohongshuExtractor.extract_from_html
- WeiboExtractor.extract_from_html
- ZhihuExtractor.extract_from_html
- AsyncHTTPClient.get_page_html (error paths)
- DataCollector.collect_metrics (unsupported platform, empty html, success)
- DataCollector.batch_collect
- analyze_content_performance
- get_data_collector singleton
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.data_collector import (
    AsyncHTTPClient,
    DataCollector,
    PlatformMetricsExtractor,
    WeiboExtractor,
    XiaohongshuExtractor,
    ZhihuExtractor,
    analyze_content_performance,
    get_data_collector,
)


# ============ PlatformMetricsExtractor ============


class TestExtractNumber:
    def test_empty(self):
        assert PlatformMetricsExtractor.extract_number("") == 0

    def test_plain_number(self):
        assert PlatformMetricsExtractor.extract_number("123") == 123

    def test_with_comma(self):
        assert PlatformMetricsExtractor.extract_number("1,234") == 1234

    def test_wan_format(self):
        assert PlatformMetricsExtractor.extract_number("1.2万") == 12000

    def test_w_format(self):
        assert PlatformMetricsExtractor.extract_number("3.5w") == 35000

    def test_W_format(self):
        assert PlatformMetricsExtractor.extract_number("2.0W") == 20000

    def test_k_format(self):
        assert PlatformMetricsExtractor.extract_number("5.5k") == 5500

    def test_K_format(self):
        assert PlatformMetricsExtractor.extract_number("1.0K") == 1000

    def test_no_number(self):
        assert PlatformMetricsExtractor.extract_number("abc") == 0

    def test_with_spaces(self):
        assert PlatformMetricsExtractor.extract_number("  42  ") == 42


# ============ XiaohongshuExtractor ============


class TestXiaohongshuExtractor:
    def test_extract_likes(self):
        html = "点赞 1.2万"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["likes"] == 12000

    def test_extract_likes_reversed(self):
        html = "999 点赞"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["likes"] == 999

    def test_extract_comments(self):
        html = "评论 500"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["comments"] == 500

    def test_extract_comments_reversed(self):
        html = "42 评论"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["comments"] == 42

    def test_extract_shares(self):
        html = "收藏 300"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["shares"] == 300
        assert result["collected"] == 300

    def test_extract_shares_reversed(self):
        html = "88 收藏"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["shares"] == 88

    def test_empty_html(self):
        result = XiaohongshuExtractor.extract_from_html("")
        assert result["likes"] == 0
        assert result["comments"] == 0
        assert result["shares"] == 0
        assert result["views"] == 0

    def test_initial_state_json(self):
        html = 'window.__INITIAL_STATE__ = {"test": 1};'
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["views"] == 0  # Still 0, but code path exercised

    def test_initial_state_invalid_json(self):
        html = "window.__INITIAL_STATE__ = {invalid json};"
        result = XiaohongshuExtractor.extract_from_html(html)
        assert result["views"] == 0


# ============ WeiboExtractor ============


class TestWeiboExtractor:
    def test_extract_views(self):
        html = "阅读 1.5万"
        result = WeiboExtractor.extract_from_html(html)
        assert result["views"] == 15000

    def test_extract_likes(self):
        html = "赞 (42)"
        result = WeiboExtractor.extract_from_html(html)
        assert result["likes"] == 42

    def test_extract_comments(self):
        html = "评论 (100)"
        result = WeiboExtractor.extract_from_html(html)
        assert result["comments"] == 100

    def test_extract_shares(self):
        html = "转发 (25)"
        result = WeiboExtractor.extract_from_html(html)
        assert result["shares"] == 25

    def test_all_metrics(self):
        html = "阅读 5000 赞 (10) 评论 (5) 转发 (3)"
        result = WeiboExtractor.extract_from_html(html)
        assert result["views"] == 5000
        assert result["likes"] == 10
        assert result["comments"] == 5
        assert result["shares"] == 3

    def test_empty_html(self):
        result = WeiboExtractor.extract_from_html("")
        assert all(v == 0 for v in result.values())


# ============ ZhihuExtractor ============


class TestZhihuExtractor:
    def test_extract_views(self):
        html = '"viewCount": 5000'
        result = ZhihuExtractor.extract_from_html(html)
        assert result["views"] == 5000

    def test_extract_likes(self):
        html = '"voteupCount": 200'
        result = ZhihuExtractor.extract_from_html(html)
        assert result["likes"] == 200

    def test_extract_comments(self):
        html = '"commentCount": 30'
        result = ZhihuExtractor.extract_from_html(html)
        assert result["comments"] == 30

    def test_all_metrics(self):
        html = '"viewCount": 10000, "voteupCount": 500, "commentCount": 100'
        result = ZhihuExtractor.extract_from_html(html)
        assert result["views"] == 10000
        assert result["likes"] == 500
        assert result["comments"] == 100

    def test_empty_html(self):
        result = ZhihuExtractor.extract_from_html("")
        assert all(v == 0 for v in result.values())


# ============ AsyncHTTPClient ============


class TestAsyncHTTPClient:
    @pytest.mark.asyncio
    async def test_get_page_html_success(self):
        client = AsyncHTTPClient(timeout=5)
        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await client.get_page_html("http://example.com")
            assert result == "<html>Test</html>"

    @pytest.mark.asyncio
    async def test_get_page_html_timeout(self):
        client = AsyncHTTPClient(timeout=1)

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await client.get_page_html("http://example.com")
            assert result == ""

    @pytest.mark.asyncio
    async def test_get_page_html_http_error(self):
        client = AsyncHTTPClient(timeout=5)

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404", request=mock_request, response=mock_response
                )
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await client.get_page_html("http://example.com")
            assert result == ""

    @pytest.mark.asyncio
    async def test_get_page_html_generic_error(self):
        client = AsyncHTTPClient(timeout=5)

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=ConnectionError("fail"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await client.get_page_html("http://example.com")
            assert result == ""


# ============ DataCollector ============


class TestDataCollector:
    @pytest.mark.asyncio
    async def test_collect_metrics_unsupported_platform(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        result = await collector.collect_metrics("tiktok", "http://example.com")
        assert not result.success
        assert "不支持的平台" in result.error

    @pytest.mark.asyncio
    async def test_collect_metrics_empty_html(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        collector.http_client.get_page_html = AsyncMock(return_value="")
        result = await collector.collect_metrics("xiaohongshu", "http://example.com")
        assert not result.success
        assert "无法获取页面内容" in result.error

    @pytest.mark.asyncio
    async def test_collect_metrics_success(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        html = "点赞 100 评论 50 收藏 30"
        collector.http_client.get_page_html = AsyncMock(return_value=html)
        result = await collector.collect_metrics("xiaohongshu", "http://example.com")
        assert result.success
        assert result.data["likes"] == 100
        assert result.data["comments"] == 50
        assert result.data["shares"] == 30

    @pytest.mark.asyncio
    async def test_collect_metrics_weibo(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        html = "阅读 2000 赞 (10) 评论 (5) 转发 (3)"
        collector.http_client.get_page_html = AsyncMock(return_value=html)
        result = await collector.collect_metrics("weibo", "http://example.com")
        assert result.success
        assert result.data["views"] == 2000

    @pytest.mark.asyncio
    async def test_batch_collect_skips_no_url(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        contents = [
            {"id": "1", "platform": "xiaohongshu"},  # No publish_url
            {"id": "2", "platform": "xiaohongshu", "publish_url": ""},
        ]
        results = await collector.batch_collect(contents)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_batch_collect_with_error(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        collector.collect_and_save = AsyncMock(side_effect=Exception("DB error"))
        contents = [
            {"id": "1", "platform": "xiaohongshu", "publish_url": "http://example.com"},
        ]
        results = await collector.batch_collect(contents)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "DB error" in results[0]["error"]


# ============ analyze_content_performance ============


class TestAnalyzeContentPerformance:
    def test_empty_history(self):
        result = analyze_content_performance([])
        assert result == {"error": "No data"}

    def test_single_entry(self):
        result = analyze_content_performance([{"likes": 100, "views": 500}])
        assert result["latest_likes"] == 100
        assert result["latest_views"] == 500
        assert result["likes_growth_rate"] == 0
        assert result["is_trending"] is False

    def test_two_entries_growth(self):
        result = analyze_content_performance([
            {"likes": 100, "views": 500},
            {"likes": 200, "views": 1000},
        ])
        assert result["latest_likes"] == 200
        assert result["latest_views"] == 1000
        assert result["likes_growth_rate"] == 100.0
        assert result["views_growth_rate"] == 100.0
        assert result["is_trending"] is True

    def test_two_entries_no_growth(self):
        result = analyze_content_performance([
            {"likes": 100, "views": 500},
            {"likes": 110, "views": 520},
        ])
        assert result["is_trending"] is False

    def test_zero_previous_likes(self):
        """Division by zero protection: max(previous["likes"], 1)"""
        result = analyze_content_performance([
            {"likes": 0, "views": 0},
            {"likes": 50, "views": 100},
        ])
        assert result["likes_growth_rate"] == 5000.0
        assert result["views_growth_rate"] == 10000.0

    def test_trending_by_likes_only(self):
        result = analyze_content_performance([
            {"likes": 100, "views": 1000},
            {"likes": 200, "views": 1010},
        ])
        assert result["is_trending"] is True  # likes_growth > 50%

    def test_trending_by_views_only(self):
        result = analyze_content_performance([
            {"likes": 100, "views": 100},
            {"likes": 110, "views": 200},
        ])
        assert result["is_trending"] is True  # views_growth > 50%

    def test_missing_views(self):
        """Views key missing uses .get default 0"""
        result = analyze_content_performance([
            {"likes": 10},
            {"likes": 20},
        ])
        assert result["latest_views"] == 0


# ============ get_data_collector ============


class TestGetDataCollector:
    def test_singleton(self):
        import src.services.data_collector as dc_mod

        dc_mod._data_collector = None
        c1 = get_data_collector()
        c2 = get_data_collector()
        assert c1 is c2
        dc_mod._data_collector = None  # Reset
