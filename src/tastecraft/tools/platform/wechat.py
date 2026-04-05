"""WeChat platform tool — wrappers existing wechat.py logic."""

from __future__ import annotations

import asyncio
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

# Reuse existing publishing logic from the CrewAI-era codebase
try:
    from crew.tools.platform.wechat import WechatTool
    from crew.tools.platform.base import ContentType, PublishContent

    _WechatTool = WechatTool()
except ImportError:
    _WechatTool = None
    ContentType = None
    PublishContent = None


class PublishWechatTool(BaseTool):
    """
    Publish a content draft to WeChat Official Account (微信公众号).

    Supports two methods:
    - API method (primary): Fast, requires AppID + AppSecret
    - Browser method: Uses CDP for cases not covered by API

    Prerequisites:
    - AppID and AppSecret configured in config or environment
    - WeChat Official Account with publishing permissions
    """

    name = "publish_wechat"
    description = (
        "Publish a content draft to WeChat Official Account (微信公众号). "
        "Requires AppID and AppSecret configured. Supports article posting with "
        "HTML content. Returns publish result with article URL on success."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Article title (max 64 characters, WeChat limit)",
            },
            "body": {
                "type": "string",
                "description": "Article body (HTML or plain text)",
            },
            "author": {
                "type": "string",
                "description": "Author name (optional, defaults to account setting)",
            },
            "digest": {
                "type": "string",
                "description": "Article summary/digest (max 120 chars, auto-generated if empty)",
            },
            "cover_image": {
                "type": "string",
                "description": "Cover image URL or path",
            },
            "need_open_comment": {
                "type": "boolean",
                "description": "Whether to open comments (default: true)",
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
        author: str = "",
        digest: str = "",
        cover_image: str = "",
        need_open_comment: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        if _WechatTool is None:
            return ToolResult(
                success=False,
                error="WeChat tool not available. "
                "Ensure crew.tools.platform.wechat is importable.",
            )

        # Rate limiting check
        if not self._check_rate_limit():
            return ToolResult(
                success=False,
                error="Rate limit exceeded. WeChat allows 1 push per day via API.",
            )

        # Build HTML content from plain text
        html_body = self._to_html(body)

        content = PublishContent(
            title=title[:64],
            body=html_body,
            content_type=ContentType.ARTICLE,
            images=[],
            tags=[],
        )

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _WechatTool.publish, content
            )
            if result.is_success():
                return ToolResult(
                    success=True,
                    data={
                        "platform": "wechat",
                        "media_id": result.data.get("media_id", ""),
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
        # TODO: implement persistent rate limit tracking
        return True

    def _to_html(self, text: str) -> str:
        """Convert plain text to basic HTML for WeChat."""
        paragraphs = text.split("\n\n")
        html_parts = [
            f"<p>{p.replace('\n', '<br/>')}</p>"
            for p in paragraphs
            if p.strip()
        ]
        return (
            "<!DOCTYPE html><html><body>"
            + "".join(html_parts)
            + "</body></html>"
        )


class CollectWechatMetricsTool(BaseTool):
    """Collect post performance metrics from WeChat Official Account."""

    name = "collect_wechat_metrics"
    description = (
        "Collect performance metrics for a WeChat Official Account article. "
        "Uses WeChat datacube API to fetch article summary stats. "
        "Returns views, reads, likes, comments, shares, and completion rate."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "article_id": {
                "type": "string",
                "description": "Article media ID from WeChat API",
            },
            "article_url": {
                "type": "string",
                "description": "Article URL (alternative to article_id)",
            },
        },
        "required": [],
    }

    async def execute(
        self, article_id: str = "", article_url: str = "", **kwargs: Any
    ) -> ToolResult:
        # TODO: implement WeChat datacube API call
        return ToolResult(
            success=True,
            data={
                "views": 0,
                "reads": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "completion_rate": 0.0,
                "note": "Metrics collection not yet implemented — needs WeChat datacube API",
            },
            metadata={"tool": self.name},
        )
