"""
Analytics Tools for Media Publishing

Provides tools for:
- Data collection from published content
- Analytics report generation
- Performance tracking
"""

from datetime import datetime
from enum import Enum
import json
from typing import Any

from .base_tool import BaseTool, ToolResult, ToolStatus


class MetricType(Enum):
    """Types of metrics to collect"""
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    FAVORITES = "favorites"
    ENGAGEMENT_RATE = "engagement_rate"
    CLICK_THROUGH_RATE = "click_through_rate"


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"


class DataCollectTool(BaseTool):
    """
    Tool for collecting data from published content.

    Fetches metrics from platform APIs or via web scraping.
    """

    name = "data_collect"
    description = "Collects analytics data from published content across platforms"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 10
    min_interval_seconds = 5.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._tikhub_token = self.config.get("tikhub_token")

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        if "content_id" not in kwargs and "content_ids" not in kwargs:
            return False, "Either content_id or content_ids is required"

        platform = kwargs.get("platform", "xiaohongshu")
        valid_platforms = ["xiaohongshu", "weibo", "douyin", "bilibili", "zhihu", "wechat"]
        if platform not in valid_platforms:
            return False, f"Unsupported platform: {platform}"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Collect analytics data for content.

        Args:
            content_id: Single content ID to collect data for
            content_ids: Multiple content IDs to collect data for
            platform: Platform name
            metrics: List of metrics to collect (default: all)

        Returns:
            ToolResult with analytics data
        """
        platform = kwargs.get("platform", "xiaohongshu")
        content_id = kwargs.get("content_id")
        content_ids = kwargs.get("content_ids", [])
        metrics = kwargs.get("metrics", ["all"])

        if content_id:
            content_ids = [content_id]

        try:
            results = []

            for cid in content_ids:
                data = self._fetch_content_data(cid, platform, metrics)
                results.append(data)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "platform": platform,
                    "content_count": len(content_ids),
                    "results": results,
                    "collected_at": datetime.now().isoformat()
                },
                platform=platform
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Data collection failed: {e!s}",
                platform=platform
            )

    def _fetch_content_data(
        self,
        content_id: str,
        platform: str,
        metrics: list[str]
    ) -> dict[str, Any]:
        """Fetch data for a single content item"""
        # In actual implementation:
        # 1. Call platform API or use web scraping
        # 2. Extract requested metrics
        # 3. Normalize data format

        return {
            "content_id": content_id,
            "platform": platform,
            "metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "favorites": 0,
                "engagement_rate": 0.0
            },
            "collected_at": datetime.now().isoformat()
        }


class AnalyticsReportTool(BaseTool):
    """
    Tool for generating analytics reports.

    Aggregates collected data and generates formatted reports.
    """

    name = "analytics_report"
    description = "Generates analytics reports from collected data"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 10
    min_interval_seconds = 2.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        data = kwargs.get("data")
        if not data:
            return False, "Data is required (pass collected analytics data)"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Generate analytics report.

        Args:
            data: Collected analytics data
            format: Output format (json, markdown, csv)
            include_charts: Include chart data (default: true)
            time_range: Time range for analysis (optional)

        Returns:
            ToolResult with formatted report
        """
        data = kwargs.get("data", [])
        format_type = kwargs.get("format", "json")
        include_charts = kwargs.get("include_charts", True)

        try:
            # Generate summary statistics
            summary = self._generate_summary(data)

            # Generate insights
            insights = self._generate_insights(data)

            # Generate chart data
            chart_data = None
            if include_charts:
                chart_data = self._generate_chart_data(data)

            report = {
                "summary": summary,
                "insights": insights,
                "chart_data": chart_data,
                "generated_at": datetime.now().isoformat()
            }

            # Format output
            if format_type == "markdown":
                output = self._format_markdown(report)
            elif format_type == "csv":
                output = self._format_csv(data)
            else:
                output = json.dumps(report, ensure_ascii=False, indent=2)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "format": format_type,
                    "report": output,
                    "summary": summary,
                    "insights_count": len(insights)
                },
                platform="multi"
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Report generation failed: {e!s}",
                platform="multi"
            )

    def _generate_summary(self, data: list[dict]) -> dict[str, Any]:
        """Generate summary statistics"""
        if not data:
            return {}

        total_views = sum(item.get("metrics", {}).get("views", 0) for item in data)
        total_likes = sum(item.get("metrics", {}).get("likes", 0) for item in data)
        total_comments = sum(item.get("metrics", {}).get("comments", 0) for item in data)
        total_shares = sum(item.get("metrics", {}).get("shares", 0) for item in data)

        avg_engagement = 0.0
        if data:
            engagement_rates = [
                item.get("metrics", {}).get("engagement_rate", 0)
                for item in data
            ]
            avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

        # Top performing content
        sorted_by_views = sorted(
            data,
            key=lambda x: x.get("metrics", {}).get("views", 0),
            reverse=True
        )
        top_content = sorted_by_views[:5] if sorted_by_views else []

        return {
            "total_content": len(data),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_engagement_rate": f"{avg_engagement:.2%}",
            "top_content": [
                {
                    "content_id": item.get("content_id"),
                    "views": item.get("metrics", {}).get("views", 0),
                    "platform": item.get("platform")
                }
                for item in top_content
            ]
        }

    def _generate_insights(self, data: list[dict]) -> list[str]:
        """Generate actionable insights"""
        insights = []

        if not data:
            return insights

        # Analyze engagement
        high_engagement = [
            item for item in data
            if item.get("metrics", {}).get("engagement_rate", 0) > 0.05
        ]

        if high_engagement:
            insights.append(
                f"{len(high_engagement)} posts have high engagement (>5%). "
                "Consider creating similar content."
            )

        # Analyze platforms
        platform_counts = {}
        for item in data:
            platform = item.get("platform", "unknown")
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        best_platform = max(platform_counts, key=platform_counts.get, default=None)
        if best_platform:
            insights.append(
                f"Most content is on {best_platform} ({platform_counts[best_platform]} posts). "
                "Consider diversifying to other platforms."
            )

        return insights

    def _generate_chart_data(self, data: list[dict]) -> dict[str, Any]:
        """Generate data for charts"""
        # Time series data
        time_series = []
        for item in data:
            time_series.append({
                "date": item.get("collected_at", "")[:10],
                "views": item.get("metrics", {}).get("views", 0),
                "likes": item.get("metrics", {}).get("likes", 0)
            })

        # Platform distribution
        platform_dist = {}
        for item in data:
            platform = item.get("platform", "unknown")
            views = item.get("metrics", {}).get("views", 0)
            platform_dist[platform] = platform_dist.get(platform, 0) + views

        return {
            "time_series": time_series,
            "platform_distribution": [
                {"platform": k, "views": v}
                for k, v in platform_dist.items()
            ]
        }

    def _format_markdown(self, report: dict[str, Any]) -> str:
        """Format report as Markdown"""
        lines = ["# Analytics Report\n"]
        lines.append(f"Generated: {report['generated_at']}\n")

        summary = report.get("summary", {})
        if summary:
            lines.append("## Summary\n")
            lines.append(f"- Total Content: {summary.get('total_content', 0)}")
            lines.append(f"- Total Views: {summary.get('total_views', 0):,}")
            lines.append(f"- Total Likes: {summary.get('total_likes', 0):,}")
            lines.append(f"- Total Comments: {summary.get('total_comments', 0):,}")
            lines.append(f"- Avg Engagement: {summary.get('avg_engagement_rate', '0%')}")
            lines.append("")

        insights = report.get("insights", [])
        if insights:
            lines.append("## Insights\n")
            for insight in insights:
                lines.append(f"- {insight}")
            lines.append("")

        return "\n".join(lines)

    def _format_csv(self, data: list[dict]) -> str:
        """Format data as CSV"""
        if not data:
            return ""

        headers = ["content_id", "platform", "views", "likes", "comments", "shares", "engagement_rate"]
        rows = [",".join(headers)]

        for item in data:
            metrics = item.get("metrics", {})
            row = [
                item.get("content_id", ""),
                item.get("platform", ""),
                str(metrics.get("views", 0)),
                str(metrics.get("likes", 0)),
                str(metrics.get("comments", 0)),
                str(metrics.get("shares", 0)),
                str(metrics.get("engagement_rate", 0))
            ]
            rows.append(",".join(row))

        return "\n".join(rows)


# CrewAI tool wrappers

def data_collect(content_id: str, platform: str = "xiaohongshu") -> str:
    """
    Collect analytics data for content.

    Args:
        content_id: Content ID to collect data for
        platform: Platform name

    Returns:
        JSON string with analytics data
    """
    tool = DataCollectTool()
    result = tool.execute(content_id=content_id, platform=platform)
    return json.dumps(result.to_dict(), ensure_ascii=False)


def analytics_report(data: list, format_type: str = "json") -> str:
    """
    Generate analytics report.

    Args:
        data: Collected analytics data
        format_type: Output format (json, markdown, csv)

    Returns:
        JSON string with formatted report
    """
    tool = AnalyticsReportTool()
    result = tool.execute(data=data, format=format_type)
    return json.dumps(result.to_dict(), ensure_ascii=False)


# Export for CrewAI
data_collect_tool = data_collect
analytics_report_tool = analytics_report
