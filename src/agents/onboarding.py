"""
Onboarding Agent - 用户偏好引导

职责：引导新用户通过对话录入 taste 偏好，沉淀到 TasteProfile。

流程：
1. 问大方向（领域、调性、平台）
2. 生成样稿供用户反馈
3. 根据反馈迭代，直到用户满意
4. 偏好沉淀到 TasteEngine
"""

from __future__ import annotations

import logging
from typing import Any

from src.schemas.taste_profile import ExplicitPreferences
from src.services.taste_engine import TasteEngine

logger = logging.getLogger(__name__)


# Onboarding 阶段定义
ONBOARDING_STEPS = [
    {
        "step": "domain",
        "question": "你主要创作哪个领域的内容？",
        "options": [
            {"key": "tech", "label": "科技/AI/互联网"},
            {"key": "career", "label": "职场/成长/认知"},
            {"key": "lifestyle", "label": "生活方式/旅行/美食"},
            {"key": "education", "label": "教育/知识分享"},
            {"key": "other", "label": "其他"},
        ],
    },
    {
        "step": "tone",
        "question": "你的内容调性更偏向？（可多选）",
        "multi_select": True,
        "options": [
            {"key": "professional", "label": "专业权威", "desc": "深度分析、数据驱动"},
            {"key": "friendly", "label": "亲和真诚", "desc": "像朋友聊天"},
            {"key": "humorous", "label": "幽默风趣", "desc": "轻松有趣"},
            {"key": "concise", "label": "极简干货", "desc": "只讲重点"},
        ],
    },
    {
        "step": "platforms",
        "question": "你主要在哪些平台发布？（可多选）",
        "multi_select": True,
        "options": [
            {"key": "xiaohongshu", "label": "小红书"},
            {"key": "wechat", "label": "微信公众号"},
            {"key": "weibo", "label": "微博"},
            {"key": "zhihu", "label": "知乎"},
            {"key": "douyin", "label": "抖音"},
            {"key": "bilibili", "label": "B站"},
        ],
    },
    {
        "step": "length",
        "question": "你偏好的文章长度？",
        "options": [
            {"key": "short", "label": "短（500字以内）"},
            {"key": "medium", "label": "中（500-1500字）"},
            {"key": "long", "label": "长（1500字以上）"},
        ],
    },
    {
        "step": "opening",
        "question": "你偏好的开场方式？（可多选）",
        "multi_select": True,
        "options": [
            {"key": "pain_point", "label": "痛点开场", "desc": "直击读者焦虑"},
            {"key": "counter_intuitive", "label": "反常识开场", "desc": "颠覆认知"},
            {"key": "story", "label": "故事开场", "desc": "个人经历引入"},
            {"key": "data", "label": "数据开场", "desc": "用数字说话"},
            {"key": "question", "label": "提问开场", "desc": "引发思考"},
        ],
    },
    {
        "step": "avoid",
        "question": "你希望避免什么风格？（可多选）",
        "multi_select": True,
        "options": [
            {"key": "too_marketing", "label": "太营销", "desc": "像广告"},
            {"key": "too_formal", "label": "太官话", "desc": "像新闻稿"},
            {"key": "too_template", "label": "太像模板", "desc": "千篇一律"},
            {"key": "too_long", "label": "废话太多", "desc": "铺垫太长"},
            {"key": "too_exaggerated", "label": "太夸张", "desc": "震惊体"},
        ],
    },
]

# 选项 key → 自然语言映射
TONE_MAP = {
    "professional": "专业权威",
    "friendly": "亲和真诚",
    "humorous": "幽默风趣",
    "concise": "只讲重点",
}

OPENING_MAP = {
    "pain_point": "痛点开场",
    "counter_intuitive": "反常识开场",
    "story": "故事开场",
    "data": "数据开场",
    "question": "提问开场",
}

AVOID_MAP = {
    "too_marketing": "太营销",
    "too_formal": "太官话",
    "too_template": "太像模板",
    "too_long": "废话太多",
    "too_exaggerated": "太夸张",
}


