"""Pydantic schemas for request/response validation."""

from src.schemas.analytics_report import (
    AnalyticsReport,
    AudienceDemographics,
    ComparisonAnalytics,
    EngagementRate,
    MetricType,
    MetricValue,
    PerformanceInsight,
    PlatformAnalytics,
    TimePeriod,
    TrendDirection,
)
from src.schemas.content_brief import (
    AudienceInsight,
    ContentBrief,
    ContentType,
    PlatformType,
    TargetAudience,
    TrendingTopic,
)
from src.schemas.content_draft import (
    ContentBlock,
    ContentDraft,
    DraftStatus,
    PlatformContent,
    QualityScore,
    ReviewFeedback,
)
from src.schemas.publish_result import (
    PlatformPostInfo,
    PublishError,
    PublishResult,
    PublishStatus,
    ScheduleType,
)
from src.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from src.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountStatusEnum,
    AccountUpdate,
    PlatformType as AccountPlatformType,
)

__all__ = [
    # Content Brief
    "ContentBrief",
    "AudienceInsight",
    "TrendingTopic",
    "TargetAudience",
    "ContentType",
    "PlatformType",
    # Content Draft
    "ContentDraft",
    "DraftStatus",
    "PlatformContent",
    "ContentBlock",
    "QualityScore",
    "ReviewFeedback",
    # Publish Result
    "PublishResult",
    "PublishStatus",
    "ScheduleType",
    "PlatformPostInfo",
    "PublishError",
    # Analytics Report
    "AnalyticsReport",
    "TimePeriod",
    "PlatformAnalytics",
    "MetricType",
    "MetricValue",
    "TrendDirection",
    "EngagementRate",
    "AudienceDemographics",
    "PerformanceInsight",
    "ComparisonAnalytics",
    # Client & Account
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "AccountStatusEnum",
    "AccountPlatformType",
]
