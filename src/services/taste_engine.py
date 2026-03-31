"""TasteEngine - 用户口味核心引擎.

负责三因素的录入、聚合和输出：
- Factor A: 稿件反馈信号提取
- Factor B: 显式偏好管理
- Factor C: 数据分析洞察（Sprint 4 完善）

核心输出：get_taste_prompt() 生成可注入 LLM 的自然语言口味描述。
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.schemas.taste_profile import (
    AnalyticsInsights,
    ExplicitPreferences,
    PHASE_FACTOR_WEIGHTS,
    TasteProfile,
    TasteSignal,
    TasteVector,
)

logger = logging.getLogger(__name__)


class TasteEngine:
    """用户口味核心引擎."""

    def __init__(self, profile: TasteProfile | None = None):
        self._profile = profile or TasteProfile()

    @property
    def profile(self) -> TasteProfile:
        return self._profile

    # ----------------------------------------------------------------
    # Factor A: 稿件反馈信号提取
    # ----------------------------------------------------------------

    def record_feedback(
        self, draft_id: str, action: str, details: dict[str, Any] | None = None
    ) -> list[TasteSignal]:
        """从用户对稿件的操作中提取 taste 信号.

        Args:
            draft_id: 稿件 ID
            action: approve | reject | edit | comment
            details: 附加信息 (reason, old_content, new_content, comment 等)

        Returns:
            提取的信号列表
        """
        details = details or {}
        signals: list[TasteSignal] = []

        if action == "approve":
            signals = self._signals_from_approval(draft_id, details)
            self._profile.approval_count += 1
        elif action == "reject":
            signals = self._signals_from_rejection(draft_id, details)
            self._profile.rejection_count += 1
        elif action == "edit":
            signals = self._signals_from_edit(draft_id, details)
        elif action == "comment":
            signals = self._signals_from_comment(draft_id, details)

        self._profile.total_feedback_count += 1
        self._profile.feedback_signals.extend(signals)
        self._profile.updated_at = datetime.now()

        # 每次反馈后检查阶段转换
        self._check_phase_transition()

        return signals

    def _signals_from_approval(
        self, draft_id: str, details: dict[str, Any]
    ) -> list[TasteSignal]:
        """通过 = 强化该稿件的风格维度."""
        signals = []
        base = {"source": "feedback", "content_id": draft_id, "weight": 1.0, "confidence": 0.6}

        # 强化标题风格
        if title := details.get("title", ""):
            signals.append(TasteSignal(
                **base, dimension="title_style", signal_type="like", value=title[:40],
            ))

        # 强化整体风格
        if style := details.get("style_notes", ""):
            signals.append(TasteSignal(
                **base, dimension="style", signal_type="like", value=style[:60],
            ))

        # 强化话题
        if topic := details.get("topic", ""):
            signals.append(TasteSignal(
                **base, dimension="topic", signal_type="like", value=topic[:40],
            ))

        # 通用通过信号
        signals.append(TasteSignal(
            **base, dimension="overall", signal_type="like",
            value=details.get("summary", "approved")[:60],
        ))

        return signals

    def _signals_from_rejection(
        self, draft_id: str, details: dict[str, Any]
    ) -> list[TasteSignal]:
        """拒绝 = 创建反偏好信号."""
        signals = []
        reason = details.get("reason", "rejected")
        base = {"source": "feedback", "content_id": draft_id, "weight": 1.0, "confidence": 0.7}

        signals.append(TasteSignal(
            **base, dimension="overall", signal_type="dislike", value=reason[:60],
        ))

        # 如果指明了具体维度
        if dim := details.get("dimension"):
            signals.append(TasteSignal(
                **base, dimension=dim, signal_type="dislike", value=reason[:60],
            ))

        return signals

    def _signals_from_edit(
        self, draft_id: str, details: dict[str, Any]
    ) -> list[TasteSignal]:
        """编辑 = 分析用户改了什么."""
        signals = []
        base = {"source": "feedback", "content_id": draft_id, "weight": 0.8, "confidence": 0.5}

        # 如果提供了编辑摘要
        if summary := details.get("edit_summary", ""):
            signals.append(TasteSignal(
                **base, dimension="edit_pattern", signal_type="like", value=summary[:60],
            ))

        # 如果提供了具体改动维度
        for change in details.get("changes", []):
            dim = change.get("dimension", "style")
            val = change.get("description", "edited")
            signals.append(TasteSignal(
                **base, dimension=dim, signal_type="like", value=val[:60],
            ))

        return signals

    def _signals_from_comment(
        self, draft_id: str, details: dict[str, Any]
    ) -> list[TasteSignal]:
        """评论 = 提取偏好方向."""
        signals = []
        comment = details.get("comment", "")
        if not comment:
            return signals

        sentiment = details.get("sentiment", "neutral")  # positive | negative | neutral
        signal_type = "like" if sentiment == "positive" else "dislike" if sentiment == "negative" else "like"

        signals.append(TasteSignal(
            source="feedback",
            dimension="comment",
            signal_type=signal_type,
            value=comment[:60],
            content_id=draft_id,
            weight=0.6,
            confidence=0.4,
        ))

        return signals

    # ----------------------------------------------------------------
    # Factor B: 显式偏好
    # ----------------------------------------------------------------

    def update_preferences(self, prefs: ExplicitPreferences) -> TasteProfile:
        """直接更新用户显式偏好."""
        self._profile.explicit_preferences = prefs
        self._profile.version += 1
        self._profile.updated_at = datetime.now()
        self.recompute_vectors()
        return self._profile

    # ----------------------------------------------------------------
    # Factor C: 数据分析洞察 (Sprint 4 完善)
    # ----------------------------------------------------------------

    def ingest_analytics(self, insights: AnalyticsInsights) -> list[TasteSignal]:
        """将数据分析洞察转化为 taste 信号."""
        signals = []
        base = {"source": "analytics", "weight": 0.9, "confidence": 0.8}

        for topic in insights.top_performing_topics:
            signals.append(TasteSignal(
                **base, dimension="topic", signal_type="high_perform", value=topic,
            ))

        for structure in insights.top_performing_structures:
            signals.append(TasteSignal(
                **base, dimension="structure", signal_type="high_perform", value=structure,
            ))

        for tone in insights.top_performing_tones:
            signals.append(TasteSignal(
                **base, dimension="tone", signal_type="high_perform", value=tone,
            ))

        self._profile.analytics_insights = insights
        self._profile.feedback_signals.extend(signals)
        self._profile.updated_at = datetime.now()

        self.recompute_vectors()
        return signals

    # ----------------------------------------------------------------
    # 聚合：信号 → 向量
    # ----------------------------------------------------------------

    def recompute_vectors(self) -> list[TasteVector]:
        """聚合所有信号为 taste vectors.

        权重按 phase 调整：
        - manual:    A(50%) + B(40%) + C(10%)
        - semi_auto: A(40%) + B(25%) + C(35%)
        - auto:      A(30%) + B(15%) + C(55%)
        """
        weights = PHASE_FACTOR_WEIGHTS.get(
            self._profile.phase, PHASE_FACTOR_WEIGHTS["manual"]
        )

        # 按维度分组信号
        dim_signals: dict[str, list[TasteSignal]] = defaultdict(list)
        now = datetime.now()

        for signal in self._profile.feedback_signals:
            dim_signals[signal.dimension].append(signal)

        # 注入 Factor B 显式偏好为虚拟信号
        pref_signals = self._preferences_to_signals()
        for signal in pref_signals:
            dim_signals[signal.dimension].append(signal)

        # 聚合每个维度
        vectors = []
        for dim, signals in dim_signals.items():
            prefs: dict[str, float] = defaultdict(float)
            anti_prefs: dict[str, float] = defaultdict(float)
            total_weight = 0.0

            for s in signals:
                factor_weight = weights.get(s.source, 0.3)
                decayed = s.decayed_weight(now)
                effective = decayed * factor_weight * s.confidence

                if s.signal_type in ("like", "high_perform"):
                    prefs[s.value] += effective
                elif s.signal_type in ("dislike", "low_perform"):
                    anti_prefs[s.value] += effective

                total_weight += effective

            # 归一化
            if total_weight > 0:
                max_val = max(
                    max(prefs.values(), default=0),
                    max(anti_prefs.values(), default=0),
                    1.0,
                )
                prefs = {k: min(v / max_val, 1.0) for k, v in prefs.items()}
                anti_prefs = {k: min(v / max_val, 1.0) for k, v in anti_prefs.items()}

            # 置信度 = 信号数量的对数增长，上限 0.95
            sample_count = len(signals)
            import math
            confidence = min(0.95, 0.3 + 0.15 * math.log(1 + sample_count))

            vectors.append(TasteVector(
                dimension=dim,
                preferences=dict(prefs),
                anti_preferences=dict(anti_prefs),
                confidence=round(confidence, 2),
                sample_count=sample_count,
            ))

        self._profile.taste_vectors = vectors
        self._profile.last_recomputed_at = now
        return vectors

    def _preferences_to_signals(self) -> list[TasteSignal]:
        """将显式偏好转化为虚拟信号，参与向量聚合."""
        prefs = self._profile.explicit_preferences
        signals = []
        base = {"source": "preference", "weight": 1.0, "confidence": 0.9}

        for tone in prefs.tone_prefer:
            signals.append(TasteSignal(
                **base, dimension="tone", signal_type="like", value=tone,
            ))
        for tone in prefs.tone_avoid:
            signals.append(TasteSignal(
                **base, dimension="tone", signal_type="dislike", value=tone,
            ))
        for opening in prefs.preferred_openings:
            signals.append(TasteSignal(
                **base, dimension="opening", signal_type="like", value=opening,
            ))

        signals.append(TasteSignal(
            **base, dimension="length", signal_type="like", value=prefs.preferred_length,
        ))
        signals.append(TasteSignal(
            **base, dimension="emoji", signal_type="like", value=prefs.emoji_style,
        ))
        signals.append(TasteSignal(
            **base, dimension="cta", signal_type="like", value=prefs.cta_style,
        ))
        signals.append(TasteSignal(
            **base, dimension="brand_voice", signal_type="like", value=prefs.brand_voice,
        ))

        return signals

    # ----------------------------------------------------------------
    # 输出：生成 LLM prompt
    # ----------------------------------------------------------------

    def get_taste_prompt(self, platform: str = "general") -> str:
        """生成可注入 LLM prompt 的自然语言口味描述."""
        if not self._profile.taste_vectors:
            self.recompute_vectors()

        sections = []

        # 风格偏好
        style_lines = []
        for vec in self._profile.taste_vectors:
            if vec.sample_count == 0:
                continue
            top_prefs = vec.top_preferences(3)
            top_anti = vec.top_anti_preferences(3)
            if top_prefs:
                pref_str = ", ".join(f"{v}" for v, _ in top_prefs)
                style_lines.append(
                    f"- {vec.dimension}偏好：{pref_str} "
                    f"(置信度: {vec.confidence:.0%}, 基于{vec.sample_count}条信号)"
                )
            if top_anti:
                anti_str = ", ".join(f"{v}" for v, _ in top_anti)
                style_lines.append(f"- {vec.dimension}避免：{anti_str}")

        if style_lines:
            sections.append(
                f"### 风格偏好 (整体置信度: {self._profile.avg_taste_confidence:.0%})\n"
                + "\n".join(style_lines)
            )

        # 显式偏好摘要
        prefs = self._profile.explicit_preferences
        pref_lines = [
            f"- 品牌调性：{prefs.brand_voice}",
            f"- 文章长度：{prefs.preferred_length}",
            f"- emoji风格：{prefs.emoji_style}",
            f"- CTA风格：{prefs.cta_style}",
        ]
        sections.append("### 用户设定\n" + "\n".join(pref_lines))

        # 数据洞察（如果有）
        insights = self._profile.analytics_insights
        if insights.top_performing_topics:
            data_lines = [
                f"- 高表现话题：{', '.join(insights.top_performing_topics[:5])}",
            ]
            if insights.top_performing_structures:
                data_lines.append(
                    f"- 高表现结构：{', '.join(insights.top_performing_structures[:3])}"
                )
            sections.append("### 数据验证\n" + "\n".join(data_lines))

        # 平台特定覆盖
        if platform != "general" and platform in prefs.platform_overrides:
            override = prefs.platform_overrides[platform]
            override_lines = [f"- {k}: {v}" for k, v in override.items()]
            sections.append(f"### {platform}平台特定\n" + "\n".join(override_lines))

        # 近期反馈摘要
        recent = self._profile.feedback_signals[-10:]
        if recent:
            likes = [s.value for s in recent if s.signal_type == "like"][:3]
            dislikes = [s.value for s in recent if s.signal_type == "dislike"][:3]
            feedback_lines = []
            if likes:
                feedback_lines.append(f"- 近期正向：{', '.join(likes)}")
            if dislikes:
                feedback_lines.append(f"- 近期负向：{', '.join(dislikes)}")
            if feedback_lines:
                sections.append("### 近期反馈\n" + "\n".join(feedback_lines))

        return "\n\n".join(sections)

    # ----------------------------------------------------------------
    # 阶段转换
    # ----------------------------------------------------------------

    def _check_phase_transition(self) -> str | None:
        """检查并执行阶段转换."""
        new_phase = self._profile.can_transition()
        if new_phase:
            old_phase = self._profile.phase
            self._profile.phase = new_phase
            self._profile.version += 1
            logger.info(f"Taste phase transition: {old_phase} -> {new_phase}")
            self.recompute_vectors()
        return new_phase

    def should_require_human_review(self, score: float) -> bool:
        """根据当前阶段和评分决定是否需要人工审核."""
        phase = self._profile.phase
        if phase == "manual":
            return True
        elif phase == "semi_auto":
            return score < 85
        else:  # auto
            return score < 70
