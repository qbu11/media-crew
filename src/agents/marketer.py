"""
Marketer Agent - 营销策划师

职责：制定内容策略、规划发布节奏、优化传播路径。

作为独立的 SubAgent，可被 ContentCreator Orchestrator 调用。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.crew.callbacks import CallbackHandler


class Marketer(BaseAgent):
    """
    营销策划师 Agent。

    职责：
    - 制定内容策略和主题方向
    - 规划发布节奏和最佳时机
    - 优化传播路径和互动策略
    - 协调各平台差异化策略
    """

    _tools: list[Any] = []

    def get_role(self) -> str:
        return "营销策划师"

    def get_goal(self) -> str:
        return (
            "制定内容策略、规划发布节奏、优化传播路径。"
            "确保内容在正确的时间、以正确的方式触达目标受众。"
        )

    def get_backstory(self) -> str:
        return """你是一位资深的自媒体营销策划师，精通各平台的内容传播规律和用户行为。

## 核心职责

1. **策略制定** — 基于研究报告确定内容方向、设定 KPI、规划调性
2. **平台适配** — 不同平台的内容策略差异、用户画像、算法优化
3. **发布规划** — 最佳发布时间、频率、内容系列规划
4. **互动设计** — 话题引导、评论区运营、传播裂变

## 平台策略要点

