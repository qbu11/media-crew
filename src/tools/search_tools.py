"""
Search Tools for Content Discovery

Provides tools for:
- Hot search/trending topics across platforms
- Competitor analysis
- Trend analysis and prediction
"""

from datetime import datetime, timedelta
from enum import Enum
import json
from typing import Any

from .base_tool import BaseTool, ToolResult, ToolStatus


class Platform(Enum):
    """Supported platforms for search"""
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    ZHIHU = "zhihu"


class HotSearchTool(BaseTool):
    """
    Tool for fetching hot search/trending topics from various platforms.

    Uses platform APIs or web scraping to get trending topics.
    """

    name = "hot_search"
    description = "Fetches hot search and trending topics from Chinese social media platforms"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 10
    min_interval_seconds = 5.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._tikhub_token = self.config.get("tikhub_token")
        self._cache: dict[str, tuple[list[dict], datetime]] = {}
        self._cache_ttl = timedelta(minutes=10)

    def _get_cached(self, key: str) -> list[dict] | None:
        """Get cached results if still valid"""
        if key in self._cache:
            results, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return results
        return None

    def _set_cache(self, key: str, results: list[dict]) -> None:
        """Cache results with timestamp"""
        self._cache[key] = (results, datetime.now())

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        platform_str = kwargs.get("platform", "weibo")
        try:
            Platform(platform_str.lower())
        except ValueError:
            return False, f"Unsupported platform: {platform_str}"

        limit = kwargs.get("limit", 20)
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return False, "Limit must be between 1 and 100"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Fetch hot search results.

        Args:
            platform: Platform name (xiaohongshu, weibo, douyin, bilibili, zhihu)
            limit: Maximum number of results (default: 20)
            category: Optional category filter

        Returns:
            ToolResult with hot search data
        """
        platform_str = kwargs.get("platform", "weibo").lower()
        limit = kwargs.get("limit", 20)
        category = kwargs.get("category")

        try:
            platform = Platform(platform_str)
            cache_key = f"{platform.value}_{category or 'all'}"

            # Check cache
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"results": cached[:limit], "cached": True},
                    platform=platform.value
                )

            # Fetch from platform
            results = self._fetch_from_platform(platform, limit, category)
            self._set_cache(cache_key, results)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "results": results[:limit],
                    "platform": platform.value,
                    "fetched_at": datetime.now().isoformat(),
                    "total": len(results)
                },
                platform=platform.value
            )

        except ValueError as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=str(e),
                platform=platform_str
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Failed to fetch hot search: {e!s}",
                platform=platform_str
            )

    def _fetch_from_platform(
        self,
        platform: Platform,
        limit: int,
        category: str | None
    ) -> list[dict]:
        """Fetch hot search from specific platform"""
        # In actual implementation, this would:
        # - Use platform APIs (TikHub, etc.)
        # - Or use web scraping via Chrome DevTools MCP
        # - Normalize results to common format

        # Simulated results for now
        return [
            {
                "rank": i + 1,
                "keyword": f"热门话题{i + 1}",
                "heat": 1000000 - i * 50000,
                "category": category or "综合",
                "url": f"https://{platform.value}.com/search?keyword=话题{i + 1}"
            }
            for i in range(limit)
        ]


class CompetitorAnalysisTool(BaseTool):
    """
    Tool for analyzing competitor content.

    Fetches and analyzes content from competitor accounts.
    """

    name = "competitor_analysis"
    description = "Analyzes competitor content and performance metrics"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 5
    min_interval_seconds = 10.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._tikhub_token = self.config.get("tikhub_token")

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        if "account_id" not in kwargs and "account_url" not in kwargs:
            return False, "Either account_id or account_url is required"

        platform_str = kwargs.get("platform", "xiaohongshu")
        try:
            Platform(platform_str.lower())
        except ValueError:
            return False, f"Unsupported platform: {platform_str}"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Analyze competitor account.

        Args:
            account_id: Platform-specific account ID
            account_url: Full URL to account page
            platform: Platform name
            content_limit: Number of recent posts to analyze (default: 20)

        Returns:
            ToolResult with analysis data
        """
        platform_str = kwargs.get("platform", "xiaohongshu").lower()
        account_id = kwargs.get("account_id")
        account_url = kwargs.get("account_url")
        content_limit = kwargs.get("content_limit", 20)

        try:
            platform = Platform(platform_str)

            # In actual implementation:
            # 1. Fetch account profile
            # 2. Fetch recent content
            # 3. Analyze metrics (engagement rate, best posting times, etc.)
            # 4. Generate insights

            analysis = {
                "account_id": account_id or self._extract_id_from_url(account_url),
                "platform": platform.value,
                "content_analyzed": content_limit,
                "metrics": {
                    "avg_likes": 0,
                    "avg_comments": 0,
                    "avg_shares": 0,
                    "engagement_rate": 0.0,
                    "posting_frequency": "daily"
                },
                "top_topics": [],
                "best_posting_times": [],
                "content_themes": [],
                "recommendations": []
            }

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=analysis,
                platform=platform.value
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Analysis failed: {e!s}",
                platform=platform_str
            )

    def _extract_id_from_url(self, url: str) -> str:
        """Extract account ID from URL"""
        # Simple implementation
        return url.split("/")[-1] if url else "unknown"


