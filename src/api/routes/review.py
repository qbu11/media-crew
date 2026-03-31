"""Review feedback API routes - 内容审核反馈系统."""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.schemas.taste_profile import ExplicitPreferences, TasteProfile, TasteSignal
from src.services.taste_engine import TasteEngine

router = APIRouter(prefix="/reviews", tags=["Reviews"])
logger = logging.getLogger(__name__)


# --- Request/Response Models ---


class CommentAnchor(BaseModel):
    block_id: str
    start: int
    end: int
    quote: str


class CreateCommentRequest(BaseModel):
    anchor: CommentAnchor
    category: str = "suggestion"  # issue | suggestion | approval | question
    severity: str = "medium"  # low | medium | high | critical
    message: str
    suggested_rewrite: str | None = None


class UpdateCommentRequest(BaseModel):
    status: str | None = None  # open | accepted | rejected | resolved
    message: str | None = None


class RevisionRequest(BaseModel):
    accepted_comment_ids: list[str]
    mode: str = "targeted"  # targeted | full


class UpdateDraftStatusRequest(BaseModel):
    status: str  # draft | in_review | changes_requested | revising | approved | rejected


class PreferenceUpdate(BaseModel):
    tone_prefer: list[str] | None = None
    tone_avoid: list[str] | None = None
    prefer_opening: list[str] | None = None
    prefer_length: str | None = None
    emoji: str | None = None
    cta: str | None = None


class DraftFeedbackRequest(BaseModel):
    """结构化稿件反馈请求."""

    action: str  # approve | reject | comment
    reason: str = ""
    score_override: dict[str, float] | None = None


# --- In-memory storage ---

_comments: dict[str, list[dict[str, Any]]] = {}  # draft_id -> comments
_drafts: dict[str, dict[str, Any]] = {}  # draft_id -> reviewable draft
_revisions: dict[str, dict[str, Any]] = {}  # revision_id -> revision result
_taste_engine: TasteEngine = TasteEngine()  # 核心引擎（替代裸 _taste_profile）
_taste_profile: TasteProfile = _taste_engine.profile  # 向后兼容引用
_feedback_logs: list[dict[str, Any]] = []  # 反馈日志

# 兼容层：从 TasteProfile 生成旧格式 _preferences
def _get_preferences() -> dict[str, Any]:
    """从 TasteProfile 生成兼容旧格式的 preferences dict."""
    prefs = _taste_profile.explicit_preferences
    return {
        "tone": {"prefer": prefs.tone_prefer, "avoid": prefs.tone_avoid},
        "structure": {
            "prefer_opening": prefs.preferred_openings,
            "prefer_length": prefs.preferred_length,
        },
        "style": {"emoji": prefs.emoji_style, "cta": prefs.cta_style},
        "learned": {
            "total_feedback": _taste_profile.total_feedback_count,
            "approval_count": _taste_profile.approval_count,
            "rejection_count": _taste_profile.rejection_count,
            "approval_rate": _taste_profile.approval_rate,
            "phase": _taste_profile.phase,
            "last_updated": datetime.now().isoformat(),
        },
    }


def _record_taste_signal(
    source: str, dimension: str, signal_type: str, value: str, content_id: str | None = None
) -> None:
    """记录一条 taste 信号到 profile."""
    signal = TasteSignal(
        source=source,
        dimension=dimension,
        signal_type=signal_type,
        value=value,
        content_id=content_id,
    )
    _taste_profile.feedback_signals.append(signal)


