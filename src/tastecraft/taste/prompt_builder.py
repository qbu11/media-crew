"""Build system prompts from taste profiles."""

from __future__ import annotations

from tastecraft.taste.profile import TasteProfile


def build_taste_prompt(profile: TasteProfile) -> str:
    """Compile a taste profile into a system prompt section."""
    sections: list[str] = []

    # Identity
    sections.append("## Your Content Identity\n")
    if profile.identity:
        sections.append(f"You are writing as: {profile.identity}")
    if profile.tone:
        sections.append(f"Your tone: {profile.tone}")
    if profile.audience:
        sections.append(f"Your audience: {profile.audience}")

    # Style rules
    sections.append("\n## Style Rules (MUST follow)\n")
    if profile.taboos.get("words"):
        sections.append(f"Taboo words (NEVER use): {', '.join(profile.taboos['words'])}")
    if profile.taboos.get("topics"):
        sections.append(f"Taboo topics (NEVER write about): {', '.join(profile.taboos['topics'])}")
    if profile.taboos.get("style"):
        sections.append(f"Style taboos: {', '.join(profile.taboos['style'])}")
    if profile.catchphrases:
        sections.append(
            f"Catchphrases to use naturally: {', '.join(profile.catchphrases)}"
        )
    if profile.content_goal:
        sections.append(f"Content goal: {profile.content_goal}")

    # Learned patterns
    if profile.learned:
        sections.append("\n## Learned Patterns (follow when applicable)\n")
        skip_keys = {"_confidence", "_generation_count"}
        for key, value in profile.learned.items():
            if key not in skip_keys and value:
                label = key.replace("_", " ").title()
                sections.append(f"{label}: {value}")

    return "\n".join(sections)


def build_pipeline_prompt(
    profile: TasteProfile,
    pipeline_name: str,
    extra_context: str = "",
) -> str:
    """Build a full system prompt for a pipeline run."""
    base_role = (
        f"You are TasteCraft, an AI content engine. "
        f"You are running the {pipeline_name} pipeline for project '{profile.project}'."
    )

    taste_section = build_taste_prompt(profile)

    parts = [base_role, "", taste_section]

    if extra_context:
        parts.extend(["", "## Additional Context", "", extra_context])

    parts.extend([
        "",
        "## Instructions",
        "",
        "Use the available tools to complete your task. "
        "Be concise and direct. Follow the style rules strictly. "
        "If you are unsure about something, use a tool to look it up rather than guessing.",
    ])

    return "\n".join(parts)
