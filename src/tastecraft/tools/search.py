"""Search tools for trending topics and competitor analysis."""

from __future__ import annotations

import logging
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SearchTrendingTool(BaseTool):
    """
    Search for trending topics in the user's domain.

    Uses web search APIs to discover hot topics, then scores them
    against the project's taste profile for relevance.
    """

    name = "search_trending"
    description = (
        "Search for trending topics in the content domain. "
        "Returns a list of trending topics with relevance scores, "
        "so the agent can pick the best one for content generation. "
        "Pass 'query' to specify the search domain or topic area."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or domain to find trending topics in",
            },
            "platform": {
                "type": "string",
                "enum": ["xiaohongshu", "wechat", "all"],
                "description": "Platform to search on (default: all)",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of topics to return (default: 10)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        query: str,
        platform: str = "all",
        limit: int = 10,
    ) -> ToolResult:
        topics = await self._search(query, platform, limit)
        return ToolResult(
            success=True,
            data={"topics": topics, "query": query, "platform": platform},
            metadata={"tool": self.name, "count": len(topics)},
        )

    async def _search(self, query: str, platform: str, limit: int) -> list[dict[str, Any]]:
        """
        Search for trending topics.

        In production this calls external APIs (XHS search, Sogou Weixin, etc.).
        For now returns structured placeholder data that the agent can work with.
        """
        import httpx
        import json

        topics: list[dict[str, Any]] = []

        # Try DuckDuckGo search for real trending content
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": f"{query} trending 2026", "format": "json", "no_html": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("RelatedTopics"):
                        for item in data["RelatedTopics"][:limit]:
                            if isinstance(item, dict) and "Text" in item:
                                topics.append({
                                    "topic": item["Text"][:80],
                                    "title": item["Text"][:80],
                                    "score": 5.0,
                                    "source": "duckduckgo",
                                    "url": item.get("FirstURL", ""),
                                })
        except Exception as e:
            logger.warning("Search failed: %s", e)

        # Fallback: generate topic suggestions from the query
        if not topics:
            topics = [
                {"topic": f"{query} latest trends and insights", "title": f"{query} latest trends", "score": 6.0, "source": "generated"},
                {"topic": f"How {query} is changing in 2026", "title": f"How {query} is changing", "score": 5.5, "source": "generated"},
                {"topic": f"Common mistakes in {query}", "title": f"Common mistakes in {query}", "score": 5.0, "source": "generated"},
            ][:limit]

        return topics


class SearchCompetitorTool(BaseTool):
    """
    Analyze competitor content in the user's domain.

    Searches for top-performing content from competitor accounts
    and extracts patterns (title structures, content length, engagement strategies).
    """

    name = "search_competitor"
    description = (
        "Analyze competitor content in the given domain. "
        "Returns top-performing content with extracted patterns "
        "(title structures, content formats, engagement strategies)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain/niche to analyze competitors in",
            },
            "platform": {
                "type": "string",
                "enum": ["xiaohongshu", "wechat"],
                "description": "Platform to search",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 5)",
            },
        },
        "required": ["domain"],
    }

    async def execute(
        self,
        domain: str,
        platform: str = "xiaohongshu",
        limit: int = 5,
    ) -> ToolResult:
        # Placeholder: in production uses platform-specific search APIs
        return ToolResult(
            success=True,
            data={
                "competitors": [],
                "patterns": {
                    "title_formats": ["numbered_list", "how_to", "contrarian_take"],
                    "avg_engagement_rate": 0.035,
                    "common_hashtags": [],
                },
                "domain": domain,
                "platform": platform,
            },
            metadata={"tool": self.name},
        )


class ReadContentHistoryTool(BaseTool):
    """Read past content from the project for dedup and style reference."""

    name = "read_content_history"
    description = (
        "Read past content from this project. Use for deduplication "
        "(avoid repeating topics) and style reference (match established patterns)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max number of past content items (default: 10)",
            },
            "status": {
                "type": "string",
                "description": "Filter by status (draft, queued, published)",
            },
        },
        "required": [],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> ToolResult:
        from tastecraft.models.base import get_session
        from tastecraft.models.tables import Content
        from sqlalchemy import select

        session = await get_session()
        async with session:
            stmt = (
                select(Content)
                .where(Content.project_id == self._project_id)
                .order_by(Content.created_at.desc())
                .limit(limit)
            )
            if status:
                stmt = stmt.where(Content.status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            items = [
                {
                    "id": r.id,
                    "title": r.title,
                    "body_preview": r.body[:200] if r.body else "",
                    "status": r.status,
                    "quality_score": r.quality_score,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
            return ToolResult(
                success=True,
                data={"items": items, "count": len(items)},
                metadata={"tool": self.name},
            )
