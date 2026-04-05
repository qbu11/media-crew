"""Evolution Pipeline — weekly taste profile refinement from signal data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from tastecraft.core.agent_loop import agent_loop, AgentResult
from tastecraft.core.config import Settings, get_settings
from tastecraft.models.base import get_session
from tastecraft.models.tables import AnalyticsSnapshot, Content, ContentRevision, EvolutionLog, PublishLog
from tastecraft.taste.profile import TasteProfile
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.tools.base import ToolRegistry
from tastecraft.tools.notification import NotifyFeishuTool

logger = logging.getLogger(__name__)


async def run_evolution_pipeline(project_id: str, trigger: str = "weekly") -> dict[str, Any]:
    """
    Evolution Pipeline: analyze weekly signals and refine implicit taste dimensions.

    Signal sources (in priority order):
    1. User edit diffs (CONTENT_REVISION) — highest signal value
    2. Analytics snapshots (ANALYTICS_SNAPSHOT) — performance correlation
    3. Trending consumption vs ignore — topic preference signals

    Constraints:
    - Max 3 dimensions changed per evolution
    - Confidence < 0.5 -> mark as "experimental"
    - Explicit dimensions never auto-modified
    """
    settings = get_settings()
    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    # Aggregate signals
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    signals = await _aggregate_signals(project_id, week_ago)

    if not signals:
        logger.info("No evolution signals for project %s", project_id)
        return {"changed": False, "reason": "no_signals"}

    # Run evolution via agent
    result = await _evolve(settings, project_id, profile, signals, trigger)
    return result


async def _aggregate_signals(
    project_id: str,
    since: datetime,
) -> dict[str, Any]:
    """Gather all evolution signals from the past week."""
    session = await get_session()
    signals: dict[str, Any] = {"edit_diffs": [], "performance": [], "trending": []}

    async with session:
        # User edit diffs
        revisions = await session.execute(
            select(ContentRevision)
            .join(Content, ContentRevision.content_id == Content.id)
            .where(Content.project_id == project_id, ContentRevision.created_at >= since)
        )
        for r in revisions.scalars().all():
            signals["edit_diffs"].append({
                "content_id": r.content_id,
                "diff": r.diff,
                "learned_signals": r.learned_signals,
                "source": r.revision_source,
            })

        # Analytics snapshots (T+7d have full data)
        snapshots = await session.execute(
            select(AnalyticsSnapshot)
            .join(PublishLog, AnalyticsSnapshot.publish_log_id == PublishLog.id)
            .join(Content, PublishLog.content_id == Content.id)
            .where(
                Content.project_id == project_id,
                AnalyticsSnapshot.snapshot_type == "T+7d",
                AnalyticsSnapshot.collected_at >= since,
            )
        )
        for s in snapshots.scalars().all():
            signals["performance"].append({
                "content_id": s.publish_log_id,
                "views": s.views,
                "likes": s.likes,
                "comments": s.comments,
                "engagement_rate": s.engagement_rate,
            })

    return signals


async def _evolve(
    settings: Settings,
    project_id: str,
    profile: TasteProfile,
    signals: dict[str, Any],
    trigger: str,
) -> dict[str, Any]:
    """Run evolution analysis and update taste_learned.json."""
    project_dir = settings.project_dir(project_id)

    # Build system prompt
    system_prompt = build_pipeline_prompt(
        profile,
        pipeline_name="evolution",
        extra_context=(
            "You are analyzing taste evolution signals. "
            "Review the aggregated signals and propose up to 3 taste dimension changes. "
            "Each change must include: dimension name, old value, new value, confidence (0-1), rationale. "
            "Changes with confidence < 0.5 should be marked experimental. "
            "NEVER modify explicit dimensions (identity, tone, taboos, catchphrases, content_goal). "
            "Output a JSON object with 'changes' array and 'confidence_delta'."
        ),
    )

    user_msg = (
        f"Analyze these evolution signals and propose taste profile updates:\n\n"
        f"Signals:\n{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
        f"Current implicit dimensions:\n{json.dumps(profile.implicit, ensure_ascii=False, indent=2)}\n\n"
        "Propose up to 3 dimension changes. Output JSON."
    )

    registry = ToolRegistry()
    registry.register(NotifyFeishuTool())

    result: AgentResult = await agent_loop(
        system_prompt=system_prompt,
        tools=registry,
        initial_message=user_msg,
        model=settings.default_model,
        max_tokens=settings.max_tokens,
        max_turns=10,
        api_key=settings.anthropic_api_key or None,
    )

    # Apply changes
    taste_before = dict(profile.implicit)
    changes_made = {}

    if result.success:
        try:
            # Parse JSON changes from output
            parsed = json.loads(result.output.strip().split("```json")[-1].strip().split("```")[0].strip())
            changes = parsed.get("changes", [])
            confidence_delta = parsed.get("confidence_delta", 0.0)

            for change in changes[:3]:
                dim = change.get("dimension", "")
                if dim and dim not in profile.explicit:
                    profile.implicit[dim] = change.get("new_value")
                    changes_made[dim] = {
                        "old": taste_before.get(dim),
                        "new": change.get("new_value"),
                        "confidence": change.get("confidence", 0.5),
                        "experimental": change.get("confidence", 0.5) < 0.5,
                    }

            profile.confidence = min(1.0, profile.confidence + confidence_delta)
            profile.implicit["_last_evolved"] = datetime.now(timezone.utc).isoformat()
            profile.save_learned(project_dir)

        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not parse evolution output: %s", result.output[:200])

    # Save evolution log
    session = await get_session()
    async with session:
        log = EvolutionLog(
            project_id=project_id,
            trigger=trigger,
            signals_input=signals,
            changes_made=changes_made,
            taste_before=taste_before,
            taste_after=dict(profile.implicit),
            confidence_delta=changes_made.get("_delta", 0.0),
        )
        session.add(log)
        await session.commit()

    return {
        "changed": bool(changes_made),
        "changes": changes_made,
        "new_confidence": profile.confidence,
        "output_preview": result.output[:200],
    }
