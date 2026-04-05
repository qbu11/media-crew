"""Taste profile management — load, save, merge YAML profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TasteProfile:
    """Structured taste profile for a project."""

    # Explicit dimensions (user-configured)
    project: str = ""
    identity: str = ""
    tone: str = ""
    audience: str = ""
    benchmarks: list[str] = field(default_factory=list)
    taboos: dict[str, list[str]] = field(default_factory=lambda: {
        "words": [],
        "topics": [],
        "style": [],
    })
    catchphrases: list[str] = field(default_factory=list)
    content_goal: str = ""
    platforms: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Implicit dimensions (system-learned)
    learned: dict[str, Any] = field(default_factory=dict)

    # Metadata
    confidence: float = 0.0
    generation_count: int = 0

    @property
    def domain(self) -> str:
        """Derive a search domain from identity for trending search."""
        if self.identity:
            return self.identity.strip().split(",")[0].strip()
        return ""

    @classmethod
    def load(cls, project_dir: Path) -> TasteProfile:
        """Load taste profile from project directory."""
        taste_path = project_dir / "taste.yaml"
        learned_path = project_dir / "taste_learned.json"

        profile = cls()

        if taste_path.exists():
            with open(taste_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            profile.project = data.get("project", "")
            profile.identity = data.get("identity", "")
            profile.tone = data.get("tone", "")
            profile.audience = data.get("audience", "")
            profile.benchmarks = data.get("benchmarks", [])
            profile.content_goal = data.get("content_goal", "")
            profile.catchphrases = data.get("catchphrases", [])
            profile.platforms = data.get("platforms", {})

            # Taboos can be a list of strings or a dict
            raw_taboos = data.get("taboos", {})
            if isinstance(raw_taboos, dict):
                profile.taboos = {
                    "words": raw_taboos.get("words", []),
                    "topics": raw_taboos.get("topics", []),
                    "style": raw_taboos.get("style", []),
                }
            elif isinstance(raw_taboos, list):
                profile.taboos = {"words": raw_taboos, "topics": [], "style": []}

        if learned_path.exists():
            import json
            with open(learned_path, encoding="utf-8") as f:
                profile.learned = json.load(f)
            profile.confidence = profile.learned.get("_confidence", 0.0)
            profile.generation_count = profile.learned.get("_generation_count", 0)

        return profile

    def save_explicit(self, project_dir: Path) -> None:
        """Save explicit dimensions to taste.yaml."""
        data = {
            "project": self.project,
            "identity": self.identity,
            "tone": self.tone,
            "audience": self.audience,
            "benchmarks": self.benchmarks,
            "taboos": self.taboos,
            "catchphrases": self.catchphrases,
            "content_goal": self.content_goal,
            "platforms": self.platforms,
        }
        taste_path = project_dir / "taste.yaml"
        with open(taste_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def save_learned(self, project_dir: Path) -> None:
        """Save implicit dimensions to taste_learned.json."""
        import json
        learned = {**self.learned}
        learned["_confidence"] = self.confidence
        learned["_generation_count"] = self.generation_count
        learned_path = project_dir / "taste_learned.json"
        with open(learned_path, "w", encoding="utf-8") as f:
            json.dump(learned, f, ensure_ascii=False, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Full profile as dict."""
        return {
            "project": self.project,
            "identity": self.identity,
            "tone": self.tone,
            "audience": self.audience,
            "benchmarks": self.benchmarks,
            "taboos": self.taboos,
            "catchphrases": self.catchphrases,
            "content_goal": self.content_goal,
            "platforms": self.platforms,
            "learned": self.learned,
            "confidence": self.confidence,
            "generation_count": self.generation_count,
        }