def _seed_demo_draft() -> None:
    """Seed a demo draft for testing."""
    if _drafts:
        return
    draft_id = "draft_demo_001"
    _drafts[draft_id] = {
        "id": draft_id,
        "title": "AI 创业的 5 个关键建议",
        "platform": "xiaohongshu",
        "status": "in_review",
        "version": 1,
        "blocks": [
            {"id": "b1", "type": "heading", "content": "AI 创业的 5 个关键建议"},
            {
                "id": "b2",
                "type": "text",
                "content": (
                    "在当今快速发展的 AI 时代，创业者面临着前所未有的机遇和挑战。"
                    "作为一个深耕 AI 领域多年的从业者，我想分享一些最核心的创业建议。"
                ),
            },
            {
                "id": "b3",
                "type": "text",
                "content": (
                    "第一，找到真正的痛点。很多 AI 创业者犯的最大错误就是\u201c拿着锤子找钉子\u201d。"
                    "不要因为你有一个很酷的 AI 模型就去创业，而是要先找到用户真正的痛点，"
                    "然后看 AI 能不能更好地解决它。这是最强的创业方法论。"
                ),
            },
            {
                "id": "b4",
                "type": "text",
                "content": (
                    "第二，快速验证，小步迭代。不要花半年时间打磨一个\u201c完美\u201d的产品。"
                    "用最小可行产品（MVP）快速上线，收集用户反馈，然后不断迭代。"
                    "速度是 AI 创业最重要的竞争优势。"
                ),
            },
            {
                "id": "b5",
                "type": "text",
                "content": (
                    "第三，重视数据飞轮。AI 产品的核心壁垒不是算法，而是数据。"
                    "设计好你的数据飞轮：用户使用产品 → 产生数据 → 模型变得更好 → "
                    "吸引更多用户。这个循环一旦转起来，竞争对手很难追上。"
                ),
            },
            {
                "id": "b6",
                "type": "text",
                "content": (
                    "第四，组建互补团队。AI 创业需要技术和商业的双重能力。"
                    "一个纯技术团队很容易做出没人用的产品，一个纯商业团队又做不出有竞争力的技术。"
                    "找到能互补的合伙人至关重要。"
                ),
            },
            {
                "id": "b7",
                "type": "text",
                "content": (
                    "第五，保持对 AI 伦理的敬畏。AI 创业不仅仅是赚钱，更是在塑造未来。"
                    "确保你的产品不会造成偏见、歧视或隐私泄露。负责任的 AI 才能走得更远。"
                    "这是零风险的投资策略。"
                ),
            },
        ],
        "tags": ["AI创业", "创业建议", "人工智能"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "review_score": {"overall": 82, "quality": 85, "compliance": 78, "spread": 80},
    }
    _comments[draft_id] = []


_seed_demo_draft()


# --- Draft endpoints ---


@router.get("/drafts")
async def list_reviewable_drafts() -> dict[str, Any]:
    """List all reviewable drafts."""
    return {"success": True, "drafts": list(_drafts.values())}


@router.get("/drafts/{draft_id}")
async def get_reviewable_draft(draft_id: str) -> dict[str, Any]:
    """Get a single reviewable draft with its blocks."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "data": _drafts[draft_id]}


@router.patch("/drafts/{draft_id}/status")
async def update_draft_status(draft_id: str, req: UpdateDraftStatusRequest) -> dict[str, Any]:
    """Update draft review status."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")

    valid = [
        "draft",
        "in_review",
        "changes_requested",
        "revising",
        "approved",
        "rejected",
        "scheduled",
        "published",
    ]
    if req.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")

    _drafts[draft_id]["status"] = req.status
    _drafts[draft_id]["updated_at"] = datetime.now().isoformat()
    return {"success": True, "data": _drafts[draft_id]}


# --- Comment endpoints ---


