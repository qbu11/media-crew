"""Scheduler service — cron export and APScheduler daemon."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tastecraft.core.config import get_settings
from tastecraft.models.base import get_session
from tastecraft.models.tables import ScheduleRule
from tastecraft.pipelines.analytics import run_analytics_pipeline
from tastecraft.pipelines.evolution import run_evolution_pipeline
from tastecraft.pipelines.publish import run_publish_pipeline
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Pipeline name -> CLI command mapping
PIPELINE_COMMANDS = {
    "content": "content",
    "publish": "publish",
    "analytics": "analytics",
    "evolution": "evolution",
    "trending": "trending",
}

PIPELINE_HANDLERS = {
    "content": None,  # handled by generate command
    "publish": run_publish_pipeline,
    "analytics": run_analytics_pipeline,
    "evolution": run_evolution_pipeline,
    "trending": None,  # handled by trending pipeline
}

DEFAULT_SCHEDULE = {
    "content": "0 9 * * *",      # Daily 09:00
    "publish": "0 12,18,21 * * *", # 12:00, 18:00, 21:00
    "analytics": "0 23 * * *",     # Daily 23:00
    "evolution": "0 22 * * 0",   # Sunday 22:00
    "trending": "0 9 * * 1",      # Monday 09:00
}


def load_schedule_rules(project_id: str) -> dict[str, str]:
    """Load schedule rules from project's schedule.yaml."""
    settings = get_settings()
    schedule_file = settings.project_dir(project_id) / "schedule.yaml"

    rules = dict(DEFAULT_SCHEDULE)  # start with defaults
    if schedule_file.exists():
        with open(schedule_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            schedules = data.get("schedules", {})
            for name, cfg in schedules.items():
                if isinstance(cfg, dict) and cfg.get("enabled", True):
                    rules[name] = cfg.get("cron", DEFAULT_SCHEDULE.get(name, ""))

    return rules


def export_cron(project_id: str) -> str:
    """
    Generate crontab entries for a project.
    Outputs shell commands that can be piped to crontab.
    """
    settings = get_settings()
    rules = load_schedule_rules(project_id)
    lines = [f"# --- Project: {project_id} ---"]

    for pipeline, cron_expr in rules.items():
        cmd = PIPELINE_COMMANDS.get(pipeline, pipeline)
        log_file = settings.logs_dir / project_id / f"{pipeline}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        entry = (
            f"{_cron_minute(cron_expr)} { _cron_hour(cron_expr)} "
            f"{_cron_dom(cron_expr)} {_cron_month(cron_expr)} {_cron_dow(cron_expr)} "
            f"tastecraft run {cmd} -p {project_id} --print >> {log_file} 2>&1"
        )
        lines.append(entry)

    return "\n".join(lines)


def _cron_minute(expr: str) -> str:
    return expr.split()[0] if len(expr.split()) > 0 else "0"


def _cron_hour(expr: str) -> str:
    return expr.split()[1] if len(expr.split()) > 1 else "9"


def _cron_dom(expr: str) -> str:
    return expr.split()[2] if len(expr.split()) > 2 else "*"


def _cron_month(expr: str) -> str:
    return expr.split()[3] if len(expr.split()) > 3 else "*"


def _cron_dow(expr: str) -> str:
    return expr.split()[4] if len(expr.split()) > 4 else "*"


class TasteCraftScheduler:
    """
    APScheduler-based daemon for running pipelines.

    Alternative to system cron — runs pipelines in-process.
    Useful when you want dynamic scheduling or simpler deployment.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=get_settings().timezone)
        self._running = False

    def load_projects(self) -> None:
        """Load all active project schedules and register jobs."""
        settings = get_settings()
        for project_dir in settings.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            project_id = project_dir.name
            rules = load_schedule_rules(project_id)

            for pipeline, cron_expr in rules.items():
                parts = cron_expr.split()
                if len(parts) != 5:
                    continue
                minute, hour, dom, month, dow = parts

                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=dom if dom != "*" else None,
                    month=month if month != "*" else None,
                    day_of_week=dow if dow != "*" else None,
                    timezone=settings.timezone,
                )

                handler = PIPELINE_HANDLERS.get(pipeline)
                if handler:
                    self._scheduler.add_job(
                        handler,
                        trigger=trigger,
                        args=[project_id],
                        id=f"{project_id}_{pipeline}",
                        replace_existing=True,
                        misfire_grace_time=3600,
                    )
                    logger.info("Registered job: %s_%s (%s)", project_id, pipeline, cron_expr)

    async def start(self) -> None:
        """Start the scheduler daemon."""
        self.load_projects()
        self._scheduler.start()
        self._running = True
        logger.info("TasteCraft scheduler daemon started")
        logger.info("Jobs: %s", list(self._scheduler.get_jobs()))

    async def stop(self) -> None:
        """Stop the scheduler daemon."""
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("TasteCraft scheduler daemon stopped")

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all scheduled jobs."""
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": j.id,
                "next_run": str(j.next_run_time) if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            for j in jobs
        ]
