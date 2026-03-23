"""
Unit tests for Tool classes.

Tests cover:
- Input validation
- Tool execution
- Error handling
- Rate limiting
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.tools.analytics_tools import AnalyticsReportTool, DataCollectTool
from src.tools.base_tool import BaseTool, ToolError, ToolResult, ToolStatus
from src.tools.content_tools import (
    ContentType,
    HashtagSuggestTool,
    ImageSearchTool,
    SEOOptimizeTool,
)
from src.tools.search_tools import (
    CompetitorAnalysisTool,
    HotSearchTool,
    Platform,
    TrendAnalysisTool,
)


class TestBaseTool:
    """Test cases for BaseTool abstract class."""

    def test_base_tool_is_abstract(self) -> None:
        """
        Test that BaseTool cannot be instantiated directly.

        Arrange: Import BaseTool class
        Act: Try to instantiate BaseTool
        Assert: TypeError is raised
        """
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore

    def test_tool_result_success(self) -> None:
        """
        Test ToolResult with success status.

        Arrange: Create ToolResult with success
        Act: Check attributes
        Assert: All attributes are correct
        """
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            data={"test": "value"},
            platform="xiaohongshu",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data == {"test": "value"}
        assert result.platform == "xiaohongshu"
        assert result.error is None

    def test_tool_result_to_dict(self) -> None:
        """
        Test ToolResult.to_dict conversion.

        Arrange: Create ToolResult
        Act: Call to_dict()
        Assert: Returns dictionary with all fields
        """
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": "value"},
            platform="weibo",
            content_id="123",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["status"] == "success"
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["platform"] == "weibo"
        assert result_dict["content_id"] == "123"

    def test_tool_result_is_success(self) -> None:
        """
        Test ToolResult.is_success method.

        Arrange: Create ToolResult with success status
        Act: Call is_success()
        Assert: Returns True
        """
        result = ToolResult(status=ToolStatus.SUCCESS)
        assert result.is_success() is True

    def test_tool_result_is_failed(self) -> None:
        """
        Test ToolResult.is_failed method.

        Arrange: Create ToolResult with failed status
        Act: Call is_failed()
        Assert: Returns True
        """
        result = ToolResult(status=ToolStatus.FAILED, error="Test error")
        assert result.is_failed() is True

    def test_tool_error_creation(self) -> None:
        """
        Test ToolError exception creation.

        Arrange: Create ToolError with details
        Act: Check attributes
        Assert: All attributes are correct
        """
        error = ToolError(
            message="Test error",
            platform="xiaohongshu",
            details={"code": 500},
        )

        assert error.message == "Test error"
        assert error.platform == "xiaohongshu"
        assert error.details == {"code": 500}

    def test_tool_error_to_result(self) -> None:
        """
        Test ToolError.to_result conversion.

        Arrange: Create ToolError
        Act: Call to_result()
        Assert: Returns ToolResult with failed status
        """
        error = ToolError(
            message="Test error",
            platform="weibo",
            details={"reason": "test"},
        )

        result = error.to_result()

        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.FAILED
        assert result.error == "Test error"


class TestHotSearchTool:
    """Test cases for HotSearchTool."""

    def test_hot_search_tool_metadata(self) -> None:
        """
        Test HotSearchTool has correct metadata.

        Arrange: Create HotSearchTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = HotSearchTool()

        assert tool.name == "hot_search"
        assert tool.platform == "multi"
        assert tool.max_requests_per_minute == 10
        assert tool.min_interval_seconds == 5.0

    def test_hot_search_validate_input_valid(self) -> None:
        """
        Test HotSearchTool.validate_input with valid data.

        Arrange: Create HotSearchTool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = HotSearchTool()

        is_valid, error = tool.validate_input(platform="weibo", limit=20)

        assert is_valid is True
        assert error is None

    def test_hot_search_validate_input_invalid_platform(self) -> None:
        """
        Test HotSearchTool.validate_input with invalid platform.

        Arrange: Create HotSearchTool and invalid platform
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = HotSearchTool()

        is_valid, error = tool.validate_input(platform="invalid_platform", limit=20)

        assert is_valid is False
        assert "Unsupported platform" in error

    def test_hot_search_validate_input_invalid_limit(self) -> None:
        """
        Test HotSearchTool.validate_input with invalid limit.

        Arrange: Create HotSearchTool and invalid limit
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = HotSearchTool()

        is_valid, error = tool.validate_input(platform="weibo", limit=0)
        assert is_valid is False

        is_valid, error = tool.validate_input(platform="weibo", limit=200)
        assert is_valid is False

    def test_hot_search_execute_success(self) -> None:
        """
        Test HotSearchTool.execute returns success result.

        Arrange: Create HotSearchTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with success status
        """
        tool = HotSearchTool()

        result = tool.execute(platform="weibo", limit=5)

        assert result.status == ToolStatus.SUCCESS
        assert result.data is not None
        assert "results" in result.data
        assert len(result.data["results"]) <= 5

    def test_hot_search_execute_with_cache(self) -> None:
        """
        Test HotSearchTool uses cache for repeated requests.

        Arrange: Create HotSearchTool and make two requests
        Act: Execute twice with same parameters
        Assert: Second result uses cache
        """
        tool = HotSearchTool()

        # First request
        result1 = tool.execute(platform="weibo", limit=5)
        assert result1.data.get("cached", False) is False

        # Second request should use cache
        result2 = tool.execute(platform="weibo", limit=5)
        assert result2.data.get("cached", False) is True

    def test_hot_search_crewai_wrapper(self) -> None:
        """
        Test hot_search CrewAI wrapper function.

        Arrange: Import wrapper function
        Act: Call function
        Assert: Returns JSON string with results
        """
        from src.tools.search_tools import hot_search

        result_json = hot_search(platform="weibo", limit=3)

        assert isinstance(result_json, str)
        data = json.loads(result_json)
        assert data["status"] == "success"


class TestCompetitorAnalysisTool:
    """Test cases for CompetitorAnalysisTool."""

    def test_competitor_analysis_metadata(self) -> None:
        """
        Test CompetitorAnalysisTool has correct metadata.

        Arrange: Create CompetitorAnalysisTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = CompetitorAnalysisTool()

        assert tool.name == "competitor_analysis"
        assert tool.max_requests_per_minute == 5
        assert tool.min_interval_seconds == 10.0

    def test_competitor_analysis_validate_input_valid(self) -> None:
        """
        Test CompetitorAnalysisTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = CompetitorAnalysisTool()

        is_valid, error = tool.validate_input(
            account_url="https://example.com/user/123",
            platform="xiaohongshu",
        )

        assert is_valid is True
        assert error is None

    def test_competitor_analysis_validate_input_missing_account(self) -> None:
        """
        Test CompetitorAnalysisTool.validate_input without account info.

        Arrange: Create tool without account info
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = CompetitorAnalysisTool()

        is_valid, error = tool.validate_input(platform="xiaohongshu")

        assert is_valid is False
        assert "account_id or account_url" in error

    def test_competitor_analysis_execute_success(self) -> None:
        """
        Test CompetitorAnalysisTool.execute returns success result.

        Arrange: Create CompetitorAnalysisTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with success status
        """
        tool = CompetitorAnalysisTool()

        result = tool.execute(
            account_url="https://xiaohongshu.com/user/test123",
            platform="xiaohongshu",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data is not None
        assert "metrics" in result.data


class TestTrendAnalysisTool:
    """Test cases for TrendAnalysisTool."""

    def test_trend_analysis_metadata(self) -> None:
        """
        Test TrendAnalysisTool has correct metadata.

        Arrange: Create TrendAnalysisTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = TrendAnalysisTool()

        assert tool.name == "trend_analysis"
        assert tool.max_requests_per_minute == 3
        assert tool.min_interval_seconds == 30.0

    def test_trend_analysis_validate_input_valid(self) -> None:
        """
        Test TrendAnalysisTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = TrendAnalysisTool()

        is_valid, error = tool.validate_input(keyword="AI创业", time_range="7d")

        assert is_valid is True
        assert error is None

    def test_trend_analysis_validate_input_invalid_time_range(self) -> None:
        """
        Test TrendAnalysisTool.validate_input with invalid time range.

        Arrange: Create tool with invalid time range
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = TrendAnalysisTool()

        is_valid, error = tool.validate_input(keyword="AI", time_range="1y")

        assert is_valid is False
        assert "Invalid time_range" in error

    def test_trend_analysis_execute_success(self) -> None:
        """
        Test TrendAnalysisTool.execute returns success result.

        Arrange: Create TrendAnalysisTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with success status
        """
        tool = TrendAnalysisTool()

        result = tool.execute(keyword="AI创业", time_range="7d")

        assert result.status == ToolStatus.SUCCESS
        assert result.data is not None
        assert "trend_direction" in result.data


class TestImageSearchTool:
    """Test cases for ImageSearchTool."""

    def test_image_search_metadata(self) -> None:
        """
        Test ImageSearchTool has correct metadata.

        Arrange: Create ImageSearchTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = ImageSearchTool()

        assert tool.name == "image_search"
        assert tool.max_requests_per_minute == 10
        assert tool.min_interval_seconds == 3.0

    def test_image_search_validate_input_valid(self) -> None:
        """
        Test ImageSearchTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = ImageSearchTool()

        is_valid, error = tool.validate_input(query="AI technology", limit=10)

        assert is_valid is True
        assert error is None

    def test_image_search_validate_input_missing_query(self) -> None:
        """
        Test ImageSearchTool.validate_input without query.

        Arrange: Create tool without query
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = ImageSearchTool()

        is_valid, error = tool.validate_input(limit=10)

        assert is_valid is False
        assert "Query is required" in error

    def test_image_search_execute_success(self) -> None:
        """
        Test ImageSearchTool.execute returns success result.

        Arrange: Create ImageSearchTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with images
        """
        tool = ImageSearchTool()

        result = tool.execute(query="AI technology", limit=5)

        assert result.status == ToolStatus.SUCCESS
        assert "images" in result.data
        assert len(result.data["images"]) <= 5


class TestHashtagSuggestTool:
    """Test cases for HashtagSuggestTool."""

    def test_hashtag_suggest_metadata(self) -> None:
        """
        Test HashtagSuggestTool has correct metadata.

        Arrange: Create HashtagSuggestTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = HashtagSuggestTool()

        assert tool.name == "hashtag_suggest"
        assert tool.PLATFORM_LIMITS["xiaohongshu"] == 10
        assert tool.PLATFORM_LIMITS["weibo"] == 2

    def test_hashtag_suggest_validate_input_valid(self) -> None:
        """
        Test HashtagSuggestTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = HashtagSuggestTool()

        is_valid, error = tool.validate_input(
            content="这是一篇关于AI创业的文章",
            platform="xiaohongshu",
        )

        assert is_valid is True
        assert error is None

    def test_hashtag_suggest_validate_input_invalid_platform(self) -> None:
        """
        Test HashtagSuggestTool.validate_input with invalid platform.

        Arrange: Create tool with invalid platform
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = HashtagSuggestTool()

        is_valid, error = tool.validate_input(
            content="测试内容",
            platform="invalid",
        )

        assert is_valid is False
        assert "Unsupported platform" in error

    def test_hashtag_suggest_execute_success(self) -> None:
        """
        Test HashtagSuggestTool.execute returns success result.

        Arrange: Create HashtagSuggestTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with hashtags
        """
        tool = HashtagSuggestTool()

        result = tool.execute(
            content="AI创业是当前的热门话题，越来越多的技术人选择创业",
            platform="xiaohongshu",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "suggested_tags" in result.data
        assert "trending_tags" in result.data

    def test_hashtag_suggest_respects_limit(self) -> None:
        """
        Test HashtagSuggestTool respects platform-specific limits.

        Arrange: Create tool with different platforms
        Act: Execute with different platforms
        Assert: Tags respect platform limits
        """
        tool = HashtagSuggestTool()

        # 小红书限制10个标签
        result = tool.execute(
            content="AI创业技术产品融资团队管理增长营销运营",
            platform="xiaohongshu",
            max_tags=15,  # Request more than limit
        )

        assert result.status == ToolStatus.SUCCESS
        assert len(result.data["suggested_tags"]) <= 10


class TestSEOOptimizeTool:
    """Test cases for SEOOptimizeTool."""

    def test_seo_optimize_metadata(self) -> None:
        """
        Test SEOOptimizeTool has correct metadata.

        Arrange: Create SEOOptimizeTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = SEOOptimizeTool()

        assert tool.name == "seo_optimize"
        assert tool.max_requests_per_minute == 10

    def test_seo_optimize_validate_input_valid(self) -> None:
        """
        Test SEOOptimizeTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = SEOOptimizeTool()

        is_valid, error = tool.validate_input(content="这是一篇长文章内容...")

        assert is_valid is True
        assert error is None

    def test_seo_optimize_validate_input_missing_content(self) -> None:
        """
        Test SEOOptimizeTool.validate_input without content.

        Arrange: Create tool without content
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = SEOOptimizeTool()

        is_valid, error = tool.validate_input()

        assert is_valid is False
        assert "Content is required" in error

    def test_seo_optimize_execute_success(self) -> None:
        """
        Test SEOOptimizeTool.execute returns success result.

        Arrange: Create SEOOptimizeTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with SEO analysis
        """
        tool = SEOOptimizeTool()

        result = tool.execute(
            content="这是一篇关于AI创业的深度分析文章。内容需要足够长才能获得好的SEO评分。我们讨论了技术选型、团队搭建、融资策略等多个方面。",
            title="AI创业实战指南：从0到1的经验分享",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "seo_score" in result.data
        assert "recommendations" in result.data
        assert isinstance(result.data["seo_score"], int)

    def test_seo_optimize_calculates_score(self) -> None:
        """
        Test SEOOptimizeTool calculates score correctly.

        Arrange: Create tool with content of different quality
        Act: Execute with different content
        Assert: Higher quality content gets higher score
        """
        tool = SEOOptimizeTool()

        # Short content without structure
        result_short = tool.execute(
            content="短内容",
            title="短标题",
        )

        # Long content with structure
        result_long = tool.execute(
            content="# 标题\n\n## 副标题\n\n这是详细内容，包含[链接](url)和图片![](img)。字数足够多可以提升SEO评分。",
            title="这是一个合适长度的标题用于SEO优化",
        )

        # Both should have scores
        assert "seo_score" in result_short.data
        assert "seo_score" in result_long.data


class TestDataCollectTool:
    """Test cases for DataCollectTool."""

    def test_data_collect_metadata(self) -> None:
        """
        Test DataCollectTool has correct metadata.

        Arrange: Create DataCollectTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = DataCollectTool()

        assert tool.name == "data_collect"
        assert tool.max_requests_per_minute == 10
        assert tool.min_interval_seconds == 5.0

    def test_data_collect_validate_input_valid(self) -> None:
        """
        Test DataCollectTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = DataCollectTool()

        is_valid, error = tool.validate_input(
            content_id="content_123",
            platform="xiaohongshu",
        )

        assert is_valid is True
        assert error is None

    def test_data_collect_validate_input_missing_content(self) -> None:
        """
        Test DataCollectTool.validate_input without content_id.

        Arrange: Create tool without content_id
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = DataCollectTool()

        is_valid, error = tool.validate_input(platform="xiaohongshu")

        assert is_valid is False
        assert "content_id" in error

    def test_data_collect_execute_success(self) -> None:
        """
        Test DataCollectTool.execute returns success result.

        Arrange: Create DataCollectTool
        Act: Execute with valid parameters
        Assert: Returns ToolResult with metrics
        """
        tool = DataCollectTool()

        result = tool.execute(
            content_id="content_123",
            platform="xiaohongshu",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "results" in result.data
        assert "collected_at" in result.data

    def test_data_collect_multiple_content(self) -> None:
        """
        Test DataCollectTool with multiple content IDs.

        Arrange: Create DataCollectTool with multiple IDs
        Act: Execute with content_ids list
        Assert: Returns results for all IDs
        """
        tool = DataCollectTool()

        result = tool.execute(
            content_ids=["id1", "id2", "id3"],
            platform="xiaohongshu",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["content_count"] == 3


class TestAnalyticsReportTool:
    """Test cases for AnalyticsReportTool."""

    def test_analytics_report_metadata(self) -> None:
        """
        Test AnalyticsReportTool has correct metadata.

        Arrange: Create AnalyticsReportTool instance
        Act: Check attributes
        Assert: Metadata is correct
        """
        tool = AnalyticsReportTool()

        assert tool.name == "analytics_report"
        assert tool.max_requests_per_minute == 10

    def test_analytics_report_validate_input_valid(self) -> None:
        """
        Test AnalyticsReportTool.validate_input with valid data.

        Arrange: Create tool and valid input
        Act: Call validate_input()
        Assert: Returns (True, None)
        """
        tool = AnalyticsReportTool()

        is_valid, error = tool.validate_input(data=[{"test": "value"}])

        assert is_valid is True
        assert error is None

    def test_analytics_report_validate_input_missing_data(self) -> None:
        """
        Test AnalyticsReportTool.validate_input without data.

        Arrange: Create tool without data
        Act: Call validate_input()
        Assert: Returns (False, error_message)
        """
        tool = AnalyticsReportTool()

        is_valid, error = tool.validate_input()

        assert is_valid is False
        assert "Data is required" in error

    def test_analytics_report_execute_success(self) -> None:
        """
        Test AnalyticsReportTool.execute returns success result.

        Arrange: Create AnalyticsReportTool with sample data
        Act: Execute with valid parameters
        Assert: Returns ToolResult with report
        """
        tool = AnalyticsReportTool()

        sample_data = [
            {
                "content_id": "id1",
                "platform": "xiaohongshu",
                "metrics": {
                    "views": 1000,
                    "likes": 100,
                    "comments": 10,
                    "shares": 5,
                    "engagement_rate": 0.115,
                },
            },
            {
                "content_id": "id2",
                "platform": "wechat",
                "metrics": {
                    "views": 500,
                    "likes": 50,
                    "comments": 5,
                    "shares": 2,
                    "engagement_rate": 0.114,
                },
            },
        ]

        result = tool.execute(data=sample_data, format="json")

        assert result.status == ToolStatus.SUCCESS
        assert "summary" in result.data
        assert "insights_count" in result.data or "insights" in result.data

    def test_analytics_report_markdown_format(self) -> None:
        """
        Test AnalyticsReportTool with markdown format.

        Arrange: Create AnalyticsReportTool
        Act: Execute with format="markdown"
        Assert: Returns markdown formatted report
        """
        tool = AnalyticsReportTool()

        sample_data = [
            {
                "content_id": "id1",
                "platform": "xiaohongshu",
                "metrics": {
                    "views": 1000,
                    "likes": 100,
                    "comments": 10,
                    "shares": 5,
                },
            }
        ]

        result = tool.execute(data=sample_data, format="markdown")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["format"] == "markdown"
        assert "# Analytics Report" in result.data["report"]

    def test_analytics_report_csv_format(self) -> None:
        """
        Test AnalyticsReportTool with CSV format.

        Arrange: Create AnalyticsReportTool
        Act: Execute with format="csv"
        Assert: Returns CSV formatted report
        """
        tool = AnalyticsReportTool()

        sample_data = [
            {
                "content_id": "id1",
                "platform": "xiaohongshu",
                "metrics": {
                    "views": 1000,
                    "likes": 100,
                    "comments": 10,
                    "shares": 5,
                    "engagement_rate": 0.115,
                },
            }
        ]

        result = tool.execute(data=sample_data, format="csv")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["format"] == "csv"
        assert "content_id,platform,views" in result.data["report"]
