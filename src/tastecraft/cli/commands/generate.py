"""Generate content command — interactive and auto modes."""

from __future__ import annotations

import asyncio
import uuid

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def generate(
    ctx: typer.Context,
    topic: str = typer.Option("", "--topic", "-t", help="Specific topic to write about"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Generation mode: auto | collab"),
) -> None:
    """Generate content for the active project."""
    from tastecraft.core.config import get_settings

    settings = get_settings()
    project_id = (ctx.obj or {}).get("project") or settings.get_active_project()
    print_mode = (ctx.obj or {}).get("print_mode", False)

    if not project_id:
        console.print("[red]No active project. Run: tastecraft project use <name>[/red]")
        raise typer.Exit(1)

    project_dir = settings.project_dir(project_id)
    if not project_dir.exists():
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        raise typer.Exit(1)

    asyncio.run(_run_generate(settings, project_id, topic, mode, print_mode))


async def _run_generate(
    settings: object,
    project_id: str,
    topic: str,
    mode: str,
    print_mode: bool,
) -> None:
    """Async content generation flow."""
    from tastecraft.core.agent_loop import agent_loop
    from tastecraft.core.config import Settings
    from tastecraft.models.base import init_db
    from tastecraft.taste.profile import TasteProfile
    from tastecraft.taste.prompt_builder import build_pipeline_prompt
    from tastecraft.tools.base import ToolRegistry
    from tastecraft.tools.content import SaveDraftTool

    assert isinstance(settings, Settings)

    # Init DB
    await init_db(settings.database_url)

    # Load taste profile
    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    if not print_mode:
        console.print(Panel(
            f"[bold]TasteCraft[/bold] | Project: {project_id} | "
            f"Taste confidence: {profile.confidence:.0%}",
            style="blue",
        ))

    # Build system prompt
    system_prompt = build_pipeline_prompt(
        profile,
        pipeline_name="content",
        extra_context=_build_content_context(topic, mode),
    )

    # Register tools
    registry = ToolRegistry()
    registry.register(SaveDraftTool(project_id=project_id))

    # Build user message
    if topic:
        user_msg = f"Generate a content draft about: {topic}"
    else:
        user_msg = (
            "Select a trending topic that fits my taste profile, "
            "then generate a high-quality content draft. "
            "Save the draft using the save_draft tool."
        )

    if not print_mode:
        console.print(f"\n[dim]Generating content (mode={mode})...[/dim]\n")

    # Run agent loop
    run_id = uuid.uuid4().hex[:12]
    result = await agent_loop(
        system_prompt=system_prompt,
        tools=registry,
        initial_message=user_msg,
        model=settings.default_model,
        max_tokens=settings.max_tokens,
        max_turns=settings.max_turns,
        api_key=settings.anthropic_api_key or None,
    )

    if result.success:
        # Auto-save to DB
        saved_id = await _save_result(result.output, project_id)

        if print_mode:
            print(result.output)
        else:
            console.print(Panel(result.output, title="Generated Content", border_style="green"))
            extra = f" | Saved as content #{saved_id}" if saved_id else ""
            console.print(
                f"\n[dim]Completed in {result.turns} turns, "
                f"{result.tool_calls} tool calls, "
                f"{result.elapsed_seconds:.1f}s{extra}[/dim]"
            )
    else:
        console.print(f"[red]Generation failed: {result.output}[/red]")
        raise typer.Exit(1)


async def _save_result(output: str, project_id: str) -> int | None:
    """Parse agent output and save as draft content."""
    from tastecraft.models.base import get_session
    from tastecraft.models.tables import Content

    if not output.strip():
        return None

    # Extract title from first line (typically **Title** or # Title)
    lines = output.strip().split("\n")
    title = lines[0].strip().lstrip("#* ").rstrip("*")
    if not title:
        title = f"Untitled ({project_id})"

    try:
        session = await get_session()
        async with session:
            content = Content(
                project_id=project_id,
                title=title[:200],
                body=output,
                status="draft",
                quality_score=0.0,
            )
            session.add(content)
            await session.commit()
            await session.refresh(content)
            return content.id
    except Exception:
        return None


def _build_content_context(topic: str, mode: str) -> str:
    """Build extra context for content pipeline."""
    parts = [f"Mode: {mode}"]
    if topic:
        parts.append(f"Requested topic: {topic}")
    if mode == "collab":
        parts.append(
            "In collab mode, generate a content framework with slots "
            "marked as [USER_INPUT_REQUIRED: description] where user input is needed."
        )
    return "\n".join(parts)
