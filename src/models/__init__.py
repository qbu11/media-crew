"""Database models."""

from src.models.analytics import Analytics, AudienceInsightDB, MetricSnapshot, TimePeriod, TrendDirection
from src.models.base import Base, TimestampMixin
from src.models.content import Content, ContentBrief, ContentDraft, ContentType, DraftStatus
from src.models.publish_log import PlatformPost, PublishLog, PublishStatus, ScheduleType
from src.models.client import Client
from src.models.account import Account, AccountStatus
from src.models.hot_topic import HotTopic
from src.models.metrics import Metrics
from src.models.task import Task, TaskStatus

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Content
    "Content",
    "ContentBrief",
    "ContentDraft",
    "ContentType",
    "DraftStatus",
    # Publish Log
    "PublishLog",
    "PlatformPost",
    "PublishStatus",
    "ScheduleType",
    # Analytics
    "Analytics",
    "MetricSnapshot",
    "AudienceInsightDB",
    "TimePeriod",
    "TrendDirection",
    # Client & Account
    "Client",
    "Account",
    "AccountStatus",
    # Hotspot
    "HotTopic",
    "Metrics",
    # Task Queue
    "Task",
    "TaskStatus",
]
