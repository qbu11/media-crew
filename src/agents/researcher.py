"""
Researcher Agent - 热点研究员

职责：追踪热点、研究趋势、分析竞品、收集爆款参考。

作为独立的 SubAgent，可被 ContentCreator Orchestrator 调用。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.crew.callbacks import CallbackHandler


class Researcher(BaseAgent):
    """
    热点研究员 Agent。

    职责：
    - 追踪各平台热点话题和趋势
    - 分析竞品内容策略
    - 收集爆款内容作为参考
    - 输出研究报告供后续使用
    """

    _tools: list[Any] = []

    def get_role(self) -> str:
        return "热点研究员"

    def get_goal(self) -> str:
        return (
            "追踪热点、分析趋势、研究竞品、收集爆款参考。"
            "为内容创作提供数据支持和方向指引。"
        )

    def get_backstory(self) -> str:
        return """你是一位资深的自媒体热点研究员，拥有敏锐的热点嗅觉和丰富的数据收集经验。

## 核心职责

1. **热点追踪** — 微博热搜、小红书热榜、知乎热榜、抖音热点、B站热门
2. **趋势分析** — 话题传播路径、用户情绪、热度持续时间预测
3. **竞品研究** — 同垂类头部账号追踪、内容发布节奏、爆款模式提炼
4. **爆款收集** — 至少 5 个相关爆款，分析结构/情绪/配图/标题/内容深度

## 工作原则

- **数据驱动**：所有结论必须有数据支撑
- **时效优先**：优先关注 24 小时内的新热点
- **相关性**：只收集与研究主题高度相关的内容
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
        callback: CallbackHandler | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        执行研究流程。

        Args:
            topic: 研究主题
            target_platform: 目标平台
            callback: WS 事件回调
        """
        from src.tools.search_tools import HotSearchTool, TrendAnalysisTool

        report: dict[str, Any] = {
            "topic": topic,
            "trending_topics": [],
            "viral_references": [],
            "competitor_insights": [],
            "recommendations": [],
        }

        # 工具 1：热点搜索
        if callback:
            await callback.emit_tool_start(
                "researcher", "hot_search",
                {"keywords": topic, "platform": target_platform},
            )

        hot_tool = HotSearchTool()
        hot_result = hot_tool.execute(platform=target_platform, limit=10)

        if callback:
            await callback.emit_tool_end(
                "researcher", "hot_search", "success",
                {"count": len(hot_result.data.get("results", []))},
            )

        report["trending_topics"] = hot_result.data.get("results", [])

        # 工具 2：趋势分析
        if callback:
            await callback.emit_tool_start(
                "researcher", "trend_analysis",
                {"keyword": topic, "time_range": "7d"},
            )

        trend_tool = TrendAnalysisTool()
        trend_result = trend_tool.execute(keyword=topic, time_range="7d")

        if callback:
            await callback.emit_tool_end(
                "researcher", "trend_analysis", "success",
                {
                    "trend_direction": trend_result.data.get("trend_direction"),
                    "trend_score": trend_result.data.get("trend_score"),
                },
            )

        report["trend_analysis"] = trend_result.data

        # 工具 3：爆款搜索（使用 LLM 生成结构化爆款分析）
        if callback:
            await callback.emit_tool_start(
                "researcher", "viral_search",
                {"topic": topic, "platform": target_platform, "count": 5},
            )

        # 模拟异步工作（实际会调用 LLM 或搜索 API）
        await asyncio.sleep(0.5)

        report["viral_references"] = [
            {
                "title": f"[{target_platform}] {topic}相关爆款{i + 1}",
                "platform": target_platform,
                "metrics": {"likes": 10000 - i * 1000, "comments": 500 - i * 50},
                "analysis": {
                    "structure": "清单体" if i % 2 == 0 else "故事体",
                    "emotion": "实用驱动" if i % 2 == 0 else "焦虑缓解",
                    "title_technique": "数字+痛点",
                    "content_depth": "中等",
                },
            }
            for i in range(5)
        ]

        if callback:
            await callback.emit_tool_end(
                "researcher", "viral_search", "success",
                {"count": len(report["viral_references"])},
            )

        report["recommendations"] = [
            "标题使用数字+痛点词组合",
            "开篇用焦虑钩子，中段给框架安全感",
            "对比表格放在文章60-70%位置",
            "互动引导要具体，不要泛泛的'欢迎评论'",
        ]

        return report


class ResearchReport:
    """研究报告数据结构。"""

    def __init__(
        self,
        topic: str,
        trending_topics: list[dict[str, Any]],
        viral_references: list[dict[str, Any]],
        competitor_insights: list[dict[str, Any]] | None = None,
        recommendations: list[str] | None = None,
    ):
        self.topic = topic
        self.trending_topics = trending_topics
        self.viral_references = viral_references
        self.competitor_insights = competitor_insights or []
        self.recommendations = recommendations or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "trending_topics": self.trending_topics,
            "viral_references": self.viral_references,
            "competitor_insights": self.competitor_insights,
            "recommendations": self.recommendations,
        }

    @property
    def viral_count(self) -> int:
        return len(self.viral_references)
