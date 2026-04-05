"""Xiaohongshu platform tool — wrappers existing xiaohongshu.py logic."""

from __future__ import annotations

import asyncio
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

# Reuse existing publishing logic from the CrewAI-era codebase
try:
    from crew.tools.platform.xiaohongshu import XiaohongshuTool
    from crew.tools.platform.base import ContentType, PublishContent

    _XHSTool = XiaohongshuTool()
except ImportError:
    _XHSTool = None
    ContentType = None
    PublishContent = None


class PublishXiaohongshuTool(BaseTool):
    """
    Publish a content draft to Xiaohongshu (Little Red Book).

    Uses CDP (Chrome DevTools Protocol) via Playwright to drive a real browser,
    inheriting the user's login session for bot-detection avoidance.

    Prerequisites:
    - Chrome launched with: --remote-debugging-port=9222
    - User logged into xiaohongshu.com
    - CDP endpoint accessible at localhost:9222
    """

    name = "publish_xiaohongshu"
    description = (
        "Publish a content draft to Xiaohongshu (Little Red Book). "
        "Requires Chrome running with --remote-debugging-port=9222 and user logged in. "
        "Provide title (max 20 chars), body (max 1000 chars), optional image paths/URLs, "
        "and hashtags (max 10). Returns publish result with post URL on success."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Post title (max 20 characters, XHS limit)",
            },
            "body": {
                "type": "string",
                "description": "Post body text (max 1000 characters, XHS limit)",
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Image paths or URLs (1-18 images supported)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hashtags without # prefix (max 10 tags)",
            },
        },
        "required": ["title", "body"],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        title: str,
        body: str,
        images: list[str] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if _XHSTool is None or ContentType is None:
            return ToolResult(
                success=False,
                error="Xiaohongshu tool not available. "
                "Ensure crew.tools.platform.xiaohongshu is importable.",
            )

        # Rate limiting check
        if not self._check_rate_limit():
            return ToolResult(
                success=False,
                error="Rate limit exceeded. Wait before next post (min 60s interval, max 10/day).",
            )

        content = PublishContent(
            title=title[:20],
            body=body[:1000],
            content_type=ContentType.IMAGE_TEXT if images else ContentType.TEXT,
            images=images or [],
            tags=tags or [],
        )

        # Run sync publish in thread pool to avoid blocking
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _XHSTool.publish, content
            )
            if result.is_success():
                return ToolResult(
                    success=True,
                    data={
                        "platform": "xiaohongshu",
                        "post_id": result.data.get("post_id", ""),
                        "url": result.data.get("url", ""),
                        "status": result.status,
                    },
                    metadata={"tool": self.name},
                )
            return ToolResult(
                success=False,
                error=result.error or "Publish failed",
                data=result.data,
                metadata={"tool": self.name},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                metadata={"tool": self.name},
            )

    def _check_rate_limit(self) -> bool:
        # TODO: implement persistent rate limit tracking (file-based or DB)
        return True


class CollectXiaohongshuMetricsTool(BaseTool):
    """Collect post performance metrics from Xiaohongshu."""

    name = "collect_xhs_metrics"
    description = (
        "Collect performance metrics for a Xiaohongshu post. "
        "Provide the post URL or post ID. Returns views, likes, comments, "
        "shares, saves, and engagement rate."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "post_url": {
                "type": "string",
                "description": "URL of the Xiaohongshu post",
            },
            "post_id": {
                "type": "string",
                "description": "Post ID (alternative to post_url)",
            },
        },
        "required": [],
    }

    async def execute(
        self, post_url: str = "", post_id: str = "", **kwargs: Any
    ) -> ToolResult:
        # TODO: implement CDP scraping of post metrics page
        return ToolResult(
            success=True,
            data={
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "saves": 0,
                "engagement_rate": 0.0,
                "note": "Metrics collection not yet implemented — needs CDP page scraping",
            },
            metadata={"tool": self.name},
        )
