"""Run pipeline command — execute a specific pipeline for a project."""

from __future__ import annotations

import asyncio
import json

from rich.console import Console
import typer

console = Console()


def run_pipeline(
    ctx: typer.Context,
    pipeline: str = typer.Argument(help="Pipeline: content | publish | analytics | evolution | trending"),
) -> None:
    """Run a specific pipeline for the active project."""
    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()
    print_mode = (ctx.obj or {}).get("print_mode", False)

    if not project_id:
        console.print("[red]No active project. Run: tastecraft project use <name>[/red]")
        raise typer.Exit(1)

    valid = {"content", "publish", "analytics", "evolution", "trending"}
    if pipeline not in valid:
        console.print(f"[red]Unknown pipeline: {pipeline}[/red]")
        console.print(f"Available: {', '.join(valid)}")
        raise typer.Exit(1)

    asyncio.run(_run(settings, project_id, pipeline, print_mode))


async def _run(settings: object, project_id: str, pipeline: str, print_mode: bool) -> None:
    from tastecraft.core.config import Settings
    from tastecraft.models.base import init_db

    assert isinstance(settings, Settings)
    await init_db(settings.database_url)

    results: list[object] = []

    if pipeline == "publish":
        from tastecraft.pipelines.publish import run_publish_pipeline
        results = await run_publish_pipeline(project_id)

    elif pipeline == "analytics":
        from tastecraft.pipelines.analytics import run_analytics_pipeline
        results = await run_analytics_pipeline(project_id)

    elif pipeline == "evolution":
        from tastecraft.pipelines.evolution import run_evolution_pipeline
        results = [await run_evolution_pipeline(project_id)]

    elif pipeline == "trending":
        from tastecraft.pipelines.trending import run_trending_pipeline
        results = [await run_trending_pipeline(project_id)]

    elif pipeline == "content":
        from tastecraft.pipelines.content import run_content_pipeline
        results = [await run_content_pipeline(project_id)]

    if print_mode:
        print(json.dumps(results, ensure_ascii=False, default=str))
    else:
        for r in results:
            ok = isinstance(r, dict) and r.get("success", True)
            console.print(f"[green]{r}[/green]" if ok else f"[yellow]{r}[/yellow]")
