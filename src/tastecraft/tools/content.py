"""Content generation and management tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SaveDraftTool(BaseTool):
    """Save a content draft to the database."""

    name = "save_draft"
    description = (
        "Save a generated content draft. Provide title, body, hashtags, "
        "and an optional quality_score (0-10). Returns the saved content ID."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Content title",
            },
            "body": {
                "type": "string",
                "description": "Content body text",
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of hashtags",
            },
            "quality_score": {
                "type": "number",
                "description": "Self-assessed quality score 0-10",
            },
        },
        "required": ["title", "body"],
    }

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id

    async def execute(
        self,
        title: str = "",
        body: str = "",
        hashtags: list[str] | None = None,
        quality_score: float = 0.0,
        **kwargs: Any,
    ) -> ToolResult:
        from tastecraft.models.base import get_session
        from tastecraft.models.tables import Content

        session = await get_session()
        async with session:
            content = Content(
                project_id=self._project_id,
                title=title,
                body=body,
                metadata_json={"hashtags": hashtags or []},
                status="draft",
                quality_score=quality_score,
            )
            session.add(content)
            await session.commit()
            await session.refresh(content)

            logger.info("Draft saved: id=%d title=%s", content.id, title[:50])
            return ToolResult(
                success=True,
                data={
                    "content_id": content.id,
                    "title": title,
                    "status": "draft",
                    "quality_score": quality_score,
                },
            )
