"""Publish command — publish queued content to platforms."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def publish(
    ctx: typer.Context,
    content_id: int | None = typer.Option(None, "--id", help="Specific content ID to publish"),
    platform: str = typer.Option(None, "--platform", help="Target platform: xiaohongshu | wechat | all"),
    all_queued: bool = typer.Option(False, "--all", help="Publish all queued content"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be published without publishing"),
) -> None:
    """Publish content to platforms."""
    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()
    print_mode = (ctx.obj or {}).get("print_mode", False)

    if not project_id:
        console.print("[red]No active project. Run: tastecraft project use <name>[/red]")
        raise typer.Exit(1)

    asyncio.run(_run_publish(settings, project_id, content_id, platform, all_queued, dry_run, print_mode))


async def _run_publish(
    settings: object,
    project_id: str,
    content_id: int | None,
    platform: str | None,
    all_queued: bool,
    dry_run: bool,
    print_mode: bool,
) -> None:
    from tastecraft.core.config import Settings
    from tastecraft.models.base import init_db
    from tastecraft.pipelines.publish import run_publish_pipeline

    assert isinstance(settings, Settings)
    await init_db(settings.database_url)

    if dry_run:
        from tastecraft.models.base import get_session
        from tastecraft.models.tables import Content
        from sqlalchemy import select

        session = await get_session()
        async with session:
            stmt = select(Content).where(
                Content.project_id == project_id,
                Content.status == "queued",
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        if print_mode:
            print(f"{len(rows)} queued items ready to publish")
        else:
            table = Table(title="Queued Content")
            table.add_column("ID", style="dim")
            table.add_column("Title")
            table.add_column("Score", justify="right")
            table.add_column("Created")
            for r in rows:
                table.add_row(str(r.id), r.title[:50], f"{r.quality_score:.1f}", str(r.created_at)[:19])
            console.print(table)
        return

    max_items = 10 if all_queued else 1
    results = await run_publish_pipeline(project_id, max_items=max_items)

    if not results:
        if print_mode:
            print("No queued content to publish")
        else:
            console.print("[yellow]No queued content to publish.[/yellow]")
        return

    if print_mode:
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            print(f"[{status}] {r['title']}: {r.get('output_preview', '')[:100]}")
    else:
        for r in results:
            style = "green" if r["success"] else "red"
            console.print(f"[{style}]{'OK' if r['success'] else 'FAIL'}[/{style}] {r['title']}")
