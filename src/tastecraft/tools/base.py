"""Base tool class for Anthropic SDK tool_use integration."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result from tool execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_content_str(self) -> str:
        """Serialize for Anthropic tool_result content."""
        if self.success:
            return json.dumps(
                {"success": True, "data": self.data, **self.metadata},
                ensure_ascii=False,
                default=str,
            )
        return json.dumps(
            {"success": False, "error": self.error},
            ensure_ascii=False,
        )


class BaseTool(ABC):
    """
    Abstract base for all TasteCraft agent tools.

    Each tool exposes:
    - name / description: for the Anthropic tool schema
    - input_schema: JSON Schema dict describing parameters
    - execute(**kwargs): the actual implementation
    - to_anthropic_schema(): export for client.messages.create(tools=[...])
    """

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Export as Anthropic API tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool. Subclasses must implement."""
        ...

    async def safe_execute(self, **kwargs: Any) -> ToolResult:
        """Execute with error handling."""
        try:
            return await self.execute(**kwargs)
        except Exception as e:
            logger.exception("Tool %s failed", self.name)
            return ToolResult(success=False, error=f"{type(e).__name__}: {e}")


class ToolRegistry:
    """Registry of available tools for an agent loop."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all_schemas(self) -> list[dict[str, Any]]:
        """Export all tool schemas for Anthropic API."""
        return [t.to_anthropic_schema() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
