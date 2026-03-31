"""Onboarding API routes - 用户偏好引导."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.onboarding import OnboardingAgent
from src.api.routes.review import _taste_engine

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# 单例 OnboardingAgent，共享 TasteEngine
_onboarding_agent = OnboardingAgent(_taste_engine)


class AnswerRequest(BaseModel):
    answer: Any  # str 或 list[str]


class DraftFeedbackRequest(BaseModel):
    draft_id: str
    action: str  # approve | reject | comment
    reason: str = ""


@router.post("/start")
async def start_onboarding() -> dict[str, Any]:
    """开始新的 onboarding 会话。"""
    session_id = f"onboard-{uuid.uuid4().hex[:8]}"
    step = _onboarding_agent.start_session(session_id)
    return {"success": True, "session_id": session_id, **step}


@router.get("/{session_id}")
async def get_current_step(session_id: str) -> dict[str, Any]:
    """获取当前 onboarding 步骤。"""
    session = _onboarding_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, **session.get_current_step()}


@router.post("/{session_id}/answer")
async def answer_step(session_id: str, req: AnswerRequest) -> dict[str, Any]:
    """回答当前步骤。"""
    result = _onboarding_agent.answer_step(session_id, req.answer)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"success": True, **result}


@router.post("/{session_id}/draft-feedback")
async def draft_feedback(session_id: str, req: DraftFeedbackRequest) -> dict[str, Any]:
    """对样稿提交反馈，沉淀到 TasteEngine。"""
    result = _onboarding_agent.record_draft_feedback(
        session_id=session_id,
        draft_id=req.draft_id,
        action=req.action,
        reason=req.reason,
    )
    return {"success": True, **result}


@router.get("/{session_id}/taste-prompt")
async def get_taste_prompt_for_session(
    session_id: str, platform: str = "general"
) -> dict[str, Any]:
    """获取当前会话的 taste prompt（用于生成样稿）。"""
    session = _onboarding_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    prompt = _taste_engine.get_taste_prompt(platform)
    return {"success": True, "prompt": prompt, "platform": platform}
