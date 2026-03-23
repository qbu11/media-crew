"""热点话题模型"""
from uuid import uuid4

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class HotTopic(Base, TimestampMixin):
    """热点话题表"""

    __tablename__ = "hot_topics"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"topic-{uuid4().hex[:12]}",
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    rank: Mapped[int | None] = mapped_column(Integer)
    heat_score: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict | None] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<HotTopic(id={self.id}, platform={self.platform}, title={self.title[:30]})>"
