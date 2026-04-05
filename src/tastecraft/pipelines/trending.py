"""Trending Pipeline — scan trending topics in the user's domain."""

from __future__ import annotations

import logging

from tastecraft.core.agent_loop import agent_loop, AgentResult
from tastecraft.core.config import Settings, get_settings
from tastecraft.models.base import get_session
from tastecraft.models.tables import Content
from tastecraft.taste.profile import TasteProfile
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.tools.base import ToolRegistry
from tastecraft.tools.notification import NotifyFeishuTool
from tastecraft.tools.search import SearchTrendingTool

logger = logging.getLogger(__name__)


async def run_trending_pipeline(project_id: str) -> dict:
    """
    Trending Pipeline: scan hot topics in the user's domain.

    1. Search each platform for trending content in domain
    2. Analyze patterns from top-performing content
    3. Cache results for Content Pipeline to reference
    4. Send summary notification
    """
    settings = get_settings()
    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    domain = profile.domain or "trending"

    # Build system prompt
    system_prompt = build_pipeline_prompt(
        profile,
        pipeline_name="trending",
        extra_context=(
            f"Scan trending topics in domain: {domain}\n"
            "Analyze top-performing content patterns and cache results for content generation."
        ),
    )

    # Build tool registry
    registry = ToolRegistry()
    registry.register(SearchTrendingTool(project_id=project_id))
    registry.register(NotifyFeishuTool())

    user_msg = (
        f"Scan trending topics in the '{domain}' domain on Xiaohongshu and WeChat.\n"
        "For each trending topic, extract: title, score, source, URL.\n"
        "Analyze patterns from top content: common title formats, content styles, hashtags.\n"
        "Return a structured summary of top 10 trending topics and key patterns."
    )

    result: AgentResult = await agent_loop(
        system_prompt=system_prompt,
        tools=registry,
        initial_message=user_msg,
        model=settings.default_model,
        max_tokens=settings.max_tokens,
        max_turns=10,
        api_key=settings.anthropic_api_key or None,
    )

    return {
        "success": result.success,
        "output_preview": result.output[:500],
        "turns": result.turns,
        "elapsed": result.elapsed_seconds,
    }
