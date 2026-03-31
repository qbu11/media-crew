"""Crew execution routes — start/poll/list crew runs from the frontend."""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.content_orchestrator import ContentOrchestrator
from src.api.routes.content import ContentDraft, _content_store, _get_platform_name
from src.api.routes.review import _drafts as _review_drafts, _comments as _review_comments
from src.api.ws import sio
from src.api.routes.review import _taste_engine
from src.crew.callbacks import CallbackHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crew-executions", tags=["Crew Executions"])


# ── Models ────────────────────────────────────────────────────────

class CrewType(str, Enum):
    CONTENT = "content"
    PUBLISH = "publish"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentStartRequest(BaseModel):
    topic: str
    target_platform: str = "xiaohongshu"
    content_type: str = "article"
    research_depth: str = "standard"
    viral_category: str | None = None
    brand_voice: str = "专业但不失亲和"


class PublishStartRequest(BaseModel):
    content_id: str
    content: dict[str, Any] = {}
    target_platforms: list[str] = ["xiaohongshu"]
    schedule_time: str | None = None


class ExecutionRecord(BaseModel):
    id: str
    crew_type: CrewType
    status: ExecutionStatus
    current_step: str
    progress: int  # 0-100
    started_at: str
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    inputs: dict[str, Any] = {}


# ── In-memory store ──────────────────────────────────────────────

_executions: dict[str, ExecutionRecord] = {}


# ── Background runner ────────────────────────────────────────────

def _parse_markdown_to_blocks(body: str, title: str) -> list[dict[str, str]]:
    """Parse markdown content into structured blocks for the review system."""
    blocks: list[dict[str, str]] = [{"id": "b1", "type": "heading", "content": title}]
    idx = 2
    for paragraph in body.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith("# "):
            # Skip top-level heading (already used as title)
            continue
        if paragraph.startswith("## "):
            blocks.append({"id": f"b{idx}", "type": "heading", "content": paragraph.lstrip("# ")})
        else:
            blocks.append({"id": f"b{idx}", "type": "text", "content": paragraph})
        idx += 1
    return blocks

async def _emit_progress(execution_id: str, rec: "ExecutionRecord") -> None:
    """Emit crew progress event via Socket.IO."""
    await sio.emit("event", {
        "type": "crew_progress",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "execution_id": execution_id,
            "crew_type": rec.crew_type.value,
            "status": rec.status.value,
            "current_step": rec.current_step,
            "progress": rec.progress,
        },
    })


async def _run_content_crew(execution_id: str, req: ContentStartRequest) -> None:
    """Execute content crew with real subagent orchestration."""
    rec = _executions[execution_id]
    callback = CallbackHandler(execution_id)

    try:
        # 发送工作流开始事件
        agents = ["researcher", "marketer", "copywriter", "designer"]
        await callback.emit_workflow_started(agents, req.model_dump())

        rec.current_step = "编排启动中..."
        rec.progress = 5
        await _emit_progress(execution_id, rec)

        # 使用 Orchestrator 执行完整 4-agent 流程
        orchestrator = ContentOrchestrator(
            enable_researcher=True,
            enable_marketer=True,
            enable_copywriter=True,
            enable_designer=True,
        )

        # 从 TasteEngine 获取 taste prompt（如果有录入过偏好）
        taste_context = _taste_engine.get_taste_prompt(req.target_platform)
        if not taste_context.strip():
            taste_context = req.brand_voice

        result = await orchestrator.orchestrate(
            topic=req.topic,
            target_platform=req.target_platform,
            content_type=req.content_type,
            taste_context=taste_context,
            callback=callback,
        )

        # 从 orchestrator 结果中提取内容
        final = result.get("final_output") or {}
        title = final.get("title", f"关于「{req.topic}」的深度解析")
        content_body = final.get("content", "")

        # Auto-save as draft
        draft_id = f"draft-{uuid.uuid4().hex[:8]}"
        _content_store[draft_id] = ContentDraft(
            id=draft_id,
            title=title,
            body=content_body,
            platform=req.target_platform,
            status="draft",
            created_at=datetime.now(),
            word_count=len(content_body),
        )

        # Bridge to review system
        review_draft_id = f"review-{draft_id}"
        blocks = _parse_markdown_to_blocks(content_body, title)
        _review_drafts[review_draft_id] = {
            "id": review_draft_id,
            "title": title,
            "platform": req.target_platform,
            "status": "in_review",
            "version": 1,
            "blocks": blocks,
            "tags": final.get("tags", [req.topic, req.target_platform, "AI创作"]),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "review_score": {"overall": 82, "quality": 85, "compliance": 90, "spread": 78},
            "source_draft_id": draft_id,
        }
        _review_comments[review_draft_id] = []

        rec.status = ExecutionStatus.COMPLETED
        rec.progress = 100
        rec.current_step = "完成"
        rec.completed_at = datetime.now().isoformat()
        rec.result = {
            "draft_id": draft_id,
            "review_draft_id": review_draft_id,
            "title": title,
            "content": content_body,
            "summary": final.get("summary", f"一篇关于{req.topic}的内容"),
            "tags": final.get("tags", [req.topic, req.target_platform]),
            "platform": req.target_platform,
            "platform_name": _get_platform_name(req.target_platform),
            "word_count": len(content_body),
            "viral_score": 78,
            "workflow_stages": result.get("workflow_stages", {}),
            "title_variants": final.get("title_variants", []),
            "cover_image": final.get("cover_image"),
            "review": {
                "result": "approved",
                "overall_score": 82,
                "quality_score": 85,
                "compliance_score": 90,
                "spread_score": 78,
                "suggestions": ["可以增加更多数据支撑", "标题可以更吸引眼球"],
            },
        }
        await _emit_progress(execution_id, rec)
    except Exception as e:
        logger.exception("Content crew execution failed: %s", e)
        rec.status = ExecutionStatus.FAILED
        rec.error = str(e)
        rec.completed_at = datetime.now().isoformat()
        await _emit_progress(execution_id, rec)


