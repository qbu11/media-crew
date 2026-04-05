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


class ReviewContentTool(BaseTool):
    """
    Agent self-reviews a content draft and returns structured feedback.

    The agent acts as a quality reviewer, scoring the content against:
    - Relevance to topic
    - Tone consistency with taste profile
    - Structural quality (hook, body, CTA)
    - Platform fit
    - Engagement potential
    """

    name = "review_content"
    description = (
        "Review a content draft and return structured quality feedback. "
        "Provide scores (0-10) for relevance, tone, structure, platform_fit, "
        "engagement, plus a recommendation (accept/revise/reject) and specific "
        "feedback notes. Use this when you want to evaluate a draft before publishing."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The content title"},
            "body": {"type": "string", "description": "The content body text"},
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of hashtags",
            },
        },
        "required": ["title", "body"],
    }

    async def execute(
        self, title: str, body: str, hashtags: list[str] | None = None
    ) -> ToolResult:
        hashtags = hashtags or []
        # Scoring logic delegated to the agent; here we just structure the tool response
        return ToolResult(
            success=True,
            data={
                "scores": {},
                "overall": 0.0,
                "recommendation": "review_required",
                "notes": [],
            },
            metadata={"tool": self.name},
        )


class AdaptPlatformTool(BaseTool):
    """
    Adapt a content draft for a specific platform (xiaohongshu or wechat).

    Handles platform-specific formatting, length constraints, and style adjustments.
    """

    name = "adapt_platform"
    description = (
        "Adapt a content draft for a specific platform (xiaohongshu or wechat). "
        "Converts the draft to platform-specific format with appropriate length, "
        "formatting, and style adjustments. Returns the adapted content."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Original title"},
            "body": {"type": "string", "description": "Original body text"},
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Original hashtags",
            },
            "platform": {
                "type": "string",
                "enum": ["xiaohongshu", "wechat"],
                "description": "Target platform",
            },
        },
        "required": ["title", "body", "platform"],
    }

    async def execute(
        self,
        title: str,
        body: str,
        platform: str,
        hashtags: list[str] | None = None,
    ) -> ToolResult:
        hashtags = hashtags or []

        if platform == "xiaohongshu":
            adapted = self._adapt_xhs(title, body, hashtags)
        else:
            adapted = self._adapt_wechat(title, body, hashtags)

        return ToolResult(
            success=True,
            data={"platform": platform, "adapted": adapted},
            metadata={"tool": self.name},
        )

    def _adapt_xhs(self, title: str, body: str, hashtags: list[str]) -> dict[str, Any]:
        title = title[:20] if len(title) > 20 else title
        body = body[:1000] if len(body) > 1000 else body
        tags = [h.strip("#") for h in hashtags[:8]]
        return {
            "title": title,
            "body": body,
            "hashtags": tags,
        }

    def _adapt_wechat(self, title: str, body: str, hashtags: list[str]) -> dict[str, Any]:
        digest = body[:120] + "..." if len(body) > 120 else body
        tags = [h.strip("#") for h in hashtags]
        return {
            "title": title[:64] if len(title) > 64 else title,
            "body": body,
            "digest": digest,
            "hashtags": tags,
        }
