"""Project management commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def create(
    project_id: str = typer.Argument(..., help="Project slug (e.g. ai-startup)"),
    identity: str = typer.Option("", help="Who you are, what you do"),
    tone: str = typer.Option("", help="Content tone/style"),
    platforms: str = typer.Option(
        "xiaohongshu,wechat", help="Target platforms, comma-separated"
    ),
) -> None:
    """Create a new project with initial taste profile."""
    from tastecraft.core.config import get_settings
    from tastecraft.taste.profile import TasteProfile

    settings = get_settings()
    project_dir = settings.project_dir(project_id)

    if project_dir.exists():
        console.print(f"[red]Project '{project_id}' already exists.[/red]")
        raise typer.Exit(1)

    project_dir.mkdir(parents=True)

    # Build initial taste profile
    platform_dict = {}
    for p in platforms.split(","):
        p = p.strip()
        if p:
            platform_dict[p] = {}

    profile = TasteProfile(
        project=project_id,
        identity=identity or _prompt_if_interactive("Identity (who you are): "),
        tone=tone or _prompt_if_interactive("Tone (content style): "),
        platforms=platform_dict,
    )
    profile.save_explicit(project_dir)
    profile.save_learned(project_dir)

    # Create default schedule.yaml
    _create_default_schedule(project_dir)

    # Set as active project
    settings.set_active_project(project_id)

    console.print(f"[green]Project '{project_id}' created.[/green]")
    console.print(f"  Config: {project_dir / 'taste.yaml'}")
    console.print(f"  Edit taste profile: [bold]tastecraft taste show -p {project_id}[/bold]")


@app.command(name="list")
def list_projects() -> None:
    """List all projects."""
    from tastecraft.core.config import get_settings

    settings = get_settings()
    active = settings.get_active_project()

    if not settings.projects_dir.exists():
        console.print("[dim]No projects yet. Run: tastecraft project create <name>[/dim]")
        return

    dirs = sorted(
        d for d in settings.projects_dir.iterdir() if d.is_dir()
    )
    if not dirs:
        console.print("[dim]No projects yet.[/dim]")
        return

    table = Table(title="Projects")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Active", justify="center")

    for d in dirs:
        taste_file = d / "taste.yaml"
        status = "configured" if taste_file.exists() else "empty"
        marker = "*" if d.name == active else ""
        table.add_row(d.name, status, marker)

    console.print(table)


@app.command()
def use(project_id: str = typer.Argument(..., help="Project to activate")) -> None:
    """Switch active project."""
    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_dir = settings.project_dir(project_id)

    if not project_dir.exists():
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        raise typer.Exit(1)

    settings.set_active_project(project_id)
    console.print(f"[green]Active project: {project_id}[/green]")


@app.command()
def status(
    ctx: typer.Context,
) -> None:
    """Show current project status."""
    from tastecraft.core.config import get_settings
    from tastecraft.taste.profile import TasteProfile

    settings = get_settings()
    project_id = ctx.obj.get("project") if ctx.obj else settings.get_active_project()

    if not project_id:
        console.print("[red]No active project. Run: tastecraft project use <name>[/red]")
        raise typer.Exit(1)

    project_dir = settings.project_dir(project_id)
    if not project_dir.exists():
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        raise typer.Exit(1)

    profile = TasteProfile.load(project_dir)

    console.print(f"\n[bold]Project: {project_id}[/bold]")
    console.print(f"  Identity: {profile.identity or '[dim]not set[/dim]'}")
    console.print(f"  Tone: {profile.tone or '[dim]not set[/dim]'}")
    console.print(f"  Audience: {profile.audience or '[dim]not set[/dim]'}")
    console.print(f"  Platforms: {', '.join(profile.platforms.keys()) or '[dim]none[/dim]'}")
    console.print(f"  Taste confidence: {profile.confidence:.0%}")
    console.print(f"  Contents generated: {profile.generation_count}")
    console.print()


def _prompt_if_interactive(prompt: str) -> str:
    """Prompt user for input if running interactively."""
    import sys
    if sys.stdin.isatty():
        return typer.prompt(prompt, default="")
    return ""


def _create_default_schedule(project_dir: Path) -> None:
    """Write default schedule.yaml."""
    import yaml

    schedule = {
        "schedules": {
            "content-pipeline": {
                "cron": "0 9 * * *",
                "pipeline": "content",
                "mode": "auto",
                "enabled": True,
            },
            "publish-batch-1": {
                "cron": "0 12 * * *",
                "pipeline": "publish",
                "max_items": 1,
                "enabled": True,
            },
            "publish-batch-2": {
                "cron": "0 18 * * *",
                "pipeline": "publish",
                "max_items": 1,
                "enabled": True,
            },
            "publish-batch-3": {
                "cron": "0 21 * * *",
                "pipeline": "publish",
                "max_items": 1,
                "enabled": True,
            },
            "analytics": {
                "cron": "0 23 * * *",
                "pipeline": "analytics",
                "enabled": True,
            },
            "evolution": {
                "cron": "0 22 * * 0",
                "pipeline": "evolution",
                "enabled": True,
            },
            "trending": {
                "cron": "0 9 * * 1",
                "pipeline": "trending",
                "enabled": True,
            },
        }
    }
    with open(project_dir / "schedule.yaml", "w", encoding="utf-8") as f:
        yaml.dump(schedule, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _edit_file(path: Path) -> None:
    """Open a file in the user's preferred editor."""
    import os
    import subprocess

    editor = os.environ.get("EDITOR", "code")
    subprocess.run([editor, str(path)], check=False)
