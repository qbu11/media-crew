"""Tests for taste profile schema and DB models."""

import math
from datetime import datetime, timedelta

import pytest

from src.schemas.taste_profile import (
    AnalyticsInsights,
    CompetitorBenchmark,
    ExplicitPreferences,
    PHASE_FACTOR_WEIGHTS,
    PHASE_THRESHOLDS,
    TasteProfile,
    TasteSignal,
    TasteVector,
)


class TestTasteSignal:
    """TasteSignal 模型测试."""

    def test_create_basic_signal(self):
        signal = TasteSignal(
            source="feedback",
            dimension="tone",
            signal_type="like",
            value="真诚",
        )
        assert signal.source == "feedback"
        assert signal.dimension == "tone"
        assert signal.signal_type == "like"
        assert signal.value == "真诚"
        assert signal.weight == 1.0
        assert signal.confidence == 0.5
        assert signal.content_id is None

    def test_signal_with_content_id(self):
        signal = TasteSignal(
            source="analytics",
            dimension="topic",
            signal_type="high_perform",
            value="AI创业",
            content_id="draft-001",
        )
        assert signal.content_id == "draft-001"
        assert signal.source == "analytics"

    def test_decayed_weight_no_decay(self):
        """刚创建的信号，衰减权重应接近原始权重."""
        signal = TasteSignal(
            source="feedback",
            dimension="tone",
            signal_type="like",
            value="真诚",
            weight=1.0,
        )
        decayed = signal.decayed_weight()
        assert decayed > 0.99  # 几乎无衰减

    def test_decayed_weight_after_30_days(self):
        """30天后权重应降至约22%."""
        signal = TasteSignal(
            source="feedback",
            dimension="tone",
            signal_type="like",
            value="真诚",
            weight=1.0,
            created_at=datetime.now() - timedelta(days=30),
        )
        decayed = signal.decayed_weight()
        expected = math.exp(-0.05 * 30)  # ~0.223
        assert abs(decayed - expected) < 0.01

    def test_decayed_weight_after_60_days(self):
        """60天后权重应降至约5%."""
        signal = TasteSignal(
            source="feedback",
            dimension="tone",
            signal_type="like",
            value="真诚",
            weight=1.0,
            created_at=datetime.now() - timedelta(days=60),
        )
        decayed = signal.decayed_weight()
        assert decayed < 0.06

    def test_invalid_source_rejected(self):
        with pytest.raises(Exception):
            TasteSignal(
                source="invalid",
                dimension="tone",
                signal_type="like",
                value="真诚",
            )

    def test_weight_bounds(self):
        with pytest.raises(Exception):
            TasteSignal(
                source="feedback",
                dimension="tone",
                signal_type="like",
                value="真诚",
                weight=1.5,
            )


class TestExplicitPreferences:
    """ExplicitPreferences 模型测试."""

    def test_defaults(self):
        prefs = ExplicitPreferences()
        assert prefs.brand_voice == "专业但不失亲和"
        assert "真诚" in prefs.tone_prefer
        assert "太营销" in prefs.tone_avoid
        assert prefs.preferred_length == "short"
        assert prefs.emoji_style == "light"
        assert prefs.cta_style == "soft"

    def test_custom_preferences(self):
        prefs = ExplicitPreferences(
            brand_voice="轻松幽默",
            tone_prefer=["搞笑", "接地气"],
            tone_avoid=["严肃"],
            preferred_length="medium",
            emoji_style="heavy",
        )
        assert prefs.brand_voice == "轻松幽默"
        assert prefs.preferred_length == "medium"
        assert prefs.emoji_style == "heavy"

    def test_platform_overrides(self):
        prefs = ExplicitPreferences(
            platform_overrides={
                "xiaohongshu": {"preferred_length": "short", "emoji_style": "heavy"},
                "zhihu": {"preferred_length": "long", "emoji_style": "none"},
            }
        )
        assert "xiaohongshu" in prefs.platform_overrides
        assert prefs.platform_overrides["zhihu"]["preferred_length"] == "long"

    def test_invalid_length_rejected(self):
        with pytest.raises(Exception):
            ExplicitPreferences(preferred_length="extra_long")


