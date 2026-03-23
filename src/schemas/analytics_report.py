"""Analytics report schema for content performance analysis."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.content_brief import PlatformType


class MetricType(str, Enum):
    """Types of metrics."""

    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    SAVES = "saves"
    CLICKS = "clicks"
    CONVERSIONS = "conversions"
    IMPRESSIONS = "impressions"
    REACH = "reach"


class TimePeriod(str, Enum):
    """Standard time periods for analysis."""

    HOUR_1 = "1h"
    HOUR_6 = "6h"
    HOUR_24 = "24h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    DAY_7 = "7d"
    DAY_30 = "30d"
    CUSTOM = "custom"


class TrendDirection(str, Enum):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class MetricValue(BaseModel):
    """A single metric value with metadata."""

    type: MetricType = Field(..., description="Metric type")
    value: int = Field(..., ge=0, description="Metric value")
    previous_value: int | None = Field(default=None, description="Previous period value")
    change_percent: float | None = Field(default=None, description="Percentage change")
    trend: TrendDirection = Field(default=TrendDirection.STABLE, description="Trend direction")

    @model_validator(mode="after")
    def calculate_change(self) -> "MetricValue":
        """Calculate percentage change if not provided."""
        if self.change_percent is not None:
            return self
        if self.previous_value is not None and self.previous_value > 0:
            self.change_percent = round(
                ((self.value - self.previous_value) / self.previous_value) * 100, 2
            )
        return self


class EngagementRate(BaseModel):
    """Engagement rate metrics."""

    overall: float = Field(..., ge=0.0, description="Overall engagement rate")
    like_rate: float = Field(..., ge=0.0, description="Like rate (likes/views)")
    comment_rate: float = Field(..., ge=0.0, description="Comment rate (comments/views)")
    share_rate: float = Field(..., ge=0.0, description="Share rate (shares/views)")
    save_rate: float = Field(..., ge=0.0, description="Save rate (saves/views)")


class AudienceDemographics(BaseModel):
    """Audience demographic breakdown."""

    age_groups: dict[str, int] = Field(
        default_factory=dict, description="Distribution by age group"
    )
    genders: dict[str, int] = Field(default_factory=dict, description="Distribution by gender")
    locations: dict[str, int] = Field(
        default_factory=dict, description="Top locations by engagement"
    )
    interests: list[str] = Field(default_factory=list, description="Top interests")


class PerformanceInsight(BaseModel):
    """AI-generated insight about performance."""

    category: Literal["strength", "weakness", "opportunity", "trend"] = Field(
        ..., description="Insight category"
    )
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed description")
    actionable: bool = Field(default=True, description="Whether insight is actionable")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")
    recommendations: list[str] = Field(
        default_factory=list, description="Action recommendations"
    )


class PlatformAnalytics(BaseModel):
    """Platform-specific analytics."""

    platform: PlatformType = Field(..., description="Platform")
    post_id: str = Field(..., description="Platform post ID")
    post_url: str = Field(..., description="Post URL")

    # Core metrics
    metrics: dict[MetricType, MetricValue] = Field(
        default_factory=dict, description="Collected metrics"
    )

    # Engagement
    engagement_rate: EngagementRate | None = Field(
        default=None, description="Engagement rate metrics"
    )

    # Audience
    demographics: AudienceDemographics | None = Field(
        default=None, description="Audience demographics"
    )

    # Performance score
    performance_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Overall score")
    percentile_rank: float | None = Field(
        default=None, ge=0.0, le=100.0, description="Rank among similar content"
    )

    # Timestamps
    period_start: datetime = Field(..., description="Analysis period start")
    period_end: datetime = Field(..., description="Analysis period end")
    fetched_at: datetime = Field(default_factory=datetime.now, description="Data fetch time")

    def get_metric(self, metric_type: MetricType) -> MetricValue | None:
        """Get specific metric value."""
        return self.metrics.get(metric_type)

    def calculate_total_engagement(self) -> int:
        """Calculate total engagement (likes + comments + shares)."""
        total = 0
        for metric_type in (MetricType.LIKES, MetricType.COMMENTS, MetricType.SHARES):
            metric = self.metrics.get(metric_type)
            if metric:
                total += metric.value
        return total


class ComparisonAnalytics(BaseModel):
    """Comparison between multiple platforms or content."""

    comparison_type: Literal["platform", "content", "period"] = Field(
        ..., description="Type of comparison"
    )
    best_performing: PlatformType | str = Field(..., description="Best performing platform/content")
    worst_performing: PlatformType | str = Field(
        ..., description="Worst performing platform/content"
    )
    differences: dict[str, float] = Field(
        default_factory=dict, description="Key differences"
    )
    recommendation: str = Field(default="", description="Strategic recommendation")


class AnalyticsReport(BaseModel):
    """Comprehensive analytics report for content performance."""

    # Metadata
    id: str = Field(..., description="Unique report identifier")
    content_id: str = Field(..., description="Reference to published content")
    publish_result_id: str = Field(..., description="Reference to publish result")
    draft_id: str = Field(..., description="Reference to content draft")
    created_at: datetime = Field(default_factory=datetime.now)

    # Period
    period: TimePeriod = Field(..., description="Analysis period")
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")

    # Platform data
    platform_analytics: list[PlatformAnalytics] = Field(
        default_factory=list, description="Per-platform analytics"
    )

    # Aggregated metrics
    total_views: int = Field(default=0, ge=0, description="Total views across platforms")
    total_likes: int = Field(default=0, ge=0, description="Total likes across platforms")
    total_comments: int = Field(default=0, ge=0, description="Total comments across platforms")
    total_shares: int = Field(default=0, ge=0, description="Total shares across platforms")
    avg_engagement_rate: float = Field(default=0.0, ge=0.0, description="Average engagement rate")

    # Insights
    insights: list[PerformanceInsight] = Field(
        default_factory=list, description="AI-generated insights"
    )
    top_insights: list[PerformanceInsight] = Field(
        default_factory=list, description="Top 3 insights by confidence"
    )

    # Comparison
    comparison: ComparisonAnalytics | None = Field(
        default=None, description="Comparison analytics"
    )

    # Recommendations
    next_steps: list[str] = Field(
        default_factory=list, description="Recommended next actions"
    )
    follow_up_topics: list[str] = Field(
        default_factory=list, description="Suggested follow-up content topics"
    )

    # Metadata
    report_type: Literal["performance", "trend", "comparison"] = Field(
        default="performance", description="Report type"
    )
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Data confidence")

    def get_best_platform(self) -> PlatformType | None:
        """Get best performing platform."""
        if not self.platform_analytics:
            return None
        return max(self.platform_analytics, key=lambda x: x.performance_score).platform

    def get_total_engagement(self) -> int:
        """Calculate total engagement across all platforms."""
        return self.total_likes + self.total_comments + self.total_shares

    def get_top_insight(self) -> PerformanceInsight | None:
        """Get top insight."""
        return self.top_insights[0] if self.top_insights else None

    model_config = {"json_schema_extra": {"example": {}}}


# Example for documentation
AnalyticsReport.model_config["json_schema_extra"]["example"] = {
    "id": "analytics-20250320-001",
    "content_id": "publish-20250320-001",
    "publish_result_id": "publish-20250320-001",
    "draft_id": "draft-20250320-001",
    "period": "7d",
    "period_start": "2025-03-13T00:00:00",
    "period_end": "2025-03-20T00:00:00",
    "platform_analytics": [
        {
            "platform": "xiaohongshu",
            "post_id": "64a1b2c3d4e5f6g7h8i9j0",
            "post_url": "https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
            "metrics": {
                "views": {"type": "views", "value": 15234, "previous_value": 8567},
                "likes": {"type": "likes", "value": 1245, "previous_value": 678},
                "comments": {"type": "comments", "value": 89, "previous_value": 45},
                "shares": {"type": "shares", "value": 34, "previous_value": 12},
            },
            "performance_score": 8.2,
            "percentile_rank": 85.0,
        },
        {
            "platform": "wechat",
            "post_id": "mpwx1234567890",
            "post_url": "https://mp.weixin.qq.com/s/abc123def456",
            "metrics": {
                "views": {"type": "views", "value": 8456, "previous_value": 0},
                "likes": {"type": "likes", "value": 567, "previous_value": 0},
                "comments": {"type": "comments", "value": 23, "previous_value": 0},
                "shares": {"type": "shares", "value": 45, "previous_value": 0},
            },
            "performance_score": 7.5,
            "percentile_rank": 72.0,
        },
    ],
    "total_views": 23690,
    "total_likes": 1812,
    "total_comments": 112,
    "total_shares": 79,
    "avg_engagement_rate": 8.7,
    "insights": [
        {
            "category": "strength",
            "title": "小红书表现突出",
            "description": "小红书平台互动率高于平均水平35%",
            "actionable": True,
            "confidence": 0.9,
        },
        {
            "category": "opportunity",
            "title": "知乎话题机会",
            "description": "相关话题在知乎热度上升",
            "actionable": True,
            "confidence": 0.75,
        },
    ],
    "top_insights": [
        {
            "category": "strength",
            "title": "小红书表现突出",
            "description": "小红书平台互动率高于平均水平35%",
            "actionable": True,
            "confidence": 0.9,
        }
    ],
    "comparison": {
        "comparison_type": "platform",
        "best_performing": "xiaohongshu",
        "worst_performing": "wechat",
        "differences": {"view_rate": 1.8, "engagement_rate": 1.35},
        "recommendation": "优先在小红书投放，增加内容密度",
    },
    "next_steps": [
        "在3天内发布小红书系列内容第二篇",
        "优化微信公众号封面图",
        "准备知乎问答版本",
    ],
    "follow_up_topics": ["AI融资技巧", "AI团队管理", "AI产品验证"],
}
