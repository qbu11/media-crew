"""Agent registry and status models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class AgentStatus(str):
    """Agent status enum."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


class AgentRegistry(Base, TimestampMixin):
    """Agent registry with status and statistics."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AgentStatus.IDLE, index=True)

    # Capabilities
    tools: Mapped[dict] = mapped_column("tools_json", default=list)  # type: ignore
    llm_model: Mapped[str | None] = mapped_column(String(100), default=None)

    # Statistics
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0)
    avg_execution_time: Mapped[float] = mapped_column(Float, default=0.0)

    # Last execution
    last_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def is_available(self) -> bool:
        """Check if agent is available for tasks."""
        return self.status not in (AgentStatus.DISABLED, AgentStatus.RUNNING)

    def mark_running(self) -> None:
        """Mark agent as running."""
        self.status = AgentStatus.RUNNING

    def mark_completed(self, success: bool, execution_time: float, error: str | None = None) -> None:
        """Mark agent execution as completed."""
        self.status = AgentStatus.IDLE
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            self.last_error = error

        # Update average execution time (exponential moving average)
        if self.avg_execution_time == 0:
            self.avg_execution_time = execution_time
        else:
            self.avg_execution_time = 0.9 * self.avg_execution_time + 0.1 * execution_time

        self.last_execution_at = datetime.now()

    def __repr__(self) -> str:
        return f"<AgentRegistry(name={self.name}, status={self.status})>"


class AgentExecution(Base):
    """Individual agent execution record for detailed tracking."""

    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=lambda: f"exec-{uuid4().hex[:12]}",
    )
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Task reference
    task_id: Mapped[str | None] = mapped_column(String(50), default=None, index=True)

    # Execution
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    input_data: Mapped[dict | None] = mapped_column(default=None)
    output_data: Mapped[dict | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Token usage (for cost tracking)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def duration(self) -> float | None:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if execution is in terminal state."""
        return self.status in ("completed", "failed", "cancelled")

    def __repr__(self) -> str:
        return f"<AgentExecution(id={self.id}, agent={self.agent_name}, status={self.status})>"
