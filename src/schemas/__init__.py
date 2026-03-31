"""Pydantic schemas for request/response validation."""

from src.schemas.account import AccountCreate, AccountResponse, AccountStatusEnum, AccountUpdate
from src.schemas.account import PlatformType as AccountPlatformType
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
from src.schemas.client import ClientCreate, ClientResponse, ClientUpdate
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
from src.schemas.taste_profile import (
    AnalyticsInsights,
    CompetitorBenchmark,
    ExplicitPreferences,
    TasteProfile,
    TasteSignal,
    TasteVector,
)
from src.schemas.publish_result import (
    PlatformPostInfo,
    PublishError,
    PublishResult,
    PublishStatus,
    ScheduleType,
)

__all__ = [
    "AccountCreate",
    "AccountPlatformType",
    "AccountResponse",
    "AccountStatusEnum",
    "AccountUpdate",
    # Analytics Report
    "AnalyticsReport",
    "AudienceDemographics",
    "AudienceInsight",
    # Client & Account
    "ClientCreate",
    "ClientResponse",
    "ClientUpdate",
    "ComparisonAnalytics",
    "ContentBlock",
    # Content Brief
    "ContentBrief",
    # Content Draft
    "ContentDraft",
    "ContentType",
    "DraftStatus",
    "EngagementRate",
    "MetricType",
    "MetricValue",
    "PerformanceInsight",
    "PlatformAnalytics",
    "PlatformContent",
    "PlatformPostInfo",
    "PlatformType",
    "PublishError",
    # Publish Result
    "PublishResult",
    "PublishStatus",
    "QualityScore",
    "ReviewFeedback",
    "ScheduleType",
    "TargetAudience",
    "TimePeriod",
    "TrendDirection",
    "TrendingTopic",
    # Taste Profile
    "AnalyticsInsights",
    "CompetitorBenchmark",
    "ExplicitPreferences",
    "TasteProfile",
    "TasteSignal",
    "TasteVector",
]