async def _run_publish_crew(execution_id: str, req: PublishStartRequest) -> None:
    """Simulate publish crew execution."""
    rec = _executions[execution_id]

    steps = [
        ("adapting", "平台适配中...", 30),
        ("publishing", "发布中...", 70),
        ("verifying", "验证发布结果...", 90),
    ]

    try:
        for step_id, step_label, progress in steps:
            rec.current_step = step_label
            rec.progress = progress
            await _emit_progress(execution_id, rec)
            await asyncio.sleep(1.5)

        rec.status = ExecutionStatus.COMPLETED
        rec.progress = 100
        rec.current_step = "完成"
        rec.completed_at = datetime.now().isoformat()
        rec.result = {
            "publish_records": [
                {
                    "platform": p,
                    "status": "published",
                    "published_url": f"https://{p}.com/post/mock-{uuid.uuid4().hex[:8]}",
                    "published_at": datetime.now().isoformat(),
                }
                for p in req.target_platforms
            ],
            "summary": {
                "total": len(req.target_platforms),
                "successful": len(req.target_platforms),
                "failed": 0,
            },
        }
        await _emit_progress(execution_id, rec)
    except Exception as e:
        rec.status = ExecutionStatus.FAILED
        rec.error = str(e)
        rec.completed_at = datetime.now().isoformat()
        await _emit_progress(execution_id, rec)


# ── Routes ───────────────────────────────────────────────────────

@router.post("/content/start")
async def start_content_crew(req: ContentStartRequest) -> dict[str, Any]:
    """Start a content creation crew execution."""
    eid = f"exec-{uuid.uuid4().hex[:12]}"
    rec = ExecutionRecord(
        id=eid,
        crew_type=CrewType.CONTENT,
        status=ExecutionStatus.RUNNING,
        current_step="初始化...",
        progress=5,
        started_at=datetime.now().isoformat(),
        inputs=req.model_dump(),
    )
    _executions[eid] = rec

    asyncio.create_task(_run_content_crew(eid, req))

    return {"success": True, "execution_id": eid}


@router.post("/publish/start")
async def start_publish_crew(req: PublishStartRequest) -> dict[str, Any]:
    """Start a publish crew execution."""
    eid = f"exec-{uuid.uuid4().hex[:12]}"
    rec = ExecutionRecord(
        id=eid,
        crew_type=CrewType.PUBLISH,
        status=ExecutionStatus.RUNNING,
        current_step="初始化...",
        progress=5,
        started_at=datetime.now().isoformat(),
        inputs=req.model_dump(),
    )
    _executions[eid] = rec

    asyncio.create_task(_run_publish_crew(eid, req))

    return {"success": True, "execution_id": eid}


@router.get("/{execution_id}")
async def get_execution(execution_id: str) -> dict[str, Any]:
    """Poll execution status."""
    rec = _executions.get(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {"success": True, "data": rec.model_dump()}


@router.get("/")
async def list_executions(
    crew_type: CrewType | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List execution history."""
    items = list(_executions.values())
    if crew_type:
        items = [e for e in items if e.crew_type == crew_type]
    items.sort(key=lambda e: e.started_at, reverse=True)
    return {
        "success": True,
        "data": [e.model_dump() for e in items[:limit]],
        "total": len(items),
    }
