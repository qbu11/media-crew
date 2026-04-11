"""Analytics Pipeline — collect post-publish metrics at T+24h/72h/7d."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any

from sqlalchemy import select

from tastecraft.core.agent_loop import AgentResult, agent_loop
from tastecraft.core.config import Settings, get_settings
from tastecraft.models.base import get_session
from tastecraft.models.tables import AnalyticsSnapshot, Content, PublishLog
from tastecraft.taste.profile import TasteProfile
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.tools.base import ToolRegistry
from tastecraft.tools.notification import NotifyFeishuTool
from tastecraft.tools.platform.wechat import CollectWechatMetricsTool
from tastecraft.tools.platform.xiaohongshu import CollectXiaohongshuMetricsTool

logger = logging.getLogger(__name__)

SNAPSHOT_TYPES = ["T+24h", "T+72h", "T+7d"]
SNAPSHOT_HOURS = {"T+24h": 24, "T+72h": 72, "T+7d": 168}


async def run_analytics_pipeline(project_id: str) -> list[dict[str, Any]]:
    """
    Analytics Pipeline: collect metrics for recently published content.

    1. Find all published content needing data collection
    2. For each, determine which snapshot type is due
    3. Collect metrics from platform via CDP/API
    4. Save ANALYTICS_SNAPSHOT
    5. Send Feishu summary if T+7d
    """
    settings = get_settings()

    snapshots = await _collect_pending(settings, project_id)
    if not snapshots:
        logger.info("No analytics snapshots due for project %s", project_id)
        return []

    results = []
    for content_id, pub_id, platform, snapshot_type in snapshots:
        result = await _collect_one(settings, project_id, content_id, pub_id, platform, snapshot_type)
        results.append(result)

    return results


async def _collect_pending(
    _settings: Settings,
    project_id: str,
) -> list[tuple[int, int, str, str]]:
    """
    Find all (content_id, publish_log_id, platform, snapshot_type) tuples
    that are due for collection.
    """
    session = await get_session()
    now = datetime.now(UTC)

    items: list[tuple[int, int, str, str]] = []
    async with session:
        # Find published content with no snapshots yet (or specific snapshot types missing)
        for snapshot_type, hours in SNAPSHOT_HOURS.items():
            threshold = now - timedelta(hours=hours)
            stmt = (
                select(Content.id, PublishLog.id, PublishLog.platform)
                .join(PublishLog, Content.id == PublishLog.content_id)
                .where(
                    Content.project_id == project_id,
                    Content.status == "published",
                    PublishLog.status == "success",
                    PublishLog.published_at <= threshold,
                )
            )
            result = await session.execute(stmt)
            for content_id, pub_id, platform in result.all():
                # Check if this snapshot already exists
                check = await session.execute(
                    select(AnalyticsSnapshot).where(
                        AnalyticsSnapshot.publish_log_id == pub_id,
                        AnalyticsSnapshot.snapshot_type == snapshot_type,
                    )
                )
                if check.scalar_one_or_none() is None:
                    items.append((content_id, pub_id, platform, snapshot_type))

    return items


async def _collect_one(
    settings: Settings,
    project_id: str,
    content_id: int,
    pub_id: int,
    platform: str,
    snapshot_type: str,
) -> dict[str, Any]:
    """Collect metrics for one snapshot."""
    logger.info("Collecting %s metrics: content=%d, platform=%s", snapshot_type, content_id, platform)

    # Build tool registry
    registry = ToolRegistry()
    registry.register(CollectXiaohongshuMetricsTool())
    registry.register(CollectWechatMetricsTool())
    registry.register(NotifyFeishuTool())

    # Build system prompt
    system_prompt = build_pipeline_prompt(
        TasteProfile.load(settings.project_dir(project_id)),
        pipeline_name="analytics",
        extra_context=(
            f"Collect {snapshot_type} metrics for content_id={content_id}, "
            f"platform={platform}, publish_log_id={pub_id}. "
            f"Use the appropriate collect_metrics tool, then save the snapshot."
        ),
    )

    user_msg = (
        f"Collect {snapshot_type} metrics for this content:\n"
        f"- content_id: {content_id}\n"
        f"- platform: {platform}\n"
        f"- publish_log_id: {pub_id}\n\n"
        "Use the appropriate platform metrics tool to collect data, "
        "then save the snapshot to the database."
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

    # Parse metrics from agent text output
    metrics = _parse_metrics(result.output) if result.success else {}

    # Save snapshot to DB
    session = await get_session()
    async with session:
        snapshot = AnalyticsSnapshot(
            publish_log_id=pub_id,
            snapshot_type=snapshot_type,
            views=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            saves=metrics.get("saves", 0),
            new_followers=metrics.get("new_followers", 0),
            engagement_rate=metrics.get("engagement_rate", 0.0),
            raw_data=metrics if metrics else {"raw_output": result.output[:2000]},
        )
        session.add(snapshot)
        await session.commit()

    return {
        "content_id": content_id,
        "snapshot_type": snapshot_type,
        "success": result.success,
        "elapsed": result.elapsed_seconds,
    }


def _parse_metrics(output: str) -> dict[str, Any]:
    """Parse metrics dict from agent text output.

    Tries to extract a JSON object from the output. Looks for ```json blocks
    first, then falls back to parsing the entire output as JSON.
    """
    # Try ```json ... ``` block
    if "```json" in output:
        try:
            json_str = output.split("```json")[-1].split("```")[0].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

    # Try parsing entire output as JSON
    try:
        parsed = json.loads(output.strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try finding a JSON object in the output
    for start_idx in range(len(output)):
        if output[start_idx] == "{":
            for end_idx in range(len(output) - 1, start_idx, -1):
                if output[end_idx] == "}":
                    try:
                        return json.loads(output[start_idx : end_idx + 1])
                    except json.JSONDecodeError:
                        break
            break

    logger.warning("Could not parse metrics from agent output: %s", output[:200])
    return {}
