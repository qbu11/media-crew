"""Analytics routes."""

from datetime import datetime, timedelta
import random
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview() -> dict[str, Any]:
    """Get analytics overview."""
    # Mock data (replace with actual analytics)
    return {
        "total_posts": 156,
        "total_views": 245680,
        "total_engagement": 12450,
        "followers_gained": 328,
        "period": "last_30_days",
    }


@router.get("/platforms")
async def get_platform_stats() -> dict[str, Any]:
    """Get stats by platform."""
    platforms = ["xiaohongshu", "weibo", "zhihu", "douyin", "bilibili"]
    stats = []

    for p in platforms:
        stats.append(
            {
                "platform": p,
                "posts": random.randint(10, 50),
                "views": random.randint(10000, 100000),
                "likes": random.randint(500, 5000),
                "comments": random.randint(50, 500),
                "shares": random.randint(10, 200),
            }
        )

    return {"platforms": stats}


@router.get("/trending")
async def get_trending_topics() -> dict[str, Any]:
    """Get trending topics."""
    # Mock trending topics
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
    # Mock post performance
    days = 7
    daily_stats = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_date + timedelta(days=i)
        daily_stats.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "views": random.randint(100, 1000),
                "likes": random.randint(10, 100),
                "comments": random.randint(1, 20),
                "shares": random.randint(0, 10),
            }
        )

    return {
        "post_id": post_id,
        "total_views": sum(d["views"] for d in daily_stats),
        "total_likes": sum(d["likes"] for d in daily_stats),
        "total_comments": sum(d["comments"] for d in daily_stats),
        "total_shares": sum(d["shares"] for d in daily_stats),
        "daily_stats": daily_stats,
    }
