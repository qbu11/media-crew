"""Taste profile schema - 用户口味档案核心数据模型.

Taste 由三因素决定：
- Factor A: 用户对稿件的反馈（通过/拒绝/编辑/评论）
- Factor B: 用户显式偏好（品牌调性、风格、话题）
- Factor C: 账号流量数据 + 垂类竞品对比
"""

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TasteSignal(BaseModel):
    """单条口味信号，来自任意因素."""

    source: Literal["feedback", "preference", "analytics"] = Field(
        ..., description="信号来源: feedback(A), preference(B), analytics(C)"
    )
    dimension: str = Field(
        ..., description="口味维度: tone, structure, opening, length, topic, emotion..."
    )
    signal_type: str = Field(
        ..., description="信号类型: like, dislike, edit, high_perform, low_perform"
    )
    value: str = Field(..., description="具体值，如 '痛点开场', '真诚', '短文'")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="权重，随时间衰减")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度，重复出现则增强")
    created_at: datetime = Field(default_factory=datetime.now)
    content_id: str | None = Field(default=None, description="触发此信号的稿件 ID")

    def decayed_weight(self, now: datetime | None = None) -> float:
        """计算时间衰减后的权重. λ=0.05/天, 30天后降至~22%."""
        now = now or datetime.now()
        days = (now - self.created_at).total_seconds() / 86400
        decay = math.exp(-0.05 * days)
        return self.weight * decay


class ExplicitPreferences(BaseModel):
    """Factor B: 用户显式声明的偏好."""

    brand_voice: str = Field(default="专业但不失亲和", description="品牌调性")
    tone_prefer: list[str] = Field(
        default_factory=lambda: ["真诚", "具体", "专业但不装"],
        description="偏好的语气风格",
    )
    tone_avoid: list[str] = Field(
        default_factory=lambda: ["太营销", "太官话", "太像模板"],
        description="避免的语气风格",
    )
    preferred_topics: list[str] = Field(default_factory=list, description="偏好话题")
    avoided_topics: list[str] = Field(default_factory=list, description="避免话题")
    preferred_openings: list[str] = Field(
        default_factory=lambda: ["痛点开场", "反常识开场"],
        description="偏好的开场方式",
    )
    preferred_length: Literal["short", "medium", "long"] = Field(
        default="short", description="偏好文章长度"
    )
    emoji_style: Literal["none", "light", "heavy"] = Field(
        default="light", description="emoji 使用风格"
    )
    cta_style: Literal["none", "soft", "strong"] = Field(
        default="soft", description="行动号召风格"
    )
    platform_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="平台级偏好覆盖"
    )


class CompetitorBenchmark(BaseModel):
    """垂类竞品对标数据."""

    competitor_name: str = Field(..., description="竞品账号名")
    platform: str = Field(..., description="平台")
    avg_likes: float = Field(default=0.0, ge=0.0)
    avg_comments: float = Field(default=0.0, ge=0.0)
    top_content_patterns: list[str] = Field(default_factory=list, description="高表现内容模式")
    our_percentile: float = Field(
        default=50.0, ge=0.0, le=100.0, description="我们在竞品中的百分位"
    )


class AnalyticsInsights(BaseModel):
    """Factor C: 数据分析得出的洞察."""

    top_performing_topics: list[str] = Field(default_factory=list, description="高表现话题")
    top_performing_structures: list[str] = Field(default_factory=list, description="高表现结构")
    top_performing_tones: list[str] = Field(default_factory=list, description="高表现语气")
    avg_engagement_by_topic: dict[str, float] = Field(
        default_factory=dict, description="各话题平均互动率"
    )
    avg_engagement_by_platform: dict[str, float] = Field(
        default_factory=dict, description="各平台平均互动率"
    )
    competitor_benchmarks: list[CompetitorBenchmark] = Field(
        default_factory=list, description="竞品对标"
    )
    last_analyzed_at: datetime | None = Field(default=None, description="最后分析时间")


class TasteVector(BaseModel):
    """聚合后的口味向量，代表某个维度的偏好."""

    dimension: str = Field(..., description="维度名: tone, structure, opening, length...")
    preferences: dict[str, float] = Field(
        default_factory=dict, description="正向偏好: value -> 强度(0-1)"
    )
    anti_preferences: dict[str, float] = Field(
        default_factory=dict, description="负向偏好: value -> 强度(0-1)"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="该维度的整体置信度")
    sample_count: int = Field(default=0, ge=0, description="贡献信号数量")

    def top_preferences(self, n: int = 3) -> list[tuple[str, float]]:
        """返回最强的 n 个正向偏好."""
        sorted_prefs = sorted(self.preferences.items(), key=lambda x: x[1], reverse=True)
        return sorted_prefs[:n]

    def top_anti_preferences(self, n: int = 3) -> list[tuple[str, float]]:
        """返回最强的 n 个负向偏好."""
        sorted_anti = sorted(self.anti_preferences.items(), key=lambda x: x[1], reverse=True)
        return sorted_anti[:n]