@router.get("/drafts/{draft_id}/comments")
async def list_comments(draft_id: str) -> dict[str, Any]:
    """Get all comments for a draft."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "comments": _comments.get(draft_id, [])}


@router.post("/drafts/{draft_id}/comments")
async def create_comment(draft_id: str, req: CreateCommentRequest) -> dict[str, Any]:
    """Add a review comment to a draft."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")

    comment = {
        "id": f"cmt_{uuid.uuid4().hex[:8]}",
        "draft_id": draft_id,
        "anchor": req.anchor.model_dump(),
        "category": req.category,
        "severity": req.severity,
        "status": "open",
        "message": req.message,
        "suggested_rewrite": req.suggested_rewrite,
        "author": {"id": "user_001", "name": "审核员", "type": "human"},
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    if draft_id not in _comments:
        _comments[draft_id] = []
    _comments[draft_id].append(comment)

    return {"success": True, "comment": comment}


@router.patch("/comments/{comment_id}")
async def update_comment(comment_id: str, req: UpdateCommentRequest) -> dict[str, Any]:
    """Update a comment's status or message."""
    for draft_id, comments in _comments.items():
        for c in comments:
            if c["id"] == comment_id:
                if req.status:
                    old_status = c["status"]
                    c["status"] = req.status
                    if req.status == "resolved":
                        c["resolved_at"] = datetime.now().isoformat()
                    # Taste 学习：记录 accept/reject 为 taste signal
                    if req.status == "accepted" and old_status == "open":
                        _record_taste_signal(
                            source="feedback",
                            dimension=c["category"],
                            signal_type="like",
                            value=c["message"][:60],
                            content_id=c.get("draft_id"),
                        )
                        _taste_profile.total_feedback_count += 1
                    elif req.status == "rejected" and old_status == "open":
                        _record_taste_signal(
                            source="feedback",
                            dimension=c["category"],
                            signal_type="dislike",
                            value=c["message"][:60],
                            content_id=c.get("draft_id"),
                        )
                        _taste_profile.total_feedback_count += 1
                if req.message is not None:
                    c["message"] = req.message
                return {"success": True, "comment": c}

    raise HTTPException(status_code=404, detail="Comment not found")


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str) -> dict[str, Any]:
    """Delete a comment."""
    for draft_id, comments in _comments.items():
        for i, c in enumerate(comments):
            if c["id"] == comment_id:
                comments.pop(i)
                return {"success": True}

    raise HTTPException(status_code=404, detail="Comment not found")


# --- Revision endpoints ---


