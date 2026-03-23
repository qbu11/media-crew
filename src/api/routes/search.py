"""Platform search API routes - Search and competitor monitoring."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    """Search request."""
    keyword: str
    limit: int = 20
    sort: str = "hot"  # hot, latest, relevant


class MultiPlatformSearchRequest(BaseModel):
    """Multi-platform search request."""
    keyword: str
    platforms: list[str] = []  # Empty means all platforms
    limit: int = 20


class CompetitorConfig(BaseModel):
    """Competitor configuration."""
    competitors: dict[str, str]  # {platform: user_id}


@router.get("/status")
async def get_search_status() -> dict[str, Any]:
    """Check availability of search tools for each platform."""
    from src.tools.search import PLATFORM_SEARCHERS

    status = {}
    for platform, searcher_class in PLATFORM_SEARCHERS.items():
        try:
            searcher_class()
            status[platform] = {
                "available": True,
                "search": True,
                "user_posts": True,
                "trending": True,
            }
        except Exception:
            status[platform] = {
                "available": False,
                "search": False,
                "user_posts": False,
                "trending": False,
            }

    return {"platforms": status}


@router.post("/{platform}")
async def search_platform(platform: str, request: SearchRequest) -> dict[str, Any]:
    """Search a specific platform."""
    from src.tools.search import get_platform_searcher

    try:
        searcher = get_platform_searcher(platform)
        result = searcher.search(request.keyword, limit=request.limit, sort=request.sort)

        return {
            "success": True,
            "platform": platform,
            "keyword": request.keyword,
            "total": result.total,
            "posts": [
                {
                    "post_id": p.post_id,
                    "title": p.title,
                    "content": p.content[:300],  # Truncate
                    "author": p.author,
                    "author_id": p.author_id,
                    "publish_time": p.publish_time,
                    "url": p.url,
                    "likes": p.likes,
                    "comments": p.comments,
                    "shares": p.shares,
                    "views": p.views,
                }
                for p in result.posts
            ],
            "searched_at": result.searched_at.isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/multi")
async def search_multi_platform(request: MultiPlatformSearchRequest) -> dict[str, Any]:
    """Search across multiple platforms."""
    from src.tools.search import PLATFORM_SEARCHERS

    platforms = request.platforms if request.platforms else list(PLATFORM_SEARCHERS.keys())
    results = {}

    for platform in platforms:
        try:
            searcher = PLATFORM_SEARCHERS[platform]()
            result = searcher.search(request.keyword, limit=request.limit)
            results[platform] = {
                "total": result.total,
                "top_posts": [
                    {
                        "title": p.title,
                        "url": p.url,
                        "likes": p.likes,
                        "comments": p.comments,
                    }
                    for p in result.posts[:5]
                ]
            }
        except Exception:
            results[platform] = {"total": 0, "top_posts": []}

    return {
        "success": True,
        "keyword": request.keyword,
        "results": results,
    }


@router.get("/{platform}/trending")
async def get_trending(
    platform: str,
    category: str = Query(default=""),
    limit: int = Query(default=20),
) -> dict[str, Any]:
    """Get trending topics/posts for a platform."""
    from src.tools.search import get_platform_searcher

    try:
        searcher = get_platform_searcher(platform)
        trending = searcher.get_trending(category=category, limit=limit)

        return {
            "success": True,
            "platform": platform,
            "category": category,
            "trending": trending[:limit],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{platform}/user/{user_id}")
async def get_user_posts(
    platform: str,
    user_id: str,
    limit: int = Query(default=20),
) -> dict[str, Any]:
    """Get posts from a specific user (for competitor monitoring)."""
    from src.tools.search import get_platform_searcher

    try:
        searcher = get_platform_searcher(platform)
        result = searcher.get_user_posts(user_id, limit=limit)

        return {
            "success": True,
            "platform": platform,
            "user_id": user_id,
            "total": result.total,
            "posts": [
                {
                    "post_id": p.post_id,
                    "title": p.title,
                    "url": p.url,
                    "likes": p.likes,
                    "comments": p.comments,
                    "publish_time": p.publish_time,
                }
                for p in result.posts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/competitors")
async def get_competitor_posts(config: CompetitorConfig) -> dict[str, Any]:
    """Get latest posts from configured competitors."""
    from src.tools.search import CompetitorMonitor

    monitor = CompetitorMonitor(competitors=config.competitors)
    results = monitor.get_competitor_posts(limit=20)

    return {
        "success": True,
        "competitors": {
            platform: {
                "user_id": results[platform].keyword,
                "total": results[platform].total,
                "latest_posts": [
                    {
                        "title": p.title,
                        "url": p.url,
                        "likes": p.likes,
                        "publish_time": p.publish_time,
                    }
                    for p in results[platform].posts[:5]
                ]
            }
            for platform in results
        },
    }
