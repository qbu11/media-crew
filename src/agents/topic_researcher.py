"""
Topic Researcher Agent

选题研究员：追踪热点、分析竞品、挖掘高潜力选题。
"""

from typing import Any

from .base_agent import BaseAgent


class TopicResearcher(BaseAgent):
    """
    选题研究员 Agent。

    职责：
    - 追踪各平台热点话题和趋势
    - 分析竞品内容和策略
    - 挖掘高潜力选题
    - 生成选题报告和内容建议
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "选题研究员"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "追踪热点、分析竞品、挖掘高潜力选题，为内容创作团队提供 "
            "有价值、可执行、符合平台调性的选题建议和内容方向"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位资深的选题研究员，拥有 5 年自媒体行业经验。
你擅长从海量信息中捕捉趋势，对各大内容平台（微信公众号、小红书、抖音、B站、知乎）
的热点机制了如指掌。你能够快速分析竞品的内容策略，找到差异化的选题方向。
你的选题报告总是数据翔实、洞察深刻，帮助团队在内容创作上事半功倍。
你深谙用户心理，知道什么样的内容能够引发共鸣和传播。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - hot_topic_tracker: 热点追踪工具
        # - competitor_analyzer: 竞品分析工具
        # - trend_predictor: 趋势预测工具
        # - search_tool: 搜索工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class TopicReport:
    """
    选题报告数据结构。

    用于规范化选题研究员的输出格式。
    """

    def __init__(
        self,
        title: str,
        category: str,
        potential_score: float,
        reasoning: str,
        reference_content: list[str],
        target_audience: str,
        suggested_angle: str,
        keywords: list[str],
    ):
        """
        初始化选题报告。

        Args:
            title: 选题标题
            category: 内容分类
            potential_score: 潜力评分（0-100）
            reasoning: 选择理由
            reference_content: 参考内容链接
            target_audience: 目标受众
            suggested_angle: 建议切入点
            keywords: 关键词列表
        """
        self.title = title
        self.category = category
        self.potential_score = potential_score
        self.reasoning = reasoning
        self.reference_content = reference_content
        self.target_audience = target_audience
        self.suggested_angle = suggested_angle
        self.keywords = keywords

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "title": self.title,
            "category": self.category,
            "potential_score": self.potential_score,
            "reasoning": self.reasoning,
            "reference_content": self.reference_content,
            "target_audience": self.target_audience,
            "suggested_angle": self.suggested_angle,
            "keywords": self.keywords,
        }
