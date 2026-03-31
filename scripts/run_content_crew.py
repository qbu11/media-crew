#!/usr/bin/env python3
"""
Content Crew CLI - Run the content production pipeline.

Usage:
    python scripts/run_content_crew.py --topic "AI创业" --platforms "xiaohongshu,wechat"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import print as rprint

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.crew.crews.content_crew import ContentCrew, ContentCrewInput, ContentCrewResult
from src.schemas import ContentBrief, ContentDraft, DraftStatus, PlatformType

app = typer.Typer(
    name="content-crew",
    help="Run the content production pipeline: research -> write -> review",
    add_completion=False,
)
console = Console()


def parse_platforms(platforms_str: str) -> list[str]:
    """Parse comma-separated platforms string."""
    valid_platforms = [p.value for p in PlatformType]
    platforms = [p.strip().lower() for p in platforms_str.split(",")]

    for platform in platforms:
        if platform not in valid_platforms:
            console.print(f"[red]Error: Invalid platform '{platform}'[/red]")
            console.print(f"[yellow]Valid platforms: {', '.join(valid_platforms)}[/yellow]")
            raise typer.Exit(1)

    return platforms


def save_output(data: dict, output_path: Path) -> None:
    """Save output to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert datetime objects to ISO format
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=serialize)

    console.print(f"[green]Output saved to:[/green] {output_path}")


def display_result(result: ContentCrewResult) -> None:
    """Display the crew result in a formatted way."""
    # Status panel
    status_color = "green" if result.is_success() else "red"
    status_text = "SUCCESS" if result.is_success() else "FAILED"

    console.print()
    console.print(Panel(
        f"[{status_color}]{status_text}[/{status_color}] | "
        f"Execution time: {result.execution_time:.2f}s",
        title="[bold]Content Crew Result[/bold]",
        border_style=status_color,
    ))

    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        return

    # Topic report
    if result.topic_report:
        console.print("\n[bold cyan]📋 Topic Research Report[/bold cyan]")
        topics = result.topic_report.get("topics", [])
        if isinstance(topics, list):
            for i, topic in enumerate(topics[:5], 1):
                title = topic.get("title", "N/A")
                score = topic.get("potential_score", 0)
                console.print(f"  {i}. {title} [dim](Score: {score})[/dim]")

    # Content draft
    if result.content_draft:
        console.print("\n[bold cyan]✍️ Content Draft[/bold cyan]")
        title = result.content_draft.get("title", "N/A")
        summary = result.content_draft.get("summary", "")
        tags = result.content_draft.get("tags", [])

        console.print(f"  [bold]Title:[/bold] {title}")
        if summary:
            console.print(f"  [bold]Summary:[/bold] {summary[:100]}...")
        if tags:
            console.print(f"  [bold]Tags:[/bold] {', '.join(tags[:5])}")

    # Review report
    if result.review_report:
        console.print("\n[bold cyan]🔍 Review Report[/bold cyan]")
        review_result = result.review_report.get("result", "unknown")
        overall_score = result.review_report.get("overall_score", 0)

        review_color = "green" if review_result == "approved" else "yellow"
        console.print(f"  [bold]Result:[/bold] [{review_color}]{review_result}[/{review_color}]")
        console.print(f"  [bold]Score:[/bold] {overall_score}/100")

        issues = result.review_report.get("issues", [])
        if issues:
            console.print(f"  [bold]Issues:[/bold] {len(issues)} found")
            for issue in issues[:3]:
                console.print(f"    - {issue}")

        suggestions = result.review_report.get("suggestions", [])
        if suggestions:
            console.print(f"  [bold]Suggestions:[/bold]")
            for suggestion in suggestions[:3]:
                console.print(f"    💡 {suggestion}")

    # Approval status
    console.print()
    if result.is_approved:
        console.print("[green bold]✅ Content approved and ready for publishing![/green bold]")
    else:
        console.print("[yellow bold]⚠️ Content needs revision before publishing[/yellow bold]")


