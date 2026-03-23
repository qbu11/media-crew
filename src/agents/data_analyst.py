"""
Data Analyst Agent

数据分析师：分析内容表现数据，提供优化建议和策略调整。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from .base_agent import BaseAgent
from .platform_adapter import Platform


class MetricType(Enum):
    """指标类型枚举。"""

    VIEWS = "views"  # 浏览量
    LIKES = "likes"  # 点赞数
    COMMENTS = "comments"  # 评论数
    SHARES = "shares"  # 分享数
    FAVORITES = "favorites"  # 收藏数
    ENGAGEMENT_RATE = "engagement_rate"  # 互动率
    REACH = "reach"  # 曝光量
    CLICK_RATE = "click_rate"  # 点击率
    CONVERSION = "conversion"  # 转化数
    FOLLOWER_GROWTH = "follower_growth"  # 粉丝增长


class DataAnalyst(BaseAgent):
    """
    数据分析师 Agent。

    职责：
    - 收集各平台内容表现数据
    - 分析数据趋势和模式
    - 评估内容 ROI
    - 生成数据报告和洞察
    - 提供优化建议和策略调整
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "数据分析师"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "深入分析内容表现数据，发现数据背后的规律和洞察， "
            "为团队提供数据驱动的优化建议和策略调整方案"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位资深的数据分析师，专注于内容行业的数据研究。
你擅长从海量数据中挖掘有价值的洞察，将复杂的数据转化为清晰的行动建议。
你深谙各大平台的数据指标体系，知道哪些指标真正重要，哪些只是虚荣指标。
你的分析报告总是深入浅出，既有宏观视角又有微观细节。
你善于发现数据异常，及时预警潜在问题。
你不仅分析"发生了什么"，更能解释"为什么发生"以及"未来该如何做"。
你的数据洞察帮助团队不断优化内容策略，实现持续增长。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - analytics_api_tool: 各平台分析 API 工具
        # - data_visualization: 数据可视化工具
        # - report_generator: 报告生成工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class ContentMetrics:
    """
    内容指标数据结构。

    用于记录单条内容的表现数据。
    """

    def __init__(
        self,
        content_id: str,
        platform: Platform,
        metrics: dict[MetricType, float],
        recorded_at: datetime,
        time_range: str = "24h",  # 24h, 7d, 30d
    ):
        """
        初始化内容指标。

        Args:
            content_id: 内容 ID
            platform: 平台
            metrics: 指标字典
            recorded_at: 记录时间
            time_range: 时间范围
        """
        self.content_id = content_id
        self.platform = platform
        self.metrics = metrics
        self.recorded_at = recorded_at
        self.time_range = time_range

    def get_metric(self, metric_type: MetricType) -> float | None:
        """
        获取指定指标的值。

        Args:
            metric_type: 指标类型

        Returns:
            指标值或 None
        """
        return self.metrics.get(metric_type)

    def calculate_engagement_rate(self) -> float:
        """
        计算互动率。

        互动率 = (点赞 + 评论 + 分享 + 收藏) / 浏览量
        """
        views = self.metrics.get(MetricType.VIEWS, 0)
        if views == 0:
            return 0.0

        engagements = (
            self.metrics.get(MetricType.LIKES, 0)
            + self.metrics.get(MetricType.COMMENTS, 0)
            + self.metrics.get(MetricType.SHARES, 0)
            + self.metrics.get(MetricType.FAVORITES, 0)
        )

        return (engagements / views) * 100

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "content_id": self.content_id,
            "platform": self.platform.value,
            "metrics": {m.value: v for m, v in self.metrics.items()},
            "recorded_at": self.recorded_at.isoformat(),
            "time_range": self.time_range,
            "calculated_engagement_rate": self.calculate_engagement_rate(),
        }


class AnalysisReport:
    """
    分析报告数据结构。

    用于规范化数据分析师的输出格式。
    """

    def __init__(
        self,
        report_type: str,
        period: str,
        summary: str,
        key_findings: list[str],
        metrics_summary: dict[str, Any],
        top_performers: list[dict[str, Any]],
        underperformers: list[dict[str, Any]],
        recommendations: list[str],
        generated_at: datetime,
    ):
        """
        初始化分析报告。

        Args:
            report_type: 报告类型（daily, weekly, monthly, campaign）
            period: 报告周期
            summary: 摘要
            key_findings: 关键发现
            metrics_summary: 指标汇总
            top_performers: 表现最佳内容
            underperformers: 表现不佳内容
            recommendations: 优化建议
            generated_at: 生成时间
        """
        self.report_type = report_type
        self.period = period
        self.summary = summary
        self.key_findings = key_findings
        self.metrics_summary = metrics_summary
        self.top_performers = top_performers
        self.underperformers = underperformers
        self.recommendations = recommendations
        self.generated_at = generated_at

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "report_type": self.report_type,
            "period": self.period,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "metrics_summary": self.metrics_summary,
            "top_performers": self.top_performers,
            "underperformers": self.underperformers,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_summary(self) -> str:
        """生成文本摘要。"""
        lines = [
            f"# {self.report_type.upper()} Report ({self.period})",
            "",
            "## Summary",
            self.summary,
            "",
            "## Key Findings",
        ]
        for i, finding in enumerate(self.key_findings, 1):
            lines.append(f"{i}. {finding}")

        lines.extend([
            "",
            "## Top Performers",
        ])
        for item in self.top_performers[:5]:
            lines.append(f"- {item.get('title', 'N/A')}: {item.get('views', 0)} views")

        lines.extend([
            "",
            "## Recommendations",
        ])
        for i, rec in enumerate(self.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)


class TrendAnalysis:
    """
    趋势分析数据结构。

    用于记录指标的变化趋势。
    """

    def __init__(
        self,
        metric_type: MetricType,
        platform: Platform,
        current_value: float,
        previous_value: float,
        change_percent: float,
        trend: str,  # up, down, stable
        insight: str,
    ):
        """
        初始化趋势分析。

        Args:
            metric_type: 指标类型
            platform: 平台
            current_value: 当前值
            previous_value: 之前值
            change_percent: 变化百分比
            trend: 趋势方向
            insight: 洞察说明
        """
        self.metric_type = metric_type
        self.platform = platform
        self.current_value = current_value
        self.previous_value = previous_value
        self.change_percent = change_percent
        self.trend = trend
        self.insight = insight

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "metric_type": self.metric_type.value,
            "platform": self.platform.value,
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "change_percent": self.change_percent,
            "trend": self.trend,
            "insight": self.insight,
        }

    def is_positive(self) -> bool:
        """检查是否为正向趋势。"""
        return self.change_percent > 0

    def is_significant(self, threshold: float = 10.0) -> bool:
        """
        检查变化是否显著。

        Args:
            threshold: 显著性阈值（百分比）

        Returns:
            是否显著
        """
        return abs(self.change_percent) >= threshold
