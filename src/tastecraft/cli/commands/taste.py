"""Taste profile viewing commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def show(ctx: typer.Context) -> None:
    """Show current taste profile."""
    from tastecraft.core.config import get_settings
    from tastecraft.taste.profile import TasteProfile

    settings = get_settings()
    project_id = ctx.obj.get("project") if ctx.obj else settings.get_active_project()

    if not project_id:
        console.print("[red]No active project.[/red]")
        raise typer.Exit(1)

    project_dir = settings.project_dir(project_id)
    taste_path = project_dir / "taste.yaml"

    if not taste_path.exists():
        console.print(f"[red]No taste profile for '{project_id}'.[/red]")
        raise typer.Exit(1)

    raw = taste_path.read_text(encoding="utf-8")
    console.print(f"\n[bold]Taste Profile: {project_id}[/bold]\n")
    console.print(Syntax(raw, "yaml", theme="monokai"))

    # Show learned dimensions if any
    profile = TasteProfile.load(project_dir)
    if profile.learned:
        import json
        console.print("\n[bold]Learned Dimensions:[/bold]\n")
        console.print(Syntax(
            json.dumps(profile.learned, ensure_ascii=False, indent=2),
            "json",
            theme="monokai",
        ))


@app.command()
def edit(ctx: typer.Context) -> None:
    """Open taste.yaml in default editor."""
    import subprocess
    import os

    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_id = ctx.obj.get("project") if ctx.obj else settings.get_active_project()

    if not project_id:
        console.print("[red]No active project.[/red]")
        raise typer.Exit(1)

    taste_path = settings.project_dir(project_id) / "taste.yaml"
    editor = os.environ.get("EDITOR", "code")
    subprocess.run([editor, str(taste_path)], check=False)
