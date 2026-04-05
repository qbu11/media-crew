"""Feishu notification tool."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from tastecraft.core.config import get_settings
from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class NotifyFeishuTool(BaseTool):
    """
    Send a notification via Feishu bot webhook.

    Used by pipelines to report: content generation results,
    publish success/failure, weekly evolution report, errors and alerts.
    """

    name = "notify_feishu"
    description = (
        "Send a notification message via Feishu (Lark) bot webhook. "
        "Provide title and body. Optionally specify msg_type (text or interactive card)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Notification title"},
            "body": {"type": "string", "description": "Notification body text"},
            "msg_type": {
                "type": "string",
                "enum": ["text", "interactive"],
                "description": "Message type: text or interactive (card). Default: text",
            },
            "color": {
                "type": "string",
                "enum": ["blue", "green", "yellow", "red"],
                "description": "Card accent color. Default: blue",
            },
        },
        "required": ["title", "body"],
    }

    async def execute(
        self,
        title: str,
        body: str,
        msg_type: str = "text",
        color: str = "blue",
        **kwargs: Any,
    ) -> ToolResult:
        settings = get_settings()
        webhook_url = settings.feishu_webhook_url

        if not webhook_url:
            logger.warning("Feishu webhook not configured, skipping notification")
            return ToolResult(success=True, data={"sent": False, "reason": "not configured"})

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                payload = self._build_card(title, body, color) if msg_type == "interactive" else self._build_text(title, body)
                resp = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    return ToolResult(success=True, data={"sent": True})
                return ToolResult(success=False, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _build_text(self, title: str, body: str) -> dict[str, Any]:
        return {"msg_type": "text", "content": {"text": f"【{title}】\n{body}"}}

    def _build_card(self, title: str, body: str, color: str) -> dict[str, Any]:
        color_map = {"blue": "blue", "green": "green", "yellow": "orange", "red": "red"}
        return {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}, "template": color_map.get(color, "blue")},
                "elements": [{"tag": "markdown", "content": body[:28000]}],
            },
        }
