"""Analytics database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.content import Content, ContentDraft


class TimePeriod(str):
    """Standard time periods for analysis."""

    HOUR_1 = "1h"
    HOUR_6 = "6h"
    HOUR_24 = "24h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    DAY_7 = "7d"
    DAY_30 = "30d"
    CUSTOM = "custom"


class TrendDirection(str):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class Analytics(Base, TimestampMixin):
    """Analytics report for content performance."""

    __tablename__ = "analytics"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"analytics-{uuid4().hex[:12]}"
    )

    # Foreign keys
    content_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("contents.id", ondelete="CASCADE"), nullable=True
    )
    draft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=True
    )
    publish_log_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("publish_logs.id", ondelete="SET NULL"), nullable=True
    )

    # Period
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Platform data
    platform_analytics: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Aggregated metrics
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_likes: Mapped[int] = mapped_column(Integer, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    total_shares: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Insights
    insights: Mapped[dict] = mapped_column(JSON, nullable=False)
    top_insights: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Comparison
    comparison: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Recommendations
    next_steps: Mapped[dict] = mapped_column(JSON, nullable=False)
    follow_up_topics: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Metadata
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="performance")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

    # Relationships
    content: Mapped["Content"] = relationship("Content", back_populates="analytics")
    draft: Mapped["ContentDraft"] = relationship("ContentDraft", back_populates="analytics")

    @property
    def total_engagement(self) -> int:
        """Calculate total engagement."""
        return self.total_likes + self.total_comments + self.total_shares


class MetricSnapshot(Base, TimestampMixin):
    """Time-series metric snapshots for trend analysis."""

    __tablename__ = "metric_snapshots"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"snap-{uuid4().hex[:12]}"
    )

    # Foreign key
    analytics_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("analytics.id", ondelete="CASCADE"), nullable=False
    )

    # Platform
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    post_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Metrics
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class AudienceInsightDB(Base, TimestampMixin):
    """Audience insights data."""

    __tablename__ = "audience_insights"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"aud-{uuid4().hex[:12]}"
    )

    # Foreign key
    analytics_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("analytics.id", ondelete="CASCADE"), nullable=False
    )

    # Platform
    platform: Mapped[str] = mapped_column(String(20), nullable=False)

    # Demographics
    age_groups: Mapped[dict] = mapped_column(JSON, nullable=False)
    genders: Mapped[dict] = mapped_column(JSON, nullable=False)
    locations: Mapped[dict] = mapped_column(JSON, nullable=False)
    interests: Mapped[dict] = mapped_column(JSON, nullable=False)
