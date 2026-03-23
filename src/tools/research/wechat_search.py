"""
WeChat Search Tool - Search WeChat articles by keyword

Based on: https://github.com/qbu11/wechat-search-skill
Uses Sougou WeChat search + DrissionPage for Chrome automation.
No WeChat login required.
"""

from datetime import datetime
import json
from pathlib import Path
import subprocess

from pydantic import BaseModel


class WeChatSearchResult(BaseModel):
    """Single search result."""

    title: str
    url: str
    author: str  # 公众号名称
    account_id: str  # 公众号 ID
    publish_time: str
    summary: str = ""
    content: str = ""


class WeChatSearchResponse(BaseModel):
    """Search response."""

    keyword: str
    total: int
    results: list[WeChatSearchResult]
    searched_at: datetime


class WeChatSearchTool:
    """
    WeChat article search tool using Sougou WeChat search.

    Prerequisites:
    - Install the wechat-search-skill:
      ```bash
      git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search
      pip install -r ~/.claude/skills/wechat-search/scripts/requirements.txt
      ```
    """

    name = "wechat_search"
    description = "Search WeChat articles by keyword via Sougou WeChat search"

    def __init__(self, skill_path: str | None = None):
        """Initialize the tool."""
        self.skill_path = skill_path or self._find_skill_path()
        self.script_path = self.skill_path / "scripts" / "keyword_search.py" if self.skill_path else None

    def _find_skill_path(self) -> Path | None:
        """Find the wechat-search-skill installation path."""
        possible_paths = [
            Path.home() / ".claude" / "skills" / "wechat-search",
            Path.home() / ".openclaw" / "skills" / "wechat-search",
            Path("C:/Users") / Path.home().name / ".claude" / "skills" / "wechat-search",
        ]
        for p in possible_paths:
            if p.exists():
                return p
        return None

    def is_available(self) -> bool:
        """Check if the skill is installed."""
        return self.script_path is not None and self.script_path.exists()

    def search(
        self,
        keyword: str,
        pages: int = 3,
        days: int | None = None,
        with_content: bool = False,
        output_format: str = "csv",
    ) -> WeChatSearchResponse:
        """
        Search WeChat articles by keyword.

        Args:
            keyword: Search keyword
            pages: Number of pages to search (default 3, ~10 articles per page)
            days: Only include articles from last N days (optional)
            with_content: Fetch full article content (slower)
            output_format: Output format (csv or md, not json)

        Returns:
            WeChatSearchResponse with search results
        """
        if not self.is_available():
            raise RuntimeError(
                "wechat-search-skill not installed. "
                "Run: git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search && "
                "pip install -r ~/.claude/skills/wechat-search/scripts/requirements.txt"
            )

        # Validate format (only csv and md supported)
        if output_format not in ("csv", "md"):
            output_format = "csv"

        # Build command
        cmd = [
            "python",
            str(self.script_path),
            keyword,
            "--pages", str(pages),
            "--format", output_format,
        ]

        if days:
            cmd.extend(["--days", str(days)])

        if not with_content:
            cmd.append("--no-content")

        # Run search
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=None,  # Don't change directory, use absolute paths
        )

        if result.returncode != 0:
            raise RuntimeError(f"Search failed: {result.stderr}")

        # Parse output - find the output file path from stdout
        output_file = None
        for line in result.stdout.strip().split("\n"):
            if line.endswith((".csv", ".md")):
                output_file = line
                break

        # Try to read the output file
        if output_file and Path(output_file).exists():
            return self._parse_output_file(output_file, keyword)

        # Fallback: parse stdout
        return self._parse_stdout(result.stdout, keyword)

    def _parse_output_file(self, file_path: str, keyword: str) -> WeChatSearchResponse:
        """Parse the output file from the search."""
        path = Path(file_path)

        if file_path.endswith(".json"):
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            results = [
                WeChatSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    author=item.get("author", item.get("account", "")),
                    account_id=item.get("account_id", ""),
                    publish_time=item.get("publish_time", item.get("time", "")),
                    summary=item.get("summary", ""),
                    content=item.get("content", ""),
                )
                for item in data
            ]
        elif file_path.endswith(".csv"):
            import csv
            results = []
            with path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(WeChatSearchResult(
                        title=row.get("title", ""),
                        url=row.get("url", ""),
                        author=row.get("author", row.get("account", "")),
                        account_id=row.get("account_id", ""),
                        publish_time=row.get("publish_time", row.get("time", "")),
                        summary=row.get("summary", ""),
                        content=row.get("content", ""),
                    ))
        else:
            results = []

        return WeChatSearchResponse(
            keyword=keyword,
            total=len(results),
            results=results,
            searched_at=datetime.now(),
        )

    def _parse_stdout(self, stdout: str, keyword: str) -> WeChatSearchResponse:
        """Parse stdout output."""
        # Simple fallback - return empty results
        return WeChatSearchResponse(
            keyword=keyword,
            total=0,
            results=[],
            searched_at=datetime.now(),
        )


# Convenience function
def search_wechat_articles(
    keyword: str,
    pages: int = 3,
    days: int | None = None,
    with_content: bool = False,
) -> WeChatSearchResponse:
    """Search WeChat articles by keyword."""
    tool = WeChatSearchTool()
    return tool.search(keyword, pages=pages, days=days, with_content=with_content)
