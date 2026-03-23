"""Publish result schema for content publication tracking."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.schemas.content_brief import PlatformType


class PublishStatus(str, Enum):
    """Publication status workflow."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ScheduleType(str, Enum):
    """Schedule types."""

    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"


class PlatformPostInfo(BaseModel):
    """Platform-specific post information."""

    platform: PlatformType = Field(..., description="Target platform")
    post_id: str = Field(..., description="Platform post ID")
    post_url: str = Field(..., description="Public URL to the post")

    # Engagement snapshots (initial)
    initial_views: int = Field(default=0, ge=0, description="Initial view count")
    initial_likes: int = Field(default=0, ge=0, description="Initial like count")
    initial_comments: int = Field(default=0, ge=0, description="Initial comment count")
    initial_shares: int = Field(default=0, ge=0, description="Initial share count")

    # Timestamps
    published_at: datetime = Field(..., description="Publication timestamp")
    fetched_at: datetime = Field(default_factory=datetime.now, description="Data fetch timestamp")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional platform data")


class PublishError(BaseModel):
    """Error information for failed publication."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    platform: PlatformType | None = Field(default=None, description="Platform where error occurred")
    retry_able: bool = Field(default=False, description="Whether error is retry-able")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class PublishResult(BaseModel):
    """Result of content publication operation."""

    # Metadata
    id: str = Field(..., description="Unique publish result identifier")
    draft_id: str = Field(..., description="Reference to content draft")
    created_at: datetime = Field(default_factory=datetime.now)

    # Status
    status: PublishStatus = Field(default=PublishStatus.PENDING, description="Publication status")
    schedule_type: ScheduleType = Field(
        default=ScheduleType.IMMEDIATE, description="Schedule type"
    )

    # Scheduling
    scheduled_at: datetime | None = Field(default=None, description="Scheduled publish time")
    started_at: datetime | None = Field(default=None, description="Actual publish start time")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp")

    # Results
    platforms: list[PlatformType] = Field(..., description="Target platforms")
    successful_posts: list[PlatformPostInfo] = Field(
        default_factory=list, description="Successfully published posts"
    )
    failed_platforms: list[PlatformType] = Field(
        default_factory=list, description="Platforms that failed"
    )

    # Error handling
    errors: list[PublishError] = Field(default_factory=list, description="Errors encountered")
    retry_attempts: int = Field(default=0, ge=0, description="Total retry attempts")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")

    # Summary
    success_count: int = Field(default=0, ge=0, description="Number of successful publishes")
    failure_count: int = Field(default=0, ge=0, description="Number of failed publishes")
    total_count: int = Field(..., description="Total number of platforms")

    # Metadata
    published_by: str = Field(default="system", description="Who initiated the publish")
    notes: str = Field(default="", description="Additional notes")

    def __post_init__(self) -> None:
        """Calculate summary fields."""
        self.total_count = len(self.platforms)
        self.success_count = len(self.successful_posts)
        self.failure_count = len(self.failed_platforms)

    def is_complete(self) -> bool:
        """Check if publish operation is complete."""
        return self.status in (
            PublishStatus.PUBLISHED,
            PublishStatus.FAILED,
            PublishStatus.CANCELLED,
        )

    def get_success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def get_post_url(self, platform: PlatformType) -> str | None:
        """Get post URL for specific platform."""
        for post in self.successful_posts:
            if post.platform == platform:
                return post.post_url
        return None

    def has_retryable_errors(self) -> bool:
        """Check if there are retryable errors."""
        return any(error.retry_able for error in self.errors)

    model_config = {"json_schema_extra": {"example": {}}}


# Example for documentation
PublishResult.model_config["json_schema_extra"]["example"] = {
    "id": "publish-20250320-001",
    "draft_id": "draft-20250320-001",
    "status": "published",
    "schedule_type": "immediate",
    "scheduled_at": None,
    "started_at": "2025-03-20T10:00:00",
    "completed_at": "2025-03-20T10:02:30",
    "platforms": ["xiaohongshu", "wechat"],
    "successful_posts": [
        {
            "platform": "xiaohongshu",
            "post_id": "64a1b2c3d4e5f6g7h8i9j0",
            "post_url": "https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
            "published_at": "2025-03-20T10:00:30",
        },
        {
            "platform": "wechat",
            "post_id": "mpwx1234567890",
            "post_url": "https://mp.weixin.qq.com/s/abc123def456",
            "published_at": "2025-03-20T10:01:45",
        },
    ],
    "failed_platforms": [],
    "errors": [],
    "success_count": 2,
    "failure_count": 0,
    "total_count": 2,
}