class TestCompetitorBenchmark:
    """CompetitorBenchmark 模型测试."""

    def test_create_benchmark(self):
        bm = CompetitorBenchmark(
            competitor_name="竞品A",
            platform="xiaohongshu",
            avg_likes=5000.0,
            avg_comments=200.0,
            top_content_patterns=["痛点开场", "案例驱动"],
            our_percentile=65.0,
        )
        assert bm.competitor_name == "竞品A"
        assert bm.our_percentile == 65.0


class TestAnalyticsInsights:
    """AnalyticsInsights 模型测试."""

    def test_defaults(self):
        insights = AnalyticsInsights()
        assert insights.top_performing_topics == []
        assert insights.competitor_benchmarks == []
        assert insights.last_analyzed_at is None

    def test_with_data(self):
        insights = AnalyticsInsights(
            top_performing_topics=["AI创业", "效率工具"],
            avg_engagement_by_topic={"AI创业": 0.08, "效率工具": 0.05},
            last_analyzed_at=datetime.now(),
        )
        assert len(insights.top_performing_topics) == 2
        assert insights.avg_engagement_by_topic["AI创业"] == 0.08


class TestTasteVector:
    """TasteVector 模型测试."""

    def test_create_vector(self):
        vec = TasteVector(
            dimension="tone",
            preferences={"真诚": 0.9, "具体": 0.7, "专业": 0.5},
            anti_preferences={"太营销": 0.8, "太官话": 0.6},
            confidence=0.85,
            sample_count=15,
        )
        assert vec.dimension == "tone"
        assert vec.confidence == 0.85

    def test_top_preferences(self):
        vec = TasteVector(
            dimension="tone",
            preferences={"真诚": 0.9, "具体": 0.7, "专业": 0.5, "幽默": 0.3},
            confidence=0.8,
            sample_count=10,
        )
        top = vec.top_preferences(2)
        assert len(top) == 2
        assert top[0] == ("真诚", 0.9)
        assert top[1] == ("具体", 0.7)

    def test_top_anti_preferences(self):
        vec = TasteVector(
            dimension="tone",
            anti_preferences={"太营销": 0.8, "太官话": 0.6, "太模板": 0.3},
            confidence=0.7,
            sample_count=8,
        )
        top = vec.top_anti_preferences(2)
        assert len(top) == 2
        assert top[0] == ("太营销", 0.8)

    def test_empty_preferences(self):
        vec = TasteVector(dimension="topic", confidence=0.0, sample_count=0)
        assert vec.top_preferences() == []
        assert vec.top_anti_preferences() == []


