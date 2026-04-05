"""Project and TasteProfile database models."""

from __future__ import annotations

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tastecraft.models.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    platforms: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Content(Base, TimestampMixin):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    pipeline_run_id: Mapped[str] = mapped_column(String(100), default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    mode: Mapped[str] = mapped_column(String(20), default="auto")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_feedback: Mapped[dict] = mapped_column(JSON, default=dict)


class ContentRevision(Base, TimestampMixin):
    __tablename__ = "content_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, index=True)
    body_before: Mapped[str] = mapped_column(Text, default="")
    body_after: Mapped[str] = mapped_column(Text, default="")
    diff: Mapped[str] = mapped_column(Text, default="")
    revision_source: Mapped[str] = mapped_column(String(50), default="")
    learned_signals: Mapped[dict] = mapped_column(JSON, default=dict)


class PublishLog(Base, TimestampMixin):
    __tablename__ = "publish_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, index=True)
    platform: Mapped[str] = mapped_column(String(50))
    platform_post_id: Mapped[str] = mapped_column(String(200), default="")
    platform_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    adapted_content: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")


class AnalyticsSnapshot(Base, TimestampMixin):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publish_log_id: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(20))
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    new_followers: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)


class EvolutionLog(Base, TimestampMixin):
    __tablename__ = "evolution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    trigger: Mapped[str] = mapped_column(String(20))
    signals_input: Mapped[dict] = mapped_column(JSON, default=dict)
    changes_made: Mapped[dict] = mapped_column(JSON, default=dict)
    taste_before: Mapped[dict] = mapped_column(JSON, default=dict)
    taste_after: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0)


class ScheduleRule(Base, TimestampMixin):
    __tablename__ = "schedule_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    pipeline: Mapped[str] = mapped_column(String(50))
    cron_expr: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(default=True)
