"""
Base Tool Class for CrewAI Media Publishing Tools

Provides the foundation for all platform-specific and utility tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    """Tool execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class ToolResult:
    """
    Standardized result object for tool execution.

    Attributes:
        status: Execution status
        data: Result data (for success)
        error: Error message (for failure)
        platform: Platform identifier
        content_id: Published content ID
        metadata: Additional metadata
    """
    status: ToolStatus
    data: dict[str, Any] | None = None
    error: str | None = None
    platform: str | None = None
    content_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "platform": self.platform,
            "content_id": self.content_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }

    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ToolStatus.SUCCESS

    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == ToolStatus.FAILED


class ToolError(Exception):
    """Base exception for tool errors"""

    def __init__(self, message: str, platform: str | None = None, details: dict | None = None):
        self.message = message
        self.platform = platform
        self.details = details or {}
        super().__init__(self.message)

    def to_result(self) -> ToolResult:
        """Convert error to ToolResult"""
        return ToolResult(
            status=ToolStatus.FAILED,
            error=self.message,
            platform=self.platform,
            metadata=self.details
        )


class BaseTool(ABC):
    """
    Abstract base class for all CrewAI tools.

    All platform-specific and utility tools should inherit from this class.
    """

    # Tool metadata
    name: str = ""
    description: str = ""
    platform: str = ""
    version: str = "0.1.0"

    # Rate limiting
    max_requests_per_minute: int = 10
    min_interval_seconds: float = 1.0

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the tool.

        Args:
            config: Tool-specific configuration
        """
        self.config = config or {}
        self._last_execution: datetime | None = None
        self._execution_count = 0
        self._execution_count_window: datetime | None = None

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's primary action.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """
        Validate input parameters.

        Args:
            **kwargs: Input parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None

    def check_rate_limit(self) -> tuple[bool, str | None]:
        """
        Check if tool execution is within rate limits.

        Returns:
            Tuple of (allowed, error_message)
        """
        now = datetime.now()

        # Reset counter if window expired
        if (self._execution_count_window is None or
            (now - self._execution_count_window).seconds >= 60):
            self._execution_count = 0
            self._execution_count_window = now

        # Check rate limit
        if self._execution_count >= self.max_requests_per_minute:
            return False, f"Rate limit exceeded: {self.max_requests_per_minute} requests per minute"

        # Check minimum interval
        if self._last_execution is not None:
            elapsed = (now - self._last_execution).total_seconds()
            if elapsed < self.min_interval_seconds:
                return False, f"Minimum interval not met: {self.min_interval_seconds}s required, {elapsed:.1f}s elapsed"

        return True, None

    def pre_execute(self, **kwargs) -> ToolResult:
        """
        Pre-execution hook. Override in subclass for custom behavior.

        Returns:
            ToolResult with status=PENDING if execution should proceed
        """
        # Validate input
        is_valid, error_msg = self.validate_input(**kwargs)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Invalid input: {error_msg}",
                platform=self.platform
            )

        # Check rate limit
        allowed, error_msg = self.check_rate_limit()
        if not allowed:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Rate limit: {error_msg}",
                platform=self.platform
            )

        return ToolResult(status=ToolStatus.PENDING, platform=self.platform)

    def post_execute(self, result: ToolResult) -> ToolResult:
        """
        Post-execution hook. Override in subclass for custom behavior.

        Args:
            result: The execution result

        Returns:
            Possibly modified result
        """
        # Update execution tracking
        self._last_execution = datetime.now()
        self._execution_count += 1

        return result

    def run(self, **kwargs) -> ToolResult:
        """
        Run the tool with pre/post execution hooks.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with execution outcome
        """
        # Pre-execution checks
        pre_result = self.pre_execute(**kwargs)
        if pre_result.status != ToolStatus.PENDING:
            return pre_result

        try:
            # Execute the tool
            result = self.execute(**kwargs)
            return self.post_execute(result)

        except ToolError as e:
            return self.post_execute(e.to_result())

        except Exception as e:
            return self.post_execute(
                ToolResult(
                    status=ToolStatus.FAILED,
                    error=f"Unexpected error: {e!s}",
                    platform=self.platform
                )
            )

    def get_metadata(self) -> dict[str, Any]:
        """Get tool metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "platform": self.platform,
            "version": self.version,
            "rate_limit": {
                "max_requests_per_minute": self.max_requests_per_minute,
                "min_interval_seconds": self.min_interval_seconds
            },
            "execution_count": self._execution_count,
            "last_execution": self._last_execution.isoformat() if self._last_execution else None
        }


class ConfigurableTool(BaseTool):
    """
    Base class for tools that require configuration.

    Supports loading configuration from environment variables
    and config files.
    """

    # Required configuration keys
    required_config_keys: list[str] = []

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate configuration"""
        missing_keys = []
        for key in self.required_config_keys:
            if key not in self.config:
                # Try environment variable
                import os
                env_key = f"{self.platform.upper()}_{key.upper()}"
                value = os.environ.get(env_key)
                if value:
                    self.config[key] = value
                else:
                    missing_keys.append(key)

        if missing_keys:
            raise ToolError(
                f"Missing required configuration: {', '.join(missing_keys)}",
                platform=self.platform,
                details={"missing_keys": missing_keys}
            )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback"""
        return self.config.get(key, default)
