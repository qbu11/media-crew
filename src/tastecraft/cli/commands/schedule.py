"""Schedule management commands."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="list")
def list_schedules(ctx: typer.Context) -> None:
    """Show current schedules for active project."""
    from tastecraft.core.config import get_settings
    from tastecraft.services.scheduler import load_schedule_rules

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()

    if not project_id:
        console.print("[red]No active project.[/red]")
        raise typer.Exit(1)

    rules = load_schedule_rules(project_id)

    table = Table(title=f"Schedules: {project_id}")
    table.add_column("Pipeline", style="bold")
    table.add_column("Cron")
    for name, cron_expr in rules.items():
        table.add_row(name, cron_expr)
    console.print(table)


@app.command(name="export-cron")
def export_cron(ctx: typer.Context) -> None:
    """Generate crontab entries for the active project."""
    from tastecraft.core.config import get_settings
    from tastecraft.services.scheduler import export_cron

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()

    if not project_id:
        console.print("[red]No active project.[/red]")
        raise typer.Exit(1)

    output = export_cron(project_id)
    print(output)


@app.command(name="edit")
def edit_schedule(ctx: typer.Context) -> None:
    """Open schedule.yaml in editor."""
    import os
    import subprocess

    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()

    if not project_id:
        console.print("[red]No active project.[/red]")
        raise typer.Exit(1)

    schedule_path = settings.project_dir(project_id) / "schedule.yaml"
    editor = os.environ.get("EDITOR", "code")
    subprocess.run([editor, str(schedule_path)], check=False)
