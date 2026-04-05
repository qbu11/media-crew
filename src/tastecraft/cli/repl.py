"""Interactive REPL mode for content generation."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from tastecraft.core.agent_loop import AgentResult, agent_loop
from tastecraft.core.config import Settings
from tastecraft.models.base import init_db
from tastecraft.taste.profile import TasteProfile
from tastecraft.taste.prompt_builder import build_pipeline_prompt
from tastecraft.tools.base import ToolRegistry

console = Console()


class REPLSession:
    """
    Interactive content generation REPL.

    Flow:
    1. Show trending topic suggestions
    2. User picks topic or enters custom
    3. Agent generates draft
    4. User reviews inline: [e]dit / [a]ccept / [r]egenerate / [q]uit
    5. On accept: queue content
    """

    def __init__(
        self,
        settings: Settings,
        project_id: str,
        profile: TasteProfile,
        registry: ToolRegistry,
    ) -> None:
        self.settings = settings
        self.project_id = project_id
        self.profile = profile
        self.registry = registry
        self.session_id = uuid.uuid4().hex[:8]
        self.messages: list[dict[str, Any]] = []
        self.draft_saved = False
        self.draft_content_id: int | None = None

    async def run(self) -> None:
        """Main REPL loop."""
        console.print(
            Panel(
                f"[bold]TasteCraft REPL[/bold] | Session: {self.session_id} "
                f"| Project: {self.project_id} | "
                f"Taste confidence: {self.profile.confidence:.0%}",
                style="blue",
            )
        )
        console.print()

        # Step 1: Topic selection
        topic = await self._select_topic()
        if topic is None:
            return

        # Step 2: Generate
        await self._generate(topic)

        # Step 3: Review loop
        if self.draft_saved:
            await self._review_loop()

    async def _select_topic(self) -> str | None:
        """Show topic suggestions and let user pick."""
        from tastecraft.tools.search import SearchTrendingTool

        search_tool = SearchTrendingTool(project_id=self.project_id)
        result = await search_tool.execute(query=self.profile.domain or "trending")

        if not result.success or not result.data:
            console.print("[dim]No trending topics found. Enter a custom topic:[/dim]")
            topic = Prompt.ask("topic")
            return topic

        topics = result.data.get("topics", [])[:5]
        if not topics:
            console.print("[dim]No topics. Enter custom:[/dim]")
            topic = Prompt.ask("topic")
            return topic

        console.print("[bold]Trending topic suggestions:[/bold]")
        for i, t in enumerate(topics, 1):
            score = t.get("score", 0)
            title = t.get("title", t.get("topic", ""))
            console.print(f"  {i}. {title} [dim](score: {score})[/dim]")
        console.print(f"  0. Enter custom topic")

        choice = Prompt.ask(
            "Pick a number or 0 for custom",
            choices=["0", "1", "2", "3", "4", "5"],
            default="1",
        )
        if choice == "0":
            return Prompt.ask("topic")
        return topics[int(choice) - 1].get("title", topics[int(choice) - 1].get("topic", ""))

    async def _generate(self, topic: str) -> None:
        """Generate content draft for the topic."""
        console.print(f"\n[cyan]Generating draft about:[/cyan] {topic}")
        console.print()

        system_prompt = build_pipeline_prompt(
            self.profile,
            pipeline_name="content",
            extra_context=f"Requested topic: {topic}\nMode: REPL (interactive)",
        )

        user_msg = (
            f"Generate a high-quality content draft about: {topic}\n\n"
            "Requirements:\n"
            "1. Title: catchy, fits the taste profile\n"
            "2. Body: well-structured, engaging opening, clear value proposition\n"
            "3. Hashtags: 3-8 relevant tags\n"
            "4. Metadata: suggested images or visual direction\n\n"
            "After generating, use the save_draft tool to save the draft, "
            "then describe what was saved and what quality score was assigned."
        )

        with console.status("[bold green]Generating...") as status:
            result = await agent_loop(
                system_prompt=system_prompt,
                tools=self.registry,
                initial_message=user_msg,
                model=self.settings.default_model,
                max_tokens=self.settings.max_tokens,
                max_turns=self.settings.max_turns,
                api_key=self.settings.anthropic_api_key or None,
            )

        if result.success:
            console.print()
            console.print(Panel(Markdown(result.output), title="Draft", border_style="green"))
            console.print(
                f"\n[dim]{result.turns} turns, {result.tool_calls} tool calls, "
                f"{result.elapsed_seconds:.1f}s[/dim]"
            )
            # Check if draft was saved
            if "content_id" in result.output.lower() or "saved" in result.output.lower():
                self.draft_saved = True
        else:
            console.print(f"[red]Generation failed: {result.output}[/red]")

    async def _review_loop(self) -> None:
        """Inline review: edit / accept / regenerate / quit."""
        while True:
            console.print()
            action = Prompt.ask(
                "[bold]Action[/bold]",
                choices=["e", "a", "r", "q"],
                default="a",
            )

            if action == "e":
                # Edit in editor
                from tastecraft.cli.commands.project import _edit_file
                _edit_file(self.settings.project_dir(self.project_id) / "taste.yaml")
                console.print("[dim]Re-run generation to apply changes...[/dim]")
                break

            elif action == "a":
                # Accept and queue
                await self._queue_draft()
                break

            elif action == "r":
                # Regenerate
                console.print("[dim]Regenerating...[/dim]")
                break

            elif action == "q":
                console.print("[yellow]Draft saved. Exiting REPL.[/yellow]")
                break

    async def _queue_draft(self) -> None:
        """Queue the draft for publishing."""
        from tastecraft.models.base import get_session
        from tastecraft.models.tables import Content

        async with get_session() as sess:
            from sqlalchemy import update

            await sess.execute(
                update(Content)
                .where(Content.id == self.draft_content_id)
                .values(status="queued")
            )
            await sess.commit()

        console.print("[green]Draft queued for publishing![/green]")


async def run_repl(settings: Settings, project_id: str) -> None:
    """Start an interactive REPL session."""
    await init_db(settings.database_url)

    project_dir = settings.project_dir(project_id)
    profile = TasteProfile.load(project_dir)

    # Build tool registry
    registry = ToolRegistry()
    from tastecraft.tools.content import SaveDraftTool
    registry.register(SaveDraftTool(project_id=project_id))

    session = REPLSession(settings, project_id, profile, registry)
    await session.run()
