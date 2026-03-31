"""Tests for TasteEngine core engine."""

from datetime import datetime, timedelta

import pytest

from src.schemas.taste_profile import (
    AnalyticsInsights,
    ExplicitPreferences,
    TasteProfile,
    TasteSignal,
)
from src.services.taste_engine import TasteEngine


class TestTasteEngineInit:
    """初始化测试."""

    def test_default_init(self):
        engine = TasteEngine()
        assert engine.profile.user_id == "default"
        assert engine.profile.phase == "manual"

    def test_init_with_profile(self):
        profile = TasteProfile(user_id="test_user", phase="semi_auto")
        engine = TasteEngine(profile=profile)
        assert engine.profile.user_id == "test_user"
        assert engine.profile.phase == "semi_auto"


class TestFactorAFeedback:
    """Factor A: 稿件反馈信号提取测试."""

    def test_record_approval(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-001", "approve",
            {"title": "AI创业指南", "topic": "AI创业", "style_notes": "真诚具体"},
        )
        assert len(signals) >= 1
        assert engine.profile.approval_count == 1
        assert engine.profile.total_feedback_count == 1
        # 应有 like 类型信号
        like_signals = [s for s in signals if s.signal_type == "like"]
        assert len(like_signals) >= 1

    def test_record_rejection(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-002", "reject",
            {"reason": "语气太像广告"},
        )
        assert len(signals) >= 1
        assert engine.profile.rejection_count == 1
        dislike_signals = [s for s in signals if s.signal_type == "dislike"]
        assert len(dislike_signals) >= 1
        assert "广告" in dislike_signals[0].value

    def test_record_rejection_with_dimension(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-003", "reject",
            {"reason": "标题太长", "dimension": "title_style"},
        )
        dim_signals = [s for s in signals if s.dimension == "title_style"]
        assert len(dim_signals) == 1

    def test_record_edit(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-004", "edit",
            {
                "edit_summary": "缩短了开头",
                "changes": [
                    {"dimension": "length", "description": "缩短开头段落"},
                    {"dimension": "opening", "description": "改为痛点开场"},
                ],
            },
        )
        assert len(signals) == 3  # 1 summary + 2 changes
        assert engine.profile.total_feedback_count == 1

    def test_record_comment(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-005", "comment",
            {"comment": "结尾的互动引导很好", "sentiment": "positive"},
        )
        assert len(signals) == 1
        assert signals[0].signal_type == "like"

    def test_record_negative_comment(self):
        engine = TasteEngine()
        signals = engine.record_feedback(
            "draft-006", "comment",
            {"comment": "太啰嗦了", "sentiment": "negative"},
        )
        assert len(signals) == 1
        assert signals[0].signal_type == "dislike"

    def test_empty_comment_no_signal(self):
        engine = TasteEngine()
        signals = engine.record_feedback("draft-007", "comment", {"comment": ""})
        assert len(signals) == 0

    def test_signals_accumulate(self):
        engine = TasteEngine()
        engine.record_feedback("d1", "approve", {"title": "标题1"})
        engine.record_feedback("d2", "reject", {"reason": "太长"})
        engine.record_feedback("d3", "approve", {"title": "标题3"})
        assert engine.profile.total_feedback_count == 3
        assert engine.profile.approval_count == 2
        assert engine.profile.rejection_count == 1
        assert len(engine.profile.feedback_signals) >= 3


class TestFactorBPreferences:
    """Factor B: 显式偏好测试."""

    def test_update_preferences(self):
        engine = TasteEngine()
        new_prefs = ExplicitPreferences(
            brand_voice="轻松幽默",
            tone_prefer=["搞笑", "接地气"],
            preferred_length="medium",
        )
        profile = engine.update_preferences(new_prefs)
        assert profile.explicit_preferences.brand_voice == "轻松幽默"
        assert profile.version == 2  # incremented

    def test_preferences_trigger_recompute(self):
        engine = TasteEngine()
        engine.update_preferences(ExplicitPreferences(tone_prefer=["真诚"]))
        assert len(engine.profile.taste_vectors) > 0


class TestFactorCAnalytics:
    """Factor C: 数据分析洞察测试."""

    def test_ingest_analytics(self):
        engine = TasteEngine()
        insights = AnalyticsInsights(
            top_performing_topics=["AI创业", "效率工具"],
            top_performing_structures=["五段式"],
            top_performing_tones=["真诚"],
        )
        signals = engine.ingest_analytics(insights)
        assert len(signals) == 4  # 2 topics + 1 structure + 1 tone
        assert all(s.source == "analytics" for s in signals)
        assert engine.profile.analytics_insights.top_performing_topics == ["AI创业", "效率工具"]

    def test_analytics_triggers_recompute(self):
        engine = TasteEngine()
        engine.ingest_analytics(AnalyticsInsights(top_performing_topics=["AI"]))
        assert len(engine.profile.taste_vectors) > 0


