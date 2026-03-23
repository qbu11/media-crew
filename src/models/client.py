"""客户管理模型"""
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.account import Account


class Client(Base, TimestampMixin):
    """客户表"""

    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"client-{uuid4().hex[:12]}",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    industry: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    # 关系
    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name={self.name})>"
