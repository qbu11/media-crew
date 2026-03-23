"""Content management routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.tools.platform import PLATFORM_REGISTRY, list_platforms

router = APIRouter(prefix="/content", tags=["Content"])


class ContentBrief(BaseModel):
    """Content brief for generation."""

    topic: str
    keywords: list[str] = []
    target_platforms: list[str] = []
    tone: str = "professional"
    language: str = "zh-CN"


class ContentDraft(BaseModel):
    """Generated content draft."""

    id: str
    title: str
    body: str
    platform: str
    status: str = "draft"
    created_at: datetime
    word_count: int


class PublishRequest(BaseModel):
    """Publish content request."""

    content_id: str
    platforms: list[str]
    schedule_time: datetime | None = None


# In-memory storage for demo (replace with database in production)
_content_store: dict[str, ContentDraft] = {}


@router.get("/platforms")
async def get_platforms() -> dict[str, Any]:
    """Get all supported platforms."""
    domestic = list_platforms(domestic=True, overseas=False)
    overseas = list_platforms(domestic=False, overseas=True)

    return {
        "domestic": [
            {"id": p, "name": _get_platform_name(p), "status": "available"}
            for p in domestic
        ],
        "overseas": [
            {"id": p, "name": _get_platform_name(p), "status": "available"}
            for p in overseas
        ],
    }


def _get_platform_name(platform_id: str) -> str:
    """Get display name for platform."""
    names = {
        "xiaohongshu": "小红书",
        "wechat": "微信公众号",
        "weibo": "微博",
        "zhihu": "知乎",
        "douyin": "抖音",
        "bilibili": "B站",
        "reddit": "Reddit",
        "twitter": "X (Twitter)",
        "instagram": "Instagram",
        "facebook": "Facebook",
        "threads": "Threads",
    }
    return names.get(platform_id, platform_id)


@router.post("/generate")
async def generate_content(brief: ContentBrief) -> dict[str, Any]:
    """Generate content for specified platforms."""
    drafts = []
    for platform in brief.target_platforms:
        if platform not in PLATFORM_REGISTRY:
            continue

        tool_class = PLATFORM_REGISTRY[platform]
        tool_class()

        # Generate mock content (replace with actual AI generation)
        content_id = f"{platform}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        draft = ContentDraft(
            id=content_id,
            title=f"关于{brief.topic}的分享",
            body=f"这是一篇关于{brief.topic}的内容，关键词：{', '.join(brief.keywords)}",
            platform=platform,
            status="draft",
            created_at=datetime.now(),
            word_count=100,
        )
        _content_store[content_id] = draft
        drafts.append(draft)

    return {
        "success": True,
        "drafts": [
            {
                "id": d.id,
                "title": d.title,
                "body": d.body,
                "platform": d.platform,
                "platform_name": _get_platform_name(d.platform),
                "status": d.status,
                "created_at": d.created_at.isoformat(),
                "word_count": d.word_count,
            }
            for d in drafts
        ],
    }


@router.get("/drafts")
async def list_drafts() -> dict[str, Any]:
    """List all content drafts."""
    return {
        "drafts": [
            {
                "id": d.id,
                "title": d.title,
                "body": d.body,
                "platform": d.platform,
                "platform_name": _get_platform_name(d.platform),
                "status": d.status,
                "created_at": d.created_at.isoformat(),
                "word_count": d.word_count,
            }
            for d in _content_store.values()
        ]
    }


@router.post("/publish")
async def publish_content(request: PublishRequest) -> dict[str, Any]:
    """Publish content to platforms."""
    if request.content_id not in _content_store:
        raise HTTPException(status_code=404, detail="Content not found")

    draft = _content_store[request.content_id]
    results = []

    for platform in request.platforms:
        if platform not in PLATFORM_REGISTRY:
            results.append(
                {"platform": platform, "success": False, "error": "Unsupported platform"}
            )
            continue

        # Mock publish (replace with actual publishing)
        results.append(
            {
                "platform": platform,
                "platform_name": _get_platform_name(platform),
                "success": True,
                "post_id": f"{platform}-{datetime.now().strftime('%H%M%S')}",
                "published_at": datetime.now().isoformat(),
            }
        )

    # Update status
    draft.status = "published"

    return {"success": True, "results": results}


@router.delete("/drafts/{content_id}")
async def delete_draft(content_id: str) -> dict[str, Any]:
    """Delete a content draft."""
    if content_id not in _content_store:
        raise HTTPException(status_code=404, detail="Content not found")

    del _content_store[content_id]
    return {"success": True, "message": "Draft deleted"}