# 阶段转换阈值
PHASE_THRESHOLDS = {
    "manual_to_semi_auto": {
        "min_feedback_count": 20,
        "min_approval_rate": 0.6,
        "min_taste_confidence": 0.7,
    },
    "semi_auto_to_auto": {
        "min_feedback_count": 50,
        "min_approval_rate": 0.8,
        "min_taste_confidence": 0.85,
        "min_analytics_correlation": 0.7,
    },
}

# 三因素权重随阶段变化
PHASE_FACTOR_WEIGHTS: dict[str, dict[str, float]] = {
    "manual": {"feedback": 0.50, "preference": 0.40, "analytics": 0.10},
    "semi_auto": {"feedback": 0.40, "preference": 0.25, "analytics": 0.35},
    "auto": {"feedback": 0.30, "preference": 0.15, "analytics": 0.55},
}


class TasteProfile(BaseModel):
    """完整用户口味档案 - 产品核心数据结构."""

    user_id: str = Field(default="default", description="用户 ID")
    version: int = Field(default=1, ge=1, description="档案版本号")
    phase: Literal["manual", "semi_auto", "auto"] = Field(
        default="manual", description="当前进化阶段"
    )

    # Factor B: 显式偏好
    explicit_preferences: ExplicitPreferences = Field(
        default_factory=ExplicitPreferences, description="用户显式偏好"
    )

    # Factor C: 数据洞察
    analytics_insights: AnalyticsInsights = Field(
        default_factory=AnalyticsInsights, description="数据分析洞察"
    )

    # Factor A: 反馈信号（原始记录）
    feedback_signals: list[TasteSignal] = Field(
        default_factory=list, description="所有口味信号"
    )

    # 聚合后的口味向量
    taste_vectors: list[TasteVector] = Field(
        default_factory=list, description="聚合口味向量"
    )

    # 进化追踪
    total_feedback_count: int = Field(default=0, ge=0, description="累计反馈次数")
    approval_count: int = Field(default=0, ge=0, description="通过次数")
    rejection_count: int = Field(default=0, ge=0, description="拒绝次数")
    last_recomputed_at: datetime | None = Field(default=None, description="最后重算时间")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("feedback_signals")
    @classmethod
    def limit_signals(cls, v: list[TasteSignal]) -> list[TasteSignal]:
        """保留最近 500 条信号，防止无限增长."""
        if len(v) > 500:
            return sorted(v, key=lambda s: s.created_at, reverse=True)[:500]
        return v

    @property
    def approval_rate(self) -> float:
        """计算通过率."""
        total = self.approval_count + self.rejection_count
        if total == 0:
            return 0.0
        return self.approval_count / total

    @property
    def avg_taste_confidence(self) -> float:
        """计算所有 taste vector 的平均置信度."""
        if not self.taste_vectors:
            return 0.0
        return sum(v.confidence for v in self.taste_vectors) / len(self.taste_vectors)

    @property
    def factor_weights(self) -> dict[str, float]:
        """当前阶段的三因素权重."""
        return PHASE_FACTOR_WEIGHTS.get(self.phase, PHASE_FACTOR_WEIGHTS["manual"])

    def get_vector(self, dimension: str) -> TasteVector | None:
        """获取指定维度的口味向量."""
        for v in self.taste_vectors:
            if v.dimension == dimension:
                return v
        return None

    def can_transition(self) -> str | None:
        """检查是否满足阶段升级条件. 返回新阶段或 None."""
        if self.phase == "manual":
            thresholds = PHASE_THRESHOLDS["manual_to_semi_auto"]
            if (
                self.total_feedback_count >= thresholds["min_feedback_count"]
                and self.approval_rate >= thresholds["min_approval_rate"]
                and self.avg_taste_confidence >= thresholds["min_taste_confidence"]
            ):
                return "semi_auto"
        elif self.phase == "semi_auto":
            thresholds = PHASE_THRESHOLDS["semi_auto_to_auto"]
            if (
                self.total_feedback_count >= thresholds["min_feedback_count"]
                and self.approval_rate >= thresholds["min_approval_rate"]
                and self.avg_taste_confidence >= thresholds["min_taste_confidence"]
            ):
                return "auto"
        return None

    model_config = {"json_schema_extra": {"example": {}}}


TasteProfile.model_config["json_schema_extra"]["example"] = {
    "user_id": "default",
    "version": 1,
    "phase": "manual",
    "explicit_preferences": {
        "brand_voice": "专业但不失亲和",
        "tone_prefer": ["真诚", "具体"],
        "tone_avoid": ["太营销"],
        "preferred_length": "short",
        "emoji_style": "light",
        "cta_style": "soft",
    },
    "total_feedback_count": 0,
}