class TrendAnalysisTool(BaseTool):
    """
    Tool for analyzing content trends across platforms.

    Identifies trending topics, hashtags, and content patterns.
    """

    name = "trend_analysis"
    description = "Analyzes content trends and predicts hot topics"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 3
    min_interval_seconds = 30.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._tikhub_token = self.config.get("tikhub_token")

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        keyword = kwargs.get("keyword")
        category = kwargs.get("category")

        if not keyword and not category:
            return False, "Either keyword or category is required"

        time_range = kwargs.get("time_range", "7d")
        valid_ranges = ["24h", "7d", "30d", "90d"]
        if time_range not in valid_ranges:
            return False, f"Invalid time_range. Must be one of: {', '.join(valid_ranges)}"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Analyze trends for a keyword or category.

        Args:
            keyword: Keyword to analyze
            category: Category to analyze
            time_range: Time range for analysis (24h, 7d, 30d, 90d)
            platforms: List of platforms to include

        Returns:
            ToolResult with trend analysis
        """
        keyword = kwargs.get("keyword")
        category = kwargs.get("category")
        time_range = kwargs.get("time_range", "7d")
        platforms = kwargs.get("platforms", ["weibo", "xiaohongshu", "douyin"])

        try:
            # In actual implementation:
            # 1. Search for keyword/category across platforms
            # 2. Analyze engagement patterns
            # 3. Identify trend direction (rising, stable, declining)
            # 4. Generate predictions

            analysis = {
                "keyword": keyword,
                "category": category,
                "time_range": time_range,
                "platforms": platforms,
                "trend_direction": "rising",
                "trend_score": 75.5,
                "related_topics": [],
                "peak_times": [],
                "demographics": {},
                "predictions": []
            }

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=analysis,
                platform="multi"
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Trend analysis failed: {e!s}",
                platform="multi"
            )


# CrewAI tool wrappers

def hot_search(platform: str = "weibo", limit: int = 20) -> str:
    """
    Fetch hot search topics from a platform.

    Args:
        platform: Platform name (weibo, xiaohongshu, douyin, bilibili, zhihu)
        limit: Maximum number of results

    Returns:
        JSON string with hot search results
    """
    tool = HotSearchTool()
    result = tool.execute(platform=platform, limit=limit)
    return json.dumps(result.to_dict(), ensure_ascii=False)


def competitor_analysis(account_url: str, platform: str = "xiaohongshu") -> str:
    """
    Analyze a competitor's account.

    Args:
        account_url: URL to the competitor's account page
        platform: Platform name

    Returns:
        JSON string with analysis results
    """
    tool = CompetitorAnalysisTool()
    result = tool.execute(account_url=account_url, platform=platform)
    return json.dumps(result.to_dict(), ensure_ascii=False)


def trend_analysis(keyword: str, time_range: str = "7d") -> str:
    """
    Analyze trends for a keyword.

    Args:
        keyword: Keyword to analyze
        time_range: Time range (24h, 7d, 30d, 90d)

    Returns:
        JSON string with trend analysis
    """
    tool = TrendAnalysisTool()
    result = tool.execute(keyword=keyword, time_range=time_range)
    return json.dumps(result.to_dict(), ensure_ascii=False)


# Export for CrewAI
hot_search_tool = hot_search
competitor_analysis_tool = competitor_analysis
trend_analysis_tool = trend_analysis