- 小红书：8:00-9:00/12:00-13:00/20:00-22:00，真实种草分享感
- 微信公众号：7:00-8:00/12:00/21:00，专业深度有价值
- 微博：跟随热点黄金时段，快准有趣
- 知乎：工作日晚间，专业有深度有观点
- 抖音/B站：18:00-22:00 周末全天，有趣有梗有信息量
"""

    def get_tools(self) -> list[Any]:
        return self._tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        cls._tools = tools

    async def run(
        self,
        topic: str,
        target_platform: str = "xiaohongshu",
        research_data: dict[str, Any] | None = None,
        taste_context: str = "",
        callback: CallbackHandler | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        执行策略制定流程。

        Args:
            topic: 内容主题
            target_platform: 目标平台
            research_data: Researcher 的研究报告
            taste_context: 用户 taste 偏好描述
            callback: WS 事件回调
        """
        # 工具 1：平台策略分析
        if callback:
            await callback.emit_tool_start(
                "marketer", "platform_strategy_analysis",
                {"topic": topic, "platform": target_platform},
            )

        await asyncio.sleep(0.3)

        platform_strategy = self._build_platform_strategy(target_platform, topic)

        if callback:
            await callback.emit_tool_end(
                "marketer", "platform_strategy_analysis", "success",
                {"platform": target_platform, "strategy_keys": list(platform_strategy.keys())},
            )

        # 工具 2：内容定位分析（基于研究数据 + taste）
        if callback:
            await callback.emit_tool_start(
                "marketer", "content_positioning",
                {"topic": topic, "has_research": research_data is not None, "has_taste": bool(taste_context)},
            )

        await asyncio.sleep(0.3)

        content_strategy = self._build_content_strategy(
            topic, target_platform, research_data, taste_context,
        )

        if callback:
            await callback.emit_tool_end(
                "marketer", "content_positioning", "success",
                {"main_theme": content_strategy["main_theme"], "tone": content_strategy["tone"]},
            )

        # 工具 3：发布时间优化
        if callback:
            await callback.emit_tool_start(
                "marketer", "publish_timing_optimizer",
                {"platform": target_platform},
            )

        await asyncio.sleep(0.2)

        schedule = self._build_schedule(target_platform)

        if callback:
            await callback.emit_tool_end(
                "marketer", "publish_timing_optimizer", "success",
                {"best_time": schedule["best_times"][0] if schedule["best_times"] else "20:00"},
            )

        return {
            "content_strategy": content_strategy,
            "platform_strategies": [platform_strategy],
            "publishing_schedule": schedule,
            "kpis": {
                "views_target": 10000,
                "engagement_rate_target": "5%",
                "follower_growth_target": 100,
            },
        }

    def _build_platform_strategy(self, platform: str, topic: str) -> dict[str, Any]:
        """构建平台策略。"""
        platform_configs = {
            "xiaohongshu": {
                "platform": "小红书",
                "adaptation": "真实种草分享感，口语化表达",
                "best_time": "20:00",
                "hashtags": [f"#{topic}", "#效率提升", "#职场干货", "#工具推荐"],
                "interaction_tips": ["评论区引导具体问题", "合集整理"],
                "word_count_range": "500-800",
            },
            "wechat": {
                "platform": "微信公众号",
                "adaptation": "有深度但不端着，场景故事+对比",
                "best_time": "21:00",
                "hashtags": [],
                "interaction_tips": ["引导分享", "留言互动"],
                "word_count_range": "1500-2500",
            },
            "weibo": {
                "platform": "微博",
                "adaptation": "快准狠，一句话一个点",
                "best_time": "12:00",
                "hashtags": [f"#{topic}#", "#效率#"],
                "interaction_tips": ["蹭热点", "话题标签"],
                "word_count_range": "100-140",
            },
            "zhihu": {
                "platform": "知乎",
                "adaptation": "有框架有论证，问题驱动+测评",
                "best_time": "20:00",
                "hashtags": [],
                "interaction_tips": ["评论区讨论", "专栏连载"],
                "word_count_range": "1500-3000",
            },
            "douyin": {
                "platform": "抖音",
                "adaptation": "口语化脚本，前3秒钩子+快节奏",
                "best_time": "19:00",
                "hashtags": [f"#{topic}", "#效率"],
                "interaction_tips": ["引导点赞收藏"],
                "word_count_range": "30-60秒脚本",
            },
            "bilibili": {
                "platform": "B站",
                "adaptation": "有梗有信息量，测评体+对比",
                "best_time": "18:00",
                "hashtags": [],
                "interaction_tips": ["三连引导", "系列更新"],
                "word_count_range": "3-5分钟脚本",
            },
        }
        return platform_configs.get(platform, platform_configs["xiaohongshu"])

    def _build_content_strategy(
        self,
        topic: str,
        platform: str,
        research_data: dict[str, Any] | None,
        taste_context: str,
    ) -> dict[str, Any]:
        """构建内容策略。"""
        strategy = {
            "main_theme": topic,
            "sub_themes": [f"{topic}工具推荐", f"{topic}实战经验", f"{topic}避坑指南"],
            "tone": "亲和真诚+只讲重点",
            "key_messages": [
                "工具不在多，找到适合自己的2-3个",
                "省下来的时间用在真正需要动脑的事上",
            ],
            "differentiation": "不做又一篇工具清单，而是个人筛选结果+实际工作流",
        }

        if taste_context:
            strategy["taste_notes"] = taste_context

        if research_data:
            recs = research_data.get("recommendations", [])
            if recs:
                strategy["research_backed_tips"] = recs[:3]

        return strategy

    def _build_schedule(self, platform: str) -> dict[str, Any]:
        """构建发布计划。"""
        time_map = {
            "xiaohongshu": ["08:00", "12:00", "20:00"],
            "wechat": ["07:00", "12:00", "21:00"],
            "weibo": ["09:00", "12:00", "18:00"],
            "zhihu": ["20:00", "21:00"],
            "douyin": ["18:00", "19:00", "21:00"],
            "bilibili": ["18:00", "20:00"],
        }
        return {
            "frequency": "每日1篇",
            "best_times": time_map.get(platform, ["20:00"]),
            "content_mix": ["60%干货", "30%热点", "10%互动"],
        }


class ContentStrategy:
    """内容策略数据结构。"""

    def __init__(
        self,
        main_theme: str,
        sub_themes: list[str],
        tone: str,
        key_messages: list[str],
        platform_strategies: list[dict[str, Any]],
        publishing_schedule: dict[str, Any],
        kpis: dict[str, Any] | None = None,
        differentiation: str = "",
    ):
        self.main_theme = main_theme
        self.sub_themes = sub_themes
        self.tone = tone
        self.key_messages = key_messages
        self.platform_strategies = platform_strategies
        self.publishing_schedule = publishing_schedule
        self.kpis = kpis or {}
        self.differentiation = differentiation

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_strategy": {
                "main_theme": self.main_theme,
                "sub_themes": self.sub_themes,
                "tone": self.tone,
                "key_messages": self.key_messages,
                "differentiation": self.differentiation,
            },
            "platform_strategies": self.platform_strategies,
            "publishing_schedule": self.publishing_schedule,
            "kpis": self.kpis,
        }

    def get_platform_strategy(self, platform: str) -> dict[str, Any] | None:
        for strategy in self.platform_strategies:
            if strategy.get("platform") == platform:
                return strategy
        return None