@app.command()
def run(
    topic: Annotated[str, typer.Option("--topic", "-t", help="Main topic for content creation")],
    platforms: Annotated[str, typer.Option(
        "--platforms", "-p",
        help="Comma-separated target platforms (e.g., 'xiaohongshu,wechat')"
    )] = "xiaohongshu",
    brand_voice: Annotated[str, typer.Option(
        "--brand-voice", "-b",
        help="Brand voice description"
    )] = "专业但不失亲和",
    content_type: Annotated[str, typer.Option(
        "--content-type", "-c",
        help="Content type: article, video, image_post"
    )] = "article",
    research_depth: Annotated[str, typer.Option(
        "--depth", "-d",
        help="Research depth: basic, standard, deep"
    )] = "standard",
    viral_category: Annotated[str, typer.Option(
        "--viral-category", "-vc",
        help="Viral content category (美妆/职场/穿搭/情感/干货/科技教程等)"
    )] = None,
    output: Annotated[Path | None, typer.Option(
        "--output", "-o",
        help="Output file path for results (JSON)"
    )] = None,
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Simulate execution without running the crew"
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
    enable_human_review: Annotated[bool, typer.Option(
        "--human-review/--no-human-review",
        help="Enable human review step"
    )] = False,
) -> None:
    """
    Run the content production crew.

    The crew will:
    1. Research trending topics related to your topic
    2. Create content drafts for each platform
    3. Review content quality and compliance

    Example:
        python scripts/run_content_crew.py \\
            --topic "AI创业" \\
            --platforms "xiaohongshu,wechat" \\
            --brand-voice "专业但不失亲和" \\
            --output "data/content/draft-001.json"
    """
    # Parse and validate platforms
    platform_list = parse_platforms(platforms)

    # Display input summary
    console.print(Panel(
        f"[bold]Topic:[/bold] {topic}\n"
        f"[bold]Platforms:[/bold] {', '.join(platform_list)}\n"
        f"[bold]Brand Voice:[/bold] {brand_voice}\n"
        f"[bold]Content Type:[/bold] {content_type}\n"
        f"[bold]Research Depth:[/bold] {research_depth}\n"
        f"[bold]Human Review:[/bold] {'Yes' if enable_human_review else 'No'}",
        title="[bold]Content Crew Input[/bold]",
        border_style="blue",
    ))

    if dry_run:
        console.print("\n[yellow]DRY RUN - Simulating execution...[/yellow]")

        # Simulate result
        mock_result = {
            "status": "success",
            "dry_run": True,
            "topic": topic,
            "platforms": platform_list,
            "brand_voice": brand_voice,
            "content_type": content_type,
            "research_depth": research_depth,
            "timestamp": datetime.now().isoformat(),
            "estimated_duration": "2-5 minutes",
            "steps": [
                "1. Topic research (TopicResearcher)",
                "2. Content creation (ContentWriter)",
                "3. Content review (ContentReviewer)",
            ],
        }

        if output:
            save_output(mock_result, output)
        else:
            console.print_json(data=mock_result)

        console.print("\n[green]Dry run completed successfully![/green]")
        return

    # Extract keywords from topic
    keywords = [kw.strip() for kw in topic.split() if kw.strip()]
    if not keywords:
        keywords = [topic]

    # Create crew input
    crew_input = ContentCrewInput(
        topic=topic,
        target_platform=platform_list[0],  # Primary platform
        content_type=content_type,
        research_depth=research_depth,
        enable_human_review=enable_human_review,
        viral_category=viral_category,
    )

    # Run the crew with progress indication
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Running content crew...[/cyan]",
                total=100
            )

            # Create and execute crew
            crew = ContentCrew.create(
                enable_human_review=enable_human_review,
                verbose=verbose,
            )

            progress.update(task, advance=10, description="[cyan]Researching topics...[/cyan]")

            result = crew.execute(crew_input)

            progress.update(task, advance=90, description="[cyan]Finalizing...[/cyan]")
            progress.update(task, completed=100)

        # Display results
        display_result(result)

        # Save output if specified
        if output and result.is_success():
            output_data = {
                "status": result.status.value,
                "topic": topic,
                "platforms": platform_list,
                "brand_voice": brand_voice,
                "topic_report": result.topic_report,
                "content_draft": result.content_draft,
                "review_report": result.review_report,
                "execution_time": result.execution_time,
                "timestamp": datetime.now().isoformat(),
            }
            save_output(output_data, output)

        # Exit with appropriate code
        if not result.is_success():
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def platforms() -> None:
    """List all supported platforms."""
    table = Table(title="Supported Platforms")
    table.add_column("Platform", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Character Limit", style="yellow")

    limits = {
        "xiaohongshu": 1000,
        "wechat": 20000,
        "weibo": 2000,
        "zhihu": 50000,
        "douyin": 2200,
        "bilibili": 2000,
    }

    for platform in PlatformType:
        table.add_row(
            platform.name.title(),
            platform.value,
            str(limits.get(platform.value, "N/A"))
        )

    console.print(table)


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold cyan]Content Crew CLI[/bold cyan] v0.1.0")
    console.print("Part of Crew Media Ops")


if __name__ == "__main__":
    app()
