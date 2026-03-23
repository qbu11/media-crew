"""账号管理模型"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.client import Client


class AccountStatus(str):
    """账号状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Account(Base, TimestampMixin):
    """账号表"""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"account-{uuid4().hex[:12]}",
    )
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.ACTIVE)
    is_logged_in: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 关系
    client: Mapped["Client"] = relationship("Client", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, platform={self.platform}, username={self.username})>"