class TestTasteProfile:
    """TasteProfile 完整模型测试."""

    def test_default_profile(self):
        profile = TasteProfile()
        assert profile.user_id == "default"
        assert profile.version == 1
        assert profile.phase == "manual"
        assert profile.total_feedback_count == 0
        assert profile.approval_rate == 0.0
        assert profile.avg_taste_confidence == 0.0

    def test_approval_rate(self):
        profile = TasteProfile(approval_count=7, rejection_count=3)
        assert profile.approval_rate == 0.7

    def test_approval_rate_zero_division(self):
        profile = TasteProfile(approval_count=0, rejection_count=0)
        assert profile.approval_rate == 0.0

    def test_avg_taste_confidence(self):
        profile = TasteProfile(
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.8, sample_count=10),
                TasteVector(dimension="structure", confidence=0.6, sample_count=5),
            ]
        )
        assert profile.avg_taste_confidence == pytest.approx(0.7)

    def test_factor_weights_manual(self):
        profile = TasteProfile(phase="manual")
        weights = profile.factor_weights
        assert weights["feedback"] == 0.50
        assert weights["preference"] == 0.40
        assert weights["analytics"] == 0.10

    def test_factor_weights_semi_auto(self):
        profile = TasteProfile(phase="semi_auto")
        weights = profile.factor_weights
        assert weights["feedback"] == 0.40
        assert weights["preference"] == 0.25
        assert weights["analytics"] == 0.35

    def test_factor_weights_auto(self):
        profile = TasteProfile(phase="auto")
        weights = profile.factor_weights
        assert weights["feedback"] == 0.30
        assert weights["preference"] == 0.15
        assert weights["analytics"] == 0.55

    def test_get_vector(self):
        profile = TasteProfile(
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.8, sample_count=10),
                TasteVector(dimension="structure", confidence=0.6, sample_count=5),
            ]
        )
        tone = profile.get_vector("tone")
        assert tone is not None
        assert tone.confidence == 0.8

        missing = profile.get_vector("nonexistent")
        assert missing is None

    def test_can_transition_manual_to_semi_auto(self):
        profile = TasteProfile(
            phase="manual",
            total_feedback_count=25,
            approval_count=18,
            rejection_count=7,
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.8, sample_count=15),
                TasteVector(dimension="structure", confidence=0.7, sample_count=10),
            ],
        )
        assert profile.can_transition() == "semi_auto"

    def test_cannot_transition_insufficient_feedback(self):
        profile = TasteProfile(
            phase="manual",
            total_feedback_count=10,  # < 20
            approval_count=8,
            rejection_count=2,
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.8, sample_count=10),
            ],
        )
        assert profile.can_transition() is None

    def test_cannot_transition_low_approval_rate(self):
        profile = TasteProfile(
            phase="manual",
            total_feedback_count=25,
            approval_count=10,
            rejection_count=15,  # 40% approval rate < 60%
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.8, sample_count=15),
            ],
        )
        assert profile.can_transition() is None

    def test_can_transition_semi_auto_to_auto(self):
        profile = TasteProfile(
            phase="semi_auto",
            total_feedback_count=55,
            approval_count=46,
            rejection_count=9,  # ~84% approval
            taste_vectors=[
                TasteVector(dimension="tone", confidence=0.9, sample_count=30),
                TasteVector(dimension="structure", confidence=0.85, sample_count=25),
            ],
        )
        assert profile.can_transition() == "auto"

    def test_auto_phase_no_transition(self):
        profile = TasteProfile(phase="auto", total_feedback_count=100)
        assert profile.can_transition() is None

    def test_signal_limit_500(self):
        """超过500条信号时应截断."""
        signals = [
            TasteSignal(
                source="feedback",
                dimension="tone",
                signal_type="like",
                value=f"value_{i}",
                created_at=datetime.now() - timedelta(days=i),
            )
            for i in range(600)
        ]
        profile = TasteProfile(feedback_signals=signals)
        assert len(profile.feedback_signals) == 500
        # 应保留最新的
        assert profile.feedback_signals[0].value == "value_0"

    def test_serialization_roundtrip(self):
        """JSON 序列化/反序列化."""
        profile = TasteProfile(
            user_id="test_user",
            explicit_preferences=ExplicitPreferences(brand_voice="轻松"),
            taste_vectors=[
                TasteVector(
                    dimension="tone",
                    preferences={"真诚": 0.9},
                    confidence=0.8,
                    sample_count=10,
                ),
            ],
        )
        json_str = profile.model_dump_json()
        restored = TasteProfile.model_validate_json(json_str)
        assert restored.user_id == "test_user"
        assert restored.explicit_preferences.brand_voice == "轻松"
        assert len(restored.taste_vectors) == 1
        assert restored.taste_vectors[0].preferences["真诚"] == 0.9


class TestTasteProfileDB:
    """Taste DB 模型基础测试."""

    def test_import(self):
        from src.models.taste import TasteFeedbackLog, TasteProfileDB

        assert TasteProfileDB.__tablename__ == "taste_profiles"
        assert TasteFeedbackLog.__tablename__ == "taste_feedback_logs"

    def test_repr(self):
        from src.models.taste import TasteProfileDB

        p = TasteProfileDB()
        p.user_id = "test"
        p.phase = "manual"
        p.version = 1
        assert "test" in repr(p)
        assert "manual" in repr(p)


class TestPhaseConstants:
    """阶段常量测试."""

    def test_phase_thresholds_exist(self):
        assert "manual_to_semi_auto" in PHASE_THRESHOLDS
        assert "semi_auto_to_auto" in PHASE_THRESHOLDS

    def test_phase_factor_weights_sum_to_one(self):
        for phase, weights in PHASE_FACTOR_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, f"Phase {phase} weights sum to {total}"

    def test_all_phases_have_weights(self):
        for phase in ["manual", "semi_auto", "auto"]:
            assert phase in PHASE_FACTOR_WEIGHTS
            weights = PHASE_FACTOR_WEIGHTS[phase]
            assert "feedback" in weights
            assert "preference" in weights
            assert "analytics" in weights
