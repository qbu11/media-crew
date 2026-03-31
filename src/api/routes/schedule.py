"""Schedule routes — manage scheduled publishing tasks."""

from datetime import datetime
import logging
from typing import Any
import uuid

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.tools.platform import PLATFORM_REGISTRY
from src.tools.platform.base import PublishContent

router = APIRouter(prefix="/schedule", tags=["Schedule"])
logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────

class ScheduleCreateRequest(BaseModel):
    """Request to create a scheduled publish task."""

    platform: str = Field(..., description="Target platform")
    content: dict[str, Any] = Field(..., description="Content to publish")
    publish_time: str = Field(..., description="ISO8601 datetime for when to publish")
    trigger_type: str = Field(default="date", description="Trigger type: 'date' or 'cron'")
    cron_expression: str | None = Field(
        default=None, description="Cron expression (required if trigger_type='cron')"
    )


class ScheduleCreateResponse(BaseModel):
    """Response for scheduled task creation."""

    job_id: str
    scheduled_for: str


class ScheduleJobItem(BaseModel):
    """Single scheduled job item."""

    job_id: str
    name: str
    next_run_time: str | None
    trigger: str


class ScheduleDeleteResponse(BaseModel):
    """Response for job deletion."""

    job_id: str
    status: str = "cancelled"


# ── Routes ────────────────────────────────────────────────────────

@router.post("")
async def create_schedule(
    req: ScheduleCreateRequest,
    request: Request,
) -> dict[str, Any]:
    """
    Create a scheduled publish task.

    Supports one-time (date) or recurring (cron) schedules.
    """
    scheduler = request.app.state.scheduler

    # Parse publish_time for date trigger
    try:
        publish_dt = datetime.fromisoformat(req.publish_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid publish_time format. Use ISO8601 format.",
        ) from e

    # Create trigger based on type
    if req.trigger_type == "date":
        trigger = DateTrigger(run_date=publish_dt)
    elif req.trigger_type == "cron":
        if not req.cron_expression:
            raise HTTPException(
                status_code=400,
                detail="cron_expression is required when trigger_type='cron'",
            )
        try:
            trigger = CronTrigger.from_crontab(req.cron_expression)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {e}",
            ) from e
    else:
        raise HTTPException(
            status_code=400,
            detail="trigger_type must be 'date' or 'cron'",
        )

    # Generate job ID
    job_id = f"schedule-{req.platform}-{uuid.uuid4().hex[:8]}"

    # Create the publish task function with closure over content and platform
    async def _publish_task() -> None:
        """
        Execute the scheduled publish.

        This function is called by the scheduler when the trigger fires.
        It uses the platform tool to publish the content.
        """
        logger.info("Executing scheduled publish for platform=%s", req.platform)

        if req.platform not in PLATFORM_REGISTRY:
            logger.error("Platform %s not found in registry", req.platform)
            return

        tool_class = PLATFORM_REGISTRY[req.platform]
        tool = tool_class()

        try:
            # Build PublishContent from the request content dict
            publish_content = PublishContent(
                title=req.content.get("title", ""),
                body=req.content.get("body", ""),
                images=req.content.get("images", []),
                tags=req.content.get("tags", []),
                cover_image=req.content.get("cover_image"),
                video=req.content.get("video"),  # Note: field name is 'video', not 'video_path'
                content_type=req.content.get("content_type", "post"),
            )

            # Publish using the platform tool
            result = tool.publish(publish_content)

            if result.success:
                logger.info(
                    "Scheduled publish succeeded: platform=%s, url=%s",
                    req.platform,
                    result.data.get("url") if result.data else None,
                )
            else:
                logger.error(
                    "Scheduled publish failed: platform=%s, error=%s",
                    req.platform,
                    result.error,
                )

        except Exception as e:
            logger.exception(
                "Scheduled publish error: platform=%s, error=%s",
                req.platform,
                e,
            )

    # Add job to scheduler
    scheduler.add_custom_job(
        func=_publish_task,
        trigger=trigger,
        job_id=job_id,
        name=f"Publish to {req.platform}",
    )

    return {
        "success": True,
        "data": ScheduleCreateResponse(
            job_id=job_id,
            scheduled_for=publish_dt.isoformat(),
        ).model_dump(),
    }


@router.get("")
async def list_schedules(request: Request) -> dict[str, Any]:
    """List all scheduled tasks."""
    scheduler = request.app.state.scheduler

    jobs = scheduler.get_jobs()

    items = [
        ScheduleJobItem(
            job_id=job["id"],
            name=job.get("name", ""),
            next_run_time=job.get("next_run_time"),
            trigger=job.get("trigger", ""),
        ).model_dump()
        for job in jobs
    ]

    return {
        "success": True,
        "data": items,
        "meta": {
            "total": len(items),
        },
    }


@router.delete("/{job_id}")
async def cancel_schedule(
    job_id: str,
    request: Request,
) -> dict[str, Any]:
    """Cancel a scheduled task."""
    scheduler = request.app.state.scheduler

    # Check if job exists first
    jobs = scheduler.get_jobs()
    job_ids = [job["id"] for job in jobs]

    if job_id not in job_ids:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {e}",
        ) from e

    return {
        "success": True,
        "data": ScheduleDeleteResponse(
            job_id=job_id,
            status="cancelled",
        ).model_dump(),
    }