async def _generate_revision(
    draft: dict[str, Any], accepted: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate revision changes. Try LLM first, fallback to mock."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            return await _llm_revision(draft, accepted, api_key)
        except Exception as e:
            logger.warning("LLM revision failed, falling back to mock: %s", e)
    return _mock_revision(draft, accepted)


def _mock_revision(
    draft: dict[str, Any], accepted: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fallback mock revision when LLM is unavailable."""
    changes: list[dict[str, Any]] = []
    rationale: list[dict[str, Any]] = []
    for c in accepted:
        block_id = c["anchor"]["block_id"]
        block = next((b for b in draft["blocks"] if b["id"] == block_id), None)
        if not block:
            continue
        old_content = block["content"]
        if c.get("suggested_rewrite"):
            quote = c["anchor"]["quote"]
            new_content = old_content.replace(quote, c["suggested_rewrite"])
        else:
            new_content = old_content + f"\n[已根据反馈修改：{c['message'][:30]}]"
        changes.append({"block_id": block_id, "old_content": old_content, "new_content": new_content})
        rationale.append({"comment_id": c["id"], "resolution": f"已处理：{c['message'][:50]}"})
    return changes, rationale


async def _llm_revision(
    draft: dict[str, Any], accepted: list[dict[str, Any]], api_key: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use Anthropic LLM to generate targeted revisions."""
    import httpx

    # Build revision prompt with user preferences
    pref_summary = ""
    prefs = _taste_profile.explicit_preferences
    # 从 taste signals 提取最近的 accept/reject 摘要
    recent_likes = [
        s.value for s in _taste_profile.feedback_signals[-20:]
        if s.signal_type == "like"
    ][-5:]
    recent_dislikes = [
        s.value for s in _taste_profile.feedback_signals[-20:]
        if s.signal_type == "dislike"
    ][-5:]
    if recent_likes:
        pref_summary += f"\n用户倾向接受的反馈类型：{'; '.join(recent_likes)}"
    if recent_dislikes:
        pref_summary += f"\n用户倾向拒绝的反馈类型：{'; '.join(recent_dislikes)}"
    if prefs.tone_prefer:
        pref_summary += f"\n偏好风格：{', '.join(prefs.tone_prefer)}"
    if prefs.tone_avoid:
        pref_summary += f"\n避免风格：{', '.join(prefs.tone_avoid)}"

    # Build per-block revision instructions
    block_instructions = []
    for c in accepted:
        block = next((b for b in draft["blocks"] if b["id"] == c["anchor"]["block_id"]), None)
        if not block:
            continue
        block_instructions.append(
            f"- block_id: {block['id']}\n"
            f"  原文: {block['content'][:200]}\n"
            f"  引用: {c['anchor']['quote']}\n"
            f"  反馈: {c['message']}\n"
            f"  建议改写: {c.get('suggested_rewrite', '无')}"
        )

    prompt = (
        f"你是一位专业的内容编辑。请根据以下审核反馈修改文章段落。\n\n"
        f"文章标题：{draft['title']}\n"
        f"目标平台：{draft.get('platform', '通用')}\n"
        f"{pref_summary}\n\n"
        f"需要修改的段落和反馈：\n{''.join(block_instructions)}\n\n"
        f"请返回 JSON 数组，每个元素包含：\n"
        f'{{"block_id": "...", "new_content": "修改后的完整段落", "resolution": "修改说明"}}\n'
        f"只返回 JSON，不要其他内容。"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Parse LLM response
    text = data["content"][0]["text"].strip()
    # Extract JSON from possible markdown code block
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    revisions = json.loads(text)

    changes: list[dict[str, Any]] = []
    rationale: list[dict[str, Any]] = []
    comment_map = {c["anchor"]["block_id"]: c for c in accepted}

    for rev in revisions:
        bid = rev["block_id"]
        block = next((b for b in draft["blocks"] if b["id"] == bid), None)
        if not block:
            continue
        changes.append({
            "block_id": bid,
            "old_content": block["content"],
            "new_content": rev["new_content"],
        })
        cmt = comment_map.get(bid)
        rationale.append({
            "comment_id": cmt["id"] if cmt else "",
            "resolution": rev.get("resolution", "AI 已改写"),
        })

    return changes, rationale


@router.post("/drafts/{draft_id}/request-revision")
async def request_revision(draft_id: str, req: RevisionRequest) -> dict[str, Any]:
    """Request AI revision based on accepted comments."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft = _drafts[draft_id]
    comments = _comments.get(draft_id, [])
    accepted = [c for c in comments if c["id"] in req.accepted_comment_ids]

    if not accepted:
        raise HTTPException(status_code=400, detail="No accepted comments to revise")

    # 更新状态为 revising
    draft["status"] = "revising"
    draft["updated_at"] = datetime.now().isoformat()

    revision_id = f"rev_{uuid.uuid4().hex[:8]}"
    changes, rationale = await _generate_revision(draft, accepted)

    revision = {
        "revision_id": revision_id,
        "draft_id": draft_id,
        "changes": changes,
        "rationale": rationale,
        "created_at": datetime.now().isoformat(),
    }
    _revisions[revision_id] = revision

    return {"success": True, "revision": revision}


@router.post("/drafts/{draft_id}/apply-revision")
async def apply_revision(draft_id: str, revision_id: str) -> dict[str, Any]:
    """Apply a revision to the draft."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")
    if revision_id not in _revisions:
        raise HTTPException(status_code=404, detail="Revision not found")

    draft = _drafts[draft_id]
    revision = _revisions[revision_id]

    # 应用修改
    for change in revision["changes"]:
        for block in draft["blocks"]:
            if block["id"] == change["block_id"]:
                block["content"] = change["new_content"]
                break

    # 更新版本和状态
    draft["version"] = draft.get("version", 1) + 1
    draft["status"] = "in_review"
    draft["updated_at"] = datetime.now().isoformat()

    # 标记相关评论为 resolved
    comments = _comments.get(draft_id, [])
    resolved_ids = {r["comment_id"] for r in revision["rationale"]}
    for c in comments:
        if c["id"] in resolved_ids:
            c["status"] = "resolved"
            c["resolved_at"] = datetime.now().isoformat()

    return {"success": True, "data": draft}


# --- Preferences endpoints (backed by TasteProfile) ---


@router.get("/preferences")
async def get_preferences() -> dict[str, Any]:
    """Get user review preferences."""
    return {"success": True, "preferences": _get_preferences()}


@router.patch("/preferences")
async def update_preferences(req: PreferenceUpdate) -> dict[str, Any]:
    """Update user review preferences via TasteEngine."""
    prefs = _taste_profile.explicit_preferences
    if req.tone_prefer is not None:
        prefs.tone_prefer = req.tone_prefer
    if req.tone_avoid is not None:
        prefs.tone_avoid = req.tone_avoid
    if req.prefer_opening is not None:
        prefs.preferred_openings = req.prefer_opening
    if req.prefer_length is not None:
        prefs.preferred_length = req.prefer_length
    if req.emoji is not None:
        prefs.emoji_style = req.emoji
    if req.cta is not None:
        prefs.cta_style = req.cta
    # 通过 TasteEngine 更新，触发 recompute_vectors
    _taste_engine.update_preferences(prefs)
    return {"success": True, "preferences": _get_preferences()}


# --- Taste Profile endpoints ---


@router.get("/taste/profile")
async def get_taste_profile() -> dict[str, Any]:
    """Get the full taste profile."""
    return {
        "success": True,
        "profile": _taste_profile.model_dump(mode="json"),
    }


@router.get("/taste/phase")
async def get_taste_phase() -> dict[str, Any]:
    """Get current taste evolution phase and progress."""
    next_phase = _taste_profile.can_transition()
    return {
        "success": True,
        "phase": _taste_profile.phase,
        "can_transition_to": next_phase,
        "stats": {
            "total_feedback": _taste_profile.total_feedback_count,
            "approval_rate": round(_taste_profile.approval_rate, 2),
            "avg_confidence": round(_taste_profile.avg_taste_confidence, 2),
            "signal_count": len(_taste_profile.feedback_signals),
        },
    }


@router.get("/taste/prompt")
async def get_taste_prompt(platform: str = "general") -> dict[str, Any]:
    """Get the taste prompt for LLM injection."""
    prompt = _taste_engine.get_taste_prompt(platform)
    return {"success": True, "prompt": prompt, "platform": platform}


@router.post("/drafts/{draft_id}/feedback")
async def submit_draft_feedback(
    draft_id: str, req: DraftFeedbackRequest
) -> dict[str, Any]:
    """Submit structured feedback on a draft, recording taste signals."""
    if draft_id not in _drafts:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft = _drafts[draft_id]

    if req.action == "approve":
        draft["status"] = "approved"
        _taste_profile.approval_count += 1
        _taste_profile.total_feedback_count += 1
        # 通过 = 强化该稿件风格
        _record_taste_signal("feedback", "overall", "like", draft["title"][:40], draft_id)
    elif req.action == "reject":
        draft["status"] = "rejected"
        _taste_profile.rejection_count += 1
        _taste_profile.total_feedback_count += 1
        _record_taste_signal(
            "feedback", "overall", "dislike",
            req.reason[:60] if req.reason else "rejected",
            draft_id,
        )
    elif req.action == "comment":
        _taste_profile.total_feedback_count += 1
        if req.reason:
            _record_taste_signal("feedback", "comment", "like", req.reason[:60], draft_id)

    draft["updated_at"] = datetime.now().isoformat()

    # 记录反馈日志
    log_entry = {
        "id": f"tfb_{uuid.uuid4().hex[:8]}",
        "draft_id": draft_id,
        "action": req.action,
        "reason": req.reason,
        "created_at": datetime.now().isoformat(),
    }
    _feedback_logs.append(log_entry)

    return {
        "success": True,
        "feedback": log_entry,
        "taste_phase": _taste_profile.phase,
        "can_transition": _taste_profile.can_transition(),
    }
