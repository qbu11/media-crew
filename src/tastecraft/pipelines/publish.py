"""Publish Pipeline — adapt and publish queued content to platforms."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from tastecraft.core.agent_loop import agent_loop, AgentResult
from tastecraft.core.config import Settings, get_settings
from tastecraft.models.base import get_session
from tastecraft.models.tables import Content, PublishLog
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.taste.profile import TasteProfile
from tastecraft.tools.base import ToolRegistry
from tastecraft.tools.content import AdaptPlatformTool
from tastecraft.tools.notification import NotifyFeishuTool
from tastecraft.tools.platform.xiaohongshu import PublishXiaohongshuTool
from tastecraft.tools.platform.wechat import PublishWechatTool

logger = logging.getLogger(__name__)


async def run_publish_pipeline(
    project_id: str,
    max_items: int = 1,
) -> list[dict[str, Any]]:
    """
    Publish Pipeline: fetch queued content, adapt, and publish.

    1. Fetch next queued content from DB (FIFO)
    2. Build tool registry with publish + adapt tools
    3. Run agent loop to adapt content and publish
    4. Record results in PublishLog
    5. Send notification
    """
    settings = get_settings()
    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    # Fetch queued content
    contents = await _fetch_queued(project_id, max_items)
    if not contents:
        logger.info("No queued content for project %s", project_id)
        return []

    results = []
    for content in contents:
        result = await _publish_one(settings, profile, project_id, content)
        results.append(result)

    return results


async def _fetch_queued(
    project_id: str, limit: int
) -> list[Content]:
    """Fetch next queued content items from DB."""
    session = await get_session()
    async with session:
        stmt = (
            select(Content)
            .where(Content.project_id == project_id, Content.status == "queued")
            .order_by(Content.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _publish_one(
    settings: Settings,
    profile: TasteProfile,
    project_id: str,
    content: Content,
) -> dict[str, Any]:
    """Publish a single content item."""
    logger.info("Publishing content %d: %s", content.id, content.title[:50])

    # Build system prompt
    system_prompt = build_pipeline_prompt(
        profile,
        pipeline_name="publish",
        extra_context=(
            f"Content to publish:\n"
            f"Title: {content.title}\n"
            f"Body preview: {content.body[:500]}...\n"
            f"Platform targets: {list(profile.platforms.keys())}\n\n"
            "Use adapt_platform to format content for each platform, "
            "then use the appropriate publish tool to publish. "
            "Finally notify via notify_feishu with the result."
        ),
    )

    # Build tool registry
    registry = ToolRegistry()
    registry.register(AdaptPlatformTool())
    registry.register(PublishXiaohongshuTool(project_id=project_id))
    registry.register(PublishWechatTool(project_id=project_id))
    registry.register(NotifyFeishuTool())

    # Run agent loop
    user_msg = (
        f"Publish the following content to all configured platforms:\n\n"
        f"Title: {content.title}\n"
        f"Body: {content.body}\n"
        f"Hashtags: {content.metadata_json.get('hashtags', [])}\n\n"
        "Steps:\n"
        "1. Use adapt_platform to format for each platform\n"
        "2. Use the publish tool for each platform\n"
        "3. Notify results via notify_feishu\n"
    )

    result: AgentResult = await agent_loop(
        system_prompt=system_prompt,
        tools=registry,
        initial_message=user_msg,
        model=settings.default_model,
        max_tokens=settings.max_tokens,
        max_turns=15,
        api_key=settings.anthropic_api_key or None,
    )

    # Update content status
    session = await get_session()
    async with session:
        new_status = "published" if result.success else "failed"
        await session.execute(
            update(Content)
            .where(Content.id == content.id)
            .values(status=new_status)
        )
        await session.commit()

    return {
        "content_id": content.id,
        "title": content.title,
        "success": result.success,
        "turns": result.turns,
        "tool_calls": result.tool_calls,
        "elapsed": result.elapsed_seconds,
        "output_preview": result.output[:200] if result.success else result.output[:500],
    }
