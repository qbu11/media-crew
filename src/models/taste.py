"""Taste profile database models - 用户口味档案持久化."""

from uuid import uuid4

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TasteProfileDB(Base, TimestampMixin):
    """用户口味档案表."""

    __tablename__ = "taste_profiles"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"taste-{uuid4().hex[:12]}"
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    phase: Mapped[str] = mapped_column(String(20), default="manual")

    # Factor B: 显式偏好 (JSON)
    explicit_preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Factor C: 数据洞察 (JSON)
    analytics_insights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # 聚合口味向量 (JSON)
    taste_vectors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Factor A: 反馈信号 (JSON, 最近 500 条)
    feedback_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # 进化追踪
    total_feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    approval_count: Mapped[int] = mapped_column(Integer, default=0)
    rejection_count: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return (
            f"<TasteProfileDB(user_id={self.user_id!r}, "
            f"phase={self.phase!r}, v{self.version})>"
        )


class TasteFeedbackLog(Base, TimestampMixin):
    """口味反馈日志表 - 每次反馈的原始记录."""

    __tablename__ = "taste_feedback_logs"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: f"tfb-{uuid4().hex[:12]}"
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    draft_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # 反馈动作: approve, reject, edit, comment, score_override
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # 反馈详情 (JSON)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # 从此反馈提取的 taste signals (JSON)
    taste_signals_extracted: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # 可选的文本备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<TasteFeedbackLog(user={self.user_id!r}, "
            f"action={self.action!r}, draft={self.draft_id!r})>"
        )
