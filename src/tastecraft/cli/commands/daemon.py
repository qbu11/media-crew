"""Daemon commands — start/stop the scheduler daemon."""

from __future__ import annotations

import asyncio
import subprocess
import sys

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="start")
def start(
    ctx: typer.Context,
    background: bool = typer.Option(False, "--background", help="Run as background process"),
) -> None:
    """Start the TasteCraft scheduler daemon."""
    if background:
        subprocess.Popen(
            [sys.executable, "-m", "tastecraft", "daemon", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print("[green]Daemon started in background.[/green]")
        return

    asyncio.run(_start_daemon(ctx))


async def _start_daemon(ctx: typer.Context) -> None:
    from tastecraft.core.config import get_settings
    from tastecraft.core.logging import setup_logging
    from tastecraft.models.base import init_db
    from tastecraft.services.scheduler import TasteCraftScheduler

    settings = get_settings()
    setup_logging(log_file=settings.logs_dir / "daemon.log")
    await init_db(settings.database_url)

    scheduler = TasteCraftScheduler()
    await scheduler.start()

    console.print("[green]TasteCraft daemon started. Press Ctrl+C to stop.[/green]")
    jobs = scheduler.list_jobs()
    if jobs:
        table = Table(title="Scheduled Jobs")
        table.add_column("Job ID")
        table.add_column("Next Run")
        table.add_column("Trigger")
        for j in jobs:
            table.add_row(
                j["id"],
                str(j.get("next_run", "N/A")),
                j.get("trigger", ""),
            )
        console.print(table)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await scheduler.stop()
        console.print("\n[yellow]Daemon stopped.[/yellow]")


@app.command(name="status")
def status(ctx: typer.Context) -> None:
    """Check daemon status."""
    console.print("[dim]Daemon status check not yet implemented.[/dim]")
    console.print("Use 'tastecraft daemon start --background' to start the daemon.")


@app.command(name="stop")
def stop(ctx: typer.Context) -> None:
    """Stop the TasteCraft scheduler daemon."""
    console.print("[dim]Daemon stop not yet implemented.[/dim]")
    console.print("Kill the daemon process manually, or restart with Ctrl+C.")
