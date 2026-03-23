"""数据指标模型"""
from uuid import uuid4

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Metrics(Base, TimestampMixin):
    """数据指标表"""

    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"metric-{uuid4().hex[:12]}",
    )
    content_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="SET NULL"),
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    post_url: Mapped[str | None] = mapped_column(String(500))
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    raw_metrics: Mapped[dict | None] = mapped_column(JSON)

    @property
    def total_engagement(self) -> int:
        """总互动数"""
        return (self.likes or 0) + (self.comments or 0) + (self.shares or 0)

    def __repr__(self) -> str:
        return f"<Metrics(id={self.id}, platform={self.platform}, views={self.views})>"
