"""TasteCraft CLI — main Typer application."""

from __future__ import annotations

import typer

from tastecraft.cli.commands import daemon, generate, project, publish, run, schedule, taste

app = typer.Typer(
    name="tastecraft",
    help="TasteCraft — CLI-first AI content engine",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register sub-commands
app.add_typer(project.app, name="project", help="Manage projects")
app.add_typer(taste.app, name="taste", help="View/edit taste profiles")
app.add_typer(schedule.app, name="schedule", help="Manage cron schedules")
app.command(name="generate")(generate.generate)
app.command(name="publish")(publish.publish)
app.command(name="run")(run.run_pipeline)
app.add_typer(daemon.app, name="daemon", help="Start/stop scheduler daemon")


@app.callback()
def main(
    ctx: typer.Context,
    project_name: str = typer.Option(
        None, "-p", "--project", help="Target project (overrides active project)"
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose logging"),
    print_mode: bool = typer.Option(
        False, "--print", help="Non-interactive output (for cron/pipes)"
    ),
) -> None:
    """TasteCraft — CLI-first AI content engine."""
    from tastecraft.core.config import get_settings
    from tastecraft.core.logging import setup_logging

    settings = get_settings()
    setup_logging(
        level="DEBUG" if verbose else settings.log_level,
        log_file=settings.logs_dir / "tastecraft.log",
        verbose=verbose,
    )

    # Store shared state in context
    ctx.ensure_object(dict)
    ctx.obj["settings"] = settings
    ctx.obj["verbose"] = verbose
    ctx.obj["print_mode"] = print_mode

    # Resolve project
    if project_name:
        ctx.obj["project"] = project_name
    else:
        ctx.obj["project"] = settings.get_active_project()
