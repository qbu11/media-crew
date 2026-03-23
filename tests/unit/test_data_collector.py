"""
Unit tests for DataCollector service.

Tests cover:
- PlatformMetricsExtractor number parsing
- Platform-specific HTML extractors
- AsyncHTTPClient
- DataCollector collect_metrics
- Performance analysis
"""

from unittest.mock import AsyncMock, MagicMock, patch

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


class TestPlatformMetricsExtractor:
    def test_extract_plain_number(self):
        assert PlatformMetricsExtractor.extract_number("1234") == 1234

    def test_extract_with_commas(self):
        assert PlatformMetricsExtractor.extract_number("1,234") == 1234

    def test_extract_wan(self):
        assert PlatformMetricsExtractor.extract_number("1.2万") == 12000

    def test_extract_w(self):
        assert PlatformMetricsExtractor.extract_number("3.5w") == 35000

    def test_extract_k(self):
        assert PlatformMetricsExtractor.extract_number("5.6k") == 5600

    def test_extract_empty(self):
        assert PlatformMetricsExtractor.extract_number("") == 0

    def test_extract_no_number(self):
        assert PlatformMetricsExtractor.extract_number("abc") == 0


class TestXiaohongshuExtractor:
    def test_extract_from_html_empty(self):
        result = XiaohongshuExtractor.extract_from_html("")
        assert result["likes"] == 0
        assert result["collected"] == 0
        assert result["comments"] == 0

    def test_extract_with_data(self):
        html = """
        <span class="like-wrapper"><span class="count">1234</span></span>
        <span class="collect-wrapper"><span class="count">567</span></span>
        <span class="chat-wrapper"><span class="count">89</span></span>
        <span class="share-wrapper"><span class="count">12</span></span>
        """
        result = XiaohongshuExtractor.extract_from_html(html)
        assert "likes" in result
        assert "collected" in result
        assert "comments" in result


class TestWeiboExtractor:
    def test_extract_from_html_empty(self):
        result = WeiboExtractor.extract_from_html("")
        assert result["likes"] == 0
        assert result["shares"] == 0
        assert result["comments"] == 0


class TestZhihuExtractor:
    def test_extract_from_html_empty(self):
        result = ZhihuExtractor.extract_from_html("")
        assert result["likes"] == 0
        assert result["comments"] == 0

    def test_extract_with_data(self):
        html = """
        <meta itemprop="upvoteCount" content="500">
        <meta itemprop="commentCount" content="42">
        """
        result = ZhihuExtractor.extract_from_html(html)
        assert "likes" in result


class TestAsyncHTTPClient:
    async def test_get_page_success(self):
        client = AsyncHTTPClient(timeout=5)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>test</html>"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            html = await client.get_page_html("https://example.com")
            assert html == "<html>test</html>"

    async def test_get_page_error(self):
        client = AsyncHTTPClient(timeout=5)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("timeout")):
            html = await client.get_page_html("https://example.com")
            assert html == ""


class TestDataCollector:
    def test_init(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        assert collector.http_client is not None

    async def test_collect_metrics_unknown_platform(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")
        result = await collector.collect_metrics("unknown_platform", "https://example.com")
        assert result.success is False

    async def test_collect_metrics_xiaohongshu(self):
        collector = DataCollector(db_url="sqlite+aiosqlite:///:memory:")

        with patch.object(
            collector.http_client, "get_page_html",
            new_callable=AsyncMock,
            return_value="<html><span class='like-wrapper'><span class='count'>100</span></span></html>",
        ):
            result = await collector.collect_metrics("xiaohongshu", "https://xiaohongshu.com/post/123")
            assert isinstance(result.success, bool)


class TestAnalyzePerformance:
    def test_analyze_basic(self):
        metrics_history = [
            {"likes": 50, "comments": 10, "shares": 5, "views": 500},
            {"likes": 100, "comments": 20, "shares": 10, "views": 1000},
        ]
        result = analyze_content_performance(metrics_history)
        assert "latest_likes" in result
        assert "likes_growth_rate" in result

    def test_analyze_single_entry(self):
        metrics_history = [{"likes": 10, "comments": 5, "views": 100}]
        result = analyze_content_performance(metrics_history)
        assert result["latest_likes"] == 10
        assert result["likes_growth_rate"] == 0

    def test_analyze_empty(self):
        result = analyze_content_performance([])
        assert "error" in result


class TestSingleton:
    def test_get_data_collector(self):
        import src.services.data_collector as mod
        mod._data_collector = None
        dc = get_data_collector()
        assert isinstance(dc, DataCollector)
        dc2 = get_data_collector()
        assert dc is dc2
        mod._data_collector = None
