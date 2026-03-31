"""Analytics routes — operations + content analytics."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_executions() -> list:
    """Lazy import to avoid circular dependency."""
    from src.api.routes.crew_execution import _executions
    return list(_executions.values())


@router.get("/operations")
async def get_operations_stats() -> dict[str, Any]:
    """Get operational analytics from crew executions."""
    execs = _get_executions()
    total = len(execs)
    completed = sum(1 for e in execs if e.status.value == "completed")
    failed = sum(1 for e in execs if e.status.value == "failed")
    running = sum(1 for e in execs if e.status.value == "running")

    content_execs = [e for e in execs if e.crew_type.value == "content"]
    publish_execs = [e for e in execs if e.crew_type.value == "publish"]

    return {
        "total_executions": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "success_rate": round(completed / total, 2) if total > 0 else 0,
        "by_type": {
            "content": len(content_execs),
            "publish": len(publish_execs),
        },
    }


@router.get("/operations/timeline")
async def get_operations_timeline() -> dict[str, Any]:
    """Get execution timeline for the last 7 days."""
    execs = _get_executions()
    now = datetime.now()
    days = 7
    timeline = []

    for i in range(days):
        date = now - timedelta(days=days - 1 - i)
        date_str = date.strftime("%Y-%m-%d")
        day_execs = [
            e for e in execs
            if e.started_at.startswith(date_str)
        ]
        timeline.append({
            "date": date_str,
            "total": len(day_execs),
            "completed": sum(1 for e in day_execs if e.status.value == "completed"),
            "failed": sum(1 for e in day_execs if e.status.value == "failed"),
        })

    return {"timeline": timeline}


@router.get("/overview")
async def get_overview() -> dict[str, Any]:
    """Get content analytics overview."""
    return {
        "total_posts": 156,
        "total_views": 245680,
        "total_engagement": 12450,
        "followers_gained": 328,
        "period": "last_30_days",
    }


@router.get("/platforms")
async def get_platform_stats() -> dict[str, Any]:
    """Get stats by platform (deterministic)."""
    return {
        "platforms": [
            {"platform": "xiaohongshu", "name": "小红书", "posts": 42, "views": 85200, "likes": 4200, "comments": 380, "shares": 120},
            {"platform": "weibo", "name": "微博", "posts": 38, "views": 62400, "likes": 3100, "comments": 290, "shares": 85},
            {"platform": "zhihu", "name": "知乎", "posts": 28, "views": 45600, "likes": 2800, "comments": 420, "shares": 65},
            {"platform": "douyin", "name": "抖音", "posts": 25, "views": 128000, "likes": 8500, "comments": 620, "shares": 340},
            {"platform": "bilibili", "name": "B站", "posts": 23, "views": 34800, "likes": 1900, "comments": 280, "shares": 45},
        ]
    }


@router.get("/trending")
async def get_trending_topics() -> dict[str, Any]:
    """Get trending topics."""
    return {
        "topics": [
            {"rank": 1, "topic": "AI 编程工具", "heat": 98, "trend": "up"},
            {"rank": 2, "topic": "Claude Code", "heat": 95, "trend": "up"},
            {"rank": 3, "topic": "创业者故事", "heat": 87, "trend": "stable"},
            {"rank": 4, "topic": "产品思维", "heat": 82, "trend": "up"},
            {"rank": 5, "topic": "技术面试", "heat": 78, "trend": "down"},
        ]
    }


@router.get("/posts/{post_id}/performance")
async def get_post_performance(post_id: str) -> dict[str, Any]:
    """Get performance metrics for a specific post."""
    days = 7
    daily_stats = []
    base_date = datetime.now() - timedelta(days=days)
    # Deterministic seed based on post_id
    seed = sum(ord(c) for c in post_id)

    for i in range(days):
        date = base_date + timedelta(days=i)
        v = (seed * (i + 1) * 37) % 900 + 100
        daily_stats.append({
            "date": date.strftime("%Y-%m-%d"),
            "views": v,
            "likes": v // 10,
            "comments": v // 50,
            "shares": v // 100,
        })

    return {
        "post_id": post_id,
        "total_views": sum(d["views"] for d in daily_stats),
        "total_likes": sum(d["likes"] for d in daily_stats),
        "total_comments": sum(d["comments"] for d in daily_stats),
        "total_shares": sum(d["shares"] for d in daily_stats),
        "daily_stats": daily_stats,
    }
