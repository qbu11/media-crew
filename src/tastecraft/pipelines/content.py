"""Content Pipeline — generate content drafts using agent loop."""

from __future__ import annotations

import logging
from typing import Any

from tastecraft.core.agent_loop import AgentResult, agent_loop
from tastecraft.core.config import get_settings
from tastecraft.taste.profile import TasteProfile
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.tools.base import ToolRegistry
from tastecraft.tools.content import SaveDraftTool
from tastecraft.tools.search import ReadContentHistoryTool, SearchTrendingTool

logger = logging.getLogger(__name__)


async def run_content_pipeline(project_id: str) -> dict[str, Any]:
    """
    Content Pipeline: research trending topics and generate a content draft.

    1. Search trending topics in user's domain
    2. Review past content to avoid repetition
    3. Generate a high-quality draft aligned with taste profile
    4. Save draft to database via SaveDraftTool
    """
    settings = get_settings()
    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    registry = ToolRegistry()
    registry.register(SaveDraftTool(project_id=project_id))
    registry.register(SearchTrendingTool(project_id=project_id))
    registry.register(ReadContentHistoryTool(project_id=project_id))

    system_prompt = build_pipeline_prompt(profile, pipeline_name="content")
    user_msg = (
        "Select a trending topic that fits my taste profile, "
        "then generate a high-quality content draft. "
        "Save the draft using the save_draft tool."
    )

    result: AgentResult = await agent_loop(
        system_prompt=system_prompt,
        tools=registry,
        initial_message=user_msg,
        model=settings.default_model,
        max_tokens=settings.max_tokens,
        max_turns=settings.max_turns,
        api_key=settings.anthropic_api_key or None,
    )

    return {
        "success": result.success,
        "output_preview": result.output[:500],
        "turns": result.turns,
        "tool_calls": result.tool_calls,
        "elapsed": result.elapsed_seconds,
    }
