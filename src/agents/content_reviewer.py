"""
Content Reviewer Agent

内容审核员：审核内容质量、合规性，提供优化建议。
"""

from enum import Enum
from typing import Any

from .base_agent import BaseAgent


class ReviewResult(Enum):
    """审核结果枚举。"""

    APPROVED = "approved"  # 通过
    NEEDS_REVISION = "needs_revision"  # 需要修改
    REJECTED = "rejected"  # 拒绝


class ContentReviewer(BaseAgent):
    """
    内容审核员 Agent。

    职责：
    - 审核内容质量和专业性
    - 检查内容合规性（法律、平台规则）
    - 评估传播潜力
    - 提供具体的优化建议
    - 支持人工审核环节
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def __init__(
        self,
        llm: str | None = None,
        tools: list[Any] | None = None,
        verbose: bool = True,
        allow_delegation: bool = False,
        human_input: bool = True,  # 默认启用人工输入
    ):
        """
        初始化内容审核员。

        Args:
            llm: 使用的 LLM 模型名称
            tools: Agent 可用的工具列表
            verbose: 是否输出详细日志
            allow_delegation: 是否允许任务委托（审核员默认不允许）
            human_input: 是否需要人工输入（审核员默认需要）
        """
        super().__init__(
            llm=llm,
            tools=tools,
            verbose=verbose,
            allow_delegation=allow_delegation,
            human_input=human_input,
        )

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "内容审核员"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "严格审核内容的质量、准确性和合规性，确保内容符合平台规则 "
            "和法律法规，同时提供具体的优化建议以提升内容价值"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位资深的内容审核专家，拥有丰富的媒体审核经验。
你对各平台的内容规范了如指掌，能够快速识别敏感内容和潜在风险。
你的审核标准严格但公正，总是能提供具体、可操作的优化建议。
你深知内容创作的不易，因此在指出问题的同时也会肯定内容的亮点。
你擅长平衡内容质量和传播效果，帮助创作者在合规的前提下最大化内容影响力。
你的人工审核环节是内容发布前的最后一道防线。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - sensitive_content_checker: 敏感内容检测工具
        # - plagiarism_checker: 抄袭检测工具
        # - grammar_checker: 语法检查工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class ReviewReport:
    """
    审核报告数据结构。

    用于规范化内容审核员的输出格式。
    """

    def __init__(
        self,
        result: ReviewResult,
        quality_score: float,
        compliance_score: float,
        spread_score: float,
        issues: list[dict[str, Any]],
        suggestions: list[str],
        highlights: list[str],
        reviewer_notes: str,
    ):
        """
        初始化审核报告。

        Args:
            result: 审核结果
            quality_score: 质量评分（0-100）
            compliance_score: 合规评分（0-100）
            spread_score: 传播评分（0-100）
            issues: 问题列表，每项包含位置、类型、描述
            suggestions: 优化建议列表
            highlights: 内容亮点列表
            reviewer_notes: 审核员备注
        """
        self.result = result
        self.quality_score = quality_score
        self.compliance_score = compliance_score
        self.spread_score = spread_score
        self.issues = issues
        self.suggestions = suggestions
        self.highlights = highlights
        self.reviewer_notes = reviewer_notes

    @property
    def overall_score(self) -> float:
        """计算综合评分。"""
        return (
            self.quality_score * 0.4
            + self.compliance_score * 0.35
            + self.spread_score * 0.25
        )

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "result": self.result.value,
            "overall_score": self.overall_score,
            "quality_score": self.quality_score,
            "compliance_score": self.compliance_score,
            "spread_score": self.spread_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "highlights": self.highlights,
            "reviewer_notes": self.reviewer_notes,
        }

    def is_approved(self) -> bool:
        """检查是否通过审核。"""
        return self.result == ReviewResult.APPROVED