class OnboardingAgent:
    """
    用户偏好引导 Agent。

    管理 onboarding 会话状态，收集用户回答，最终写入 TasteEngine。
    """

    def __init__(self, taste_engine: TasteEngine):
        self._engine = taste_engine
        self._sessions: dict[str, OnboardingSession] = {}

    def start_session(self, session_id: str) -> dict[str, Any]:
        """开始新的 onboarding 会话。"""
        session = OnboardingSession(session_id)
        self._sessions[session_id] = session
        return session.get_current_step()

    def get_session(self, session_id: str) -> OnboardingSession | None:
        return self._sessions.get(session_id)

    def answer_step(self, session_id: str, answer: Any) -> dict[str, Any]:
        """回答当前步骤，返回下一步或完成状态。"""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}

        session.record_answer(answer)

        if session.is_complete():
            # 所有步骤完成，写入 TasteEngine
            prefs = session.build_preferences()
            self._engine.update_preferences(prefs)
            taste_prompt = self._engine.get_taste_prompt()

            return {
                "status": "completed",
                "message": "偏好录入完成！",
                "preferences": prefs.model_dump(),
                "taste_prompt": taste_prompt,
                "session_id": session_id,
            }

        return session.get_current_step()

    def record_draft_feedback(
        self, session_id: str, draft_id: str, action: str, reason: str = ""
    ) -> dict[str, Any]:
        """记录用户对样稿的反馈，沉淀到 TasteEngine。"""
        signals = self._engine.record_feedback(
            draft_id=draft_id,
            action=action,
            details={"reason": reason} if reason else None,
        )
        return {
            "signals_extracted": len(signals),
            "total_feedback": self._engine.profile.total_feedback_count,
            "phase": self._engine.profile.phase,
        }


class OnboardingSession:
    """单个 onboarding 会话的状态。"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_step_index = 0
        self.answers: dict[str, Any] = {}

    def get_current_step(self) -> dict[str, Any]:
        """返回当前步骤的问题和选项。"""
        if self.current_step_index >= len(ONBOARDING_STEPS):
            return {"status": "completed"}

        step = ONBOARDING_STEPS[self.current_step_index]
        return {
            "status": "in_progress",
            "step_index": self.current_step_index,
            "total_steps": len(ONBOARDING_STEPS),
            "progress": round(self.current_step_index / len(ONBOARDING_STEPS) * 100),
            **step,
        }

    def record_answer(self, answer: Any) -> None:
        """记录当前步骤的回答。"""
        if self.current_step_index < len(ONBOARDING_STEPS):
            step_key = ONBOARDING_STEPS[self.current_step_index]["step"]
            self.answers[step_key] = answer
            self.current_step_index += 1

    def is_complete(self) -> bool:
        return self.current_step_index >= len(ONBOARDING_STEPS)

    def build_preferences(self) -> ExplicitPreferences:
        """从收集的回答构建 ExplicitPreferences。"""
        tone_keys = self.answers.get("tone", [])
        if isinstance(tone_keys, str):
            tone_keys = [tone_keys]
        tone_prefer = [TONE_MAP.get(k, k) for k in tone_keys]

        avoid_keys = self.answers.get("avoid", [])
        if isinstance(avoid_keys, str):
            avoid_keys = [avoid_keys]
        tone_avoid = [AVOID_MAP.get(k, k) for k in avoid_keys]

        opening_keys = self.answers.get("opening", [])
        if isinstance(opening_keys, str):
            opening_keys = [opening_keys]
        preferred_openings = [OPENING_MAP.get(k, k) for k in opening_keys]

        length = self.answers.get("length", "short")

        # 构建 brand_voice
        brand_voice = "+".join(tone_prefer) if tone_prefer else "专业但不失亲和"

        # 构建平台覆盖
        platforms = self.answers.get("platforms", [])
        if isinstance(platforms, str):
            platforms = [platforms]

        return ExplicitPreferences(
            brand_voice=brand_voice,
            tone_prefer=tone_prefer,
            tone_avoid=tone_avoid,
            preferred_openings=preferred_openings,
            preferred_length=length,
            preferred_topics=[self.answers.get("domain", "")],
        )
