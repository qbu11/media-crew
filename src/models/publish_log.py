"""Publish log database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.content import Content, ContentDraft


class PublishStatus(str):
    """Publication status workflow."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ScheduleType(str):
    """Schedule types."""

    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"


class PublishLog(Base, TimestampMixin):
    """Publication log tracking content publish operations."""

    __tablename__ = "publish_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"publish-{uuid4().hex[:12]}"
    )

    # Foreign keys
    draft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("content_drafts.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PublishStatus.PENDING, index=True
    )
    schedule_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ScheduleType.IMMEDIATE
    )

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Results
    platforms: Mapped[dict] = mapped_column(JSON, nullable=False)  # List[str]
    successful_posts: Mapped[dict] = mapped_column(JSON, nullable=False)  # List[PlatformPostInfo]
    failed_platforms: Mapped[dict] = mapped_column(JSON, nullable=False)  # List[str]

    # Error handling
    errors: Mapped[dict] = mapped_column(JSON, nullable=False)  # List[PublishError]
    retry_attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Summary
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    published_by: Mapped[str] = mapped_column(String(50), default="system")
    notes: Mapped[str] = mapped_column(String(500), default="")

    # Relationships
    draft: Mapped["ContentDraft"] = relationship("ContentDraft", back_populates="publish_logs")
    content: Mapped["Content"] = relationship("Content", back_populates="publish_logs")

    @property
    def is_complete(self) -> bool:
        """Check if publish operation is complete."""
        return self.status in (
            PublishStatus.PUBLISHED,
            PublishStatus.FAILED,
            PublishStatus.CANCELLED,
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class PlatformPost(Base, TimestampMixin):
    """Platform-specific post information."""

    __tablename__ = "platform_posts"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"post-{uuid4().hex[:12]}"
    )

    # Foreign key
    publish_log_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("publish_logs.id", ondelete="CASCADE"), nullable=False
    )

    # Platform info
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    post_id: Mapped[str] = mapped_column(String(100), nullable=False)
    post_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Initial engagement
    initial_views: Mapped[int] = mapped_column(Integer, default=0)
    initial_likes: Mapped[int] = mapped_column(Integer, default=0)
    initial_comments: Mapped[int] = mapped_column(Integer, default=0)
    initial_shares: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Post Metadata (renamed to avoid SQLAlchemy reserved word)
    post_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