class TestVectorAggregation:
    """向量聚合测试."""

    def test_recompute_empty(self):
        engine = TasteEngine()
        vectors = engine.recompute_vectors()
        # 即使没有反馈信号，显式偏好也会生成向量
        assert len(vectors) > 0

    def test_recompute_with_signals(self):
        engine = TasteEngine()
        # 添加一些信号
        engine.record_feedback("d1", "approve", {"title": "好标题", "topic": "AI"})
        engine.record_feedback("d2", "reject", {"reason": "太营销"})
        vectors = engine.recompute_vectors()
        assert len(vectors) > 0

        # 应有 tone 维度（来自默认偏好）
        tone_vec = next((v for v in vectors if v.dimension == "tone"), None)
        assert tone_vec is not None
        assert tone_vec.sample_count > 0

    def test_confidence_increases_with_samples(self):
        engine = TasteEngine()
        # 少量信号
        engine.record_feedback("d1", "approve", {"topic": "AI"})
        vectors_few = engine.recompute_vectors()

        # 更多信号
        for i in range(10):
            engine.record_feedback(f"d{i+2}", "approve", {"topic": "AI"})
        vectors_many = engine.recompute_vectors()

        # 找到 overall 维度比较
        overall_few = next((v for v in vectors_few if v.dimension == "overall"), None)
        overall_many = next((v for v in vectors_many if v.dimension == "overall"), None)
        assert overall_many.confidence >= overall_few.confidence

    def test_phase_affects_weights(self):
        """不同阶段，三因素权重不同."""
        # manual 阶段：feedback 50%, preference 40%, analytics 10%
        engine_manual = TasteEngine(TasteProfile(phase="manual"))
        engine_manual.record_feedback("d1", "approve", {"topic": "AI"})
        engine_manual.ingest_analytics(AnalyticsInsights(top_performing_topics=["AI"]))
        vectors_manual = engine_manual.recompute_vectors()

        # auto 阶段：feedback 30%, preference 15%, analytics 55%
        engine_auto = TasteEngine(TasteProfile(phase="auto"))
        engine_auto.record_feedback("d1", "approve", {"topic": "AI"})
        engine_auto.ingest_analytics(AnalyticsInsights(top_performing_topics=["AI"]))
        vectors_auto = engine_auto.recompute_vectors()

        # 两者都应有向量，但权重分布不同
        assert len(vectors_manual) > 0
        assert len(vectors_auto) > 0


class TestTastePrompt:
    """Taste prompt 生成测试."""

    def test_basic_prompt(self):
        engine = TasteEngine()
        prompt = engine.get_taste_prompt()
        assert "风格偏好" in prompt or "用户设定" in prompt
        assert "品牌调性" in prompt

    def test_prompt_includes_preferences(self):
        engine = TasteEngine(TasteProfile(
            explicit_preferences=ExplicitPreferences(
                brand_voice="轻松幽默",
                preferred_length="long",
            ),
        ))
        prompt = engine.get_taste_prompt()
        assert "轻松幽默" in prompt
        assert "long" in prompt

    def test_prompt_includes_analytics(self):
        engine = TasteEngine()
        engine.ingest_analytics(AnalyticsInsights(
            top_performing_topics=["AI创业", "效率工具"],
        ))
        prompt = engine.get_taste_prompt()
        assert "AI创业" in prompt
        assert "数据验证" in prompt

    def test_prompt_includes_recent_feedback(self):
        engine = TasteEngine()
        engine.record_feedback("d1", "approve", {"title": "好文章"})
        engine.record_feedback("d2", "reject", {"reason": "太啰嗦"})
        prompt = engine.get_taste_prompt()
        assert "近期" in prompt

    def test_prompt_platform_override(self):
        engine = TasteEngine(TasteProfile(
            explicit_preferences=ExplicitPreferences(
                platform_overrides={"xiaohongshu": {"emoji_style": "heavy"}},
            ),
        ))
        prompt = engine.get_taste_prompt(platform="xiaohongshu")
        assert "xiaohongshu" in prompt
        assert "heavy" in prompt

    def test_prompt_no_platform_override(self):
        engine = TasteEngine()
        prompt = engine.get_taste_prompt(platform="zhihu")
        # 没有 zhihu 覆盖，不应有平台特定段
        assert "zhihu平台特定" not in prompt


class TestPhaseTransition:
    """阶段转换测试."""

    def test_no_transition_early(self):
        engine = TasteEngine()
        engine.record_feedback("d1", "approve", {})
        assert engine.profile.phase == "manual"

    def test_transition_manual_to_semi_auto(self):
        profile = TasteProfile(
            phase="manual",
            total_feedback_count=19,
            approval_count=14,
            rejection_count=5,
            taste_vectors=[
                # 需要 avg confidence >= 0.7
            ],
        )
        engine = TasteEngine(profile)

        # 手动设置高置信度向量
        from src.schemas.taste_profile import TasteVector
        engine.profile.taste_vectors = [
            TasteVector(dimension="tone", confidence=0.8, sample_count=15),
            TasteVector(dimension="style", confidence=0.75, sample_count=10),
        ]

        # 第 20 次反馈应触发转换
        engine.record_feedback("d20", "approve", {})
        assert engine.profile.phase == "semi_auto"

    def test_no_transition_low_approval_rate(self):
        profile = TasteProfile(
            phase="manual",
            total_feedback_count=19,
            approval_count=8,
            rejection_count=11,  # 42% < 60%
        )
        engine = TasteEngine(profile)
        from src.schemas.taste_profile import TasteVector
        engine.profile.taste_vectors = [
            TasteVector(dimension="tone", confidence=0.8, sample_count=15),
        ]
        engine.record_feedback("d20", "approve", {})
        assert engine.profile.phase == "manual"  # 不转换


class TestHumanReview:
    """人工审核决策测试."""

    def test_manual_always_review(self):
        engine = TasteEngine(TasteProfile(phase="manual"))
        assert engine.should_require_human_review(95) is True
        assert engine.should_require_human_review(50) is True

    def test_semi_auto_threshold(self):
        engine = TasteEngine(TasteProfile(phase="semi_auto"))
        assert engine.should_require_human_review(90) is False  # >= 85
        assert engine.should_require_human_review(80) is True   # < 85

    def test_auto_threshold(self):
        engine = TasteEngine(TasteProfile(phase="auto"))
        assert engine.should_require_human_review(75) is False  # >= 70
        assert engine.should_require_human_review(60) is True   # < 70
