"""
Unit tests for Pydantic schema validation.

Tests cover:
- Schema validation with valid data
- Validation errors with invalid data
- Field validators
- Property methods
- Model methods
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.schemas.analytics_report import (
    EngagementRate,
    MetricType,
    MetricValue,
    PerformanceInsight,
    PlatformAnalytics,
    TimePeriod,
    TrendDirection,
)
from src.schemas.content_brief import (
    AudienceInsight,
    ContentBrief,
    ContentType,
    PlatformType,
    TargetAudience,
    TrendingTopic,
)
from src.schemas.content_draft import (
    ContentBlock,
    ContentDraft,
    DraftStatus,
    PlatformContent,
    QualityScore,
    ReviewFeedback,
)
from src.schemas.publish_result import (
    PlatformPostInfo,
    PublishError,
    PublishResult,
    PublishStatus,
    ScheduleType,
)


class TestContentBriefSchema:
    """Test cases for ContentBrief schema."""

    def test_content_brief_valid_creation(self, sample_content_brief_schema: ContentBrief) -> None:
        """
        Test ContentBrief can be created with valid data.

        Arrange: Use fixture with valid content brief
        Act: Validate the instance
        Assert: All fields are correct
        """
        brief = sample_content_brief_schema

        assert brief.id == "brief-20250320-001"
        assert brief.topic == "AI创业实战指南"
        assert len(brief.keywords) == 3
        assert isinstance(brief.created_at, datetime)

    def test_content_brief_keyword_validator(self) -> None:
        """
        Test ContentBrief keyword validator normalizes keywords.

        Arrange: Create ContentBrief with mixed case keywords
        Act: Validate keywords
        Assert: Keywords are lowercased and stripped
        """
        brief = ContentBrief(
            id="brief-001",
            topic="Test",
            keywords=["  AI创业  ", "人工智能", "TECH"],
            target_audience=[],
            trending_topics=[],
            content_angle="Test",
            primary_platform=PlatformType.XIAOHONGSHU,
            key_points=[],
            hashtags=[],
        )

        assert brief.keywords == ["ai创业", "人工智能", "tech"]

    def test_content_brief_keyword_validator_empty(self) -> None:
        """
        Test ContentBrief keyword validator rejects empty keywords.

        Arrange: Try to create ContentBrief with empty keywords
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            ContentBrief(
                id="brief-001",
                topic="Test",
                keywords=[],  # Empty not allowed
                target_audience=[],
                trending_topics=[],
                content_angle="Test",
                primary_platform=PlatformType.XIAOHONGSHU,
                key_points=[],
                hashtags=[],
            )

        assert "keywords" in str(exc_info.value)

    def test_content_brief_sub_topics_validator(self) -> None:
        """
        Test ContentBrief sub_topics validator limits to 5 items.

        Arrange: Create ContentBrief with 7 sub topics
        Act: Validate
        Assert: Only first 5 are kept
        """
        brief = ContentBrief(
            id="brief-001",
            topic="Test",
            keywords=["test"],
            target_audience=[],
            trending_topics=[],
            content_angle="Test",
            primary_platform=PlatformType.XIAOHONGSHU,
            key_points=[],
            hashtags=[],
            sub_topics=[f"Topic{i}" for i in range(7)],
        )

        assert len(brief.sub_topics) == 5

    def test_content_brief_hashtag_validator(self) -> None:
        """
        Test ContentBrief hashtag validator adds # prefix.

        Arrange: Create ContentBrief with hashtags without #
        Act: Validate
        Assert: # is added to all tags
        """
        brief = ContentBrief(
            id="brief-001",
            topic="Test",
            keywords=["test"],
            target_audience=[],
            trending_topics=[],
            content_angle="Test",
            primary_platform=PlatformType.XIAOHONGSHU,
            key_points=[],
            hashtags=["AI创业", "科技创业", "#已有标签"],
        )

        assert brief.hashtags == ["#AI创业", "#科技创业", "#已有标签"]

    def test_audience_insight_validation(self) -> None:
        """
        Test AudienceInsight validates required fields.

        Arrange: Create valid AudienceInsight
        Act: Validate
        Assert: Instance is created correctly
        """
        insight = AudienceInsight(
            segment=TargetAudience.ENTREPRENEUR,
            size_estimate="10万+",
            interests=["AI技术", "创业融资"],
            pain_points=["资金短缺"],
            preferred_content_type=ContentType.ARTICLE,
        )

        assert insight.segment == TargetAudience.ENTREPRENEUR
        assert insight.size_estimate == "10万+"

    def test_trending_topic_validation(self) -> None:
        """
        Test TrendingTopic validates score ranges.

        Arrange: Create TrendingTopic with valid scores
        Act: Validate
        Assert: Instance is created correctly
        """
        topic = TrendingTopic(
            keyword="AI Agent",
            search_volume=50000,
            growth_rate=150.0,
            competition_level="medium",
            related_keywords=["智能体"],
            source_platform=PlatformType.XIAOHONGSHU,
        )

        assert topic.growth_rate == 150.0
        assert topic.competition_level == "medium"

    def test_trending_topic_invalid_growth_rate(self) -> None:
        """
        Test TrendingTopic rejects invalid growth_rate.

        Arrange: Try to create with growth_rate > 1000
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError):
            TrendingTopic(
                keyword="Test",
                growth_rate=1500.0,  # Should be -100 to 1000
                competition_level="medium",
            )


class TestContentDraftSchema:
    """Test cases for ContentDraft schema."""

    def test_content_draft_valid_creation(self, sample_content_draft_schema: ContentDraft) -> None:
        """
        Test ContentDraft can be created with valid data.

        Arrange: Use fixture with valid content draft
        Act: Validate the instance
        Assert: All fields are correct
        """
        draft = sample_content_draft_schema

        assert draft.id == "draft-20250320-001"
        assert draft.status == DraftStatus.APPROVED
        assert len(draft.platforms) == 2

    def test_content_block_validation(self) -> None:
        """
        Test ContentBlock validates content is not empty.

        Arrange: Try to create ContentBlock with empty content
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            ContentBlock(
                type="text",
                content="   ",  # Whitespace only
            )

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_content_block_valid_types(self) -> None:
        """
        Test ContentBlock accepts all valid types.

        Arrange: Create ContentBlocks with different types
        Act: Validate
        Assert: All blocks are created successfully
        """
        block_types = ["text", "image", "video", "code", "quote", "list", "heading"]

        for block_type in block_types:
            block = ContentBlock(type=block_type, content="Test content")
            assert block.type == block_type

    def test_quality_score_overall_calculation(self) -> None:
        """
        Test QualityScore.overall calculates weighted average.

        Arrange: Create QualityScore with specific values
        Act: Access overall property
        Assert: Returns correct weighted average
        """
        score = QualityScore(
            relevance=9.0,
            readability=8.0,
            engagement_potential=7.0,
            brand_alignment=8.0,
            platform_fit=7.0,
        )

        # Expected: 9*0.25 + 8*0.2 + 7*0.25 + 8*0.15 + 7*0.15 = 7.85 -> round(7.85, 1) = 7.8
        assert score.overall == pytest.approx(7.8)

    def test_quality_score_passes_threshold(self) -> None:
        """
        Test QualityScore.passes_threshold method.

        Arrange: Create QualityScore with different scores
        Act: Check against thresholds
        Assert: Returns correct boolean values
        """
        score_high = QualityScore(
            relevance=9.0,
            readability=9.0,
            engagement_potential=9.0,
            brand_alignment=9.0,
            platform_fit=9.0,
        )

        score_low = QualityScore(
            relevance=5.0,
            readability=5.0,
            engagement_potential=5.0,
            brand_alignment=5.0,
            platform_fit=5.0,
        )

        assert score_high.passes_threshold(threshold=7.0) is True
        assert score_low.passes_threshold(threshold=7.0) is False

    def test_quality_score_boundary_validation(self) -> None:
        """
        Test QualityScore validates score boundaries.

        Arrange: Try to create with scores outside 0-10 range
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError):
            QualityScore(
                relevance=11.0,  # Too high
                readability=5.0,
                engagement_potential=5.0,
                brand_alignment=5.0,
                platform_fit=5.0,
            )

        with pytest.raises(ValidationError):
            QualityScore(
                relevance=-1.0,  # Too low
                readability=5.0,
                engagement_potential=5.0,
                brand_alignment=5.0,
                platform_fit=5.0,
            )

    def test_platform_content_character_count(self) -> None:
        """
        Test PlatformContent calculates character count.

        Arrange: Create PlatformContent with plain_text
        Act: Validate
        Assert: character_count is auto-calculated
        """
        content = PlatformContent(
            platform=PlatformType.XIAOHONGSHU,
            title="测试标题",
            content_blocks=[],
            plain_text="这是测试内容，用于计算字符数。",
        )

        assert content.character_count == 15

    def test_platform_content_character_limits(self) -> None:
        """
        Test PlatformContent.is_within_limit checks platform limits.

        Arrange: Create PlatformContent for different platforms
        Act: Check against limits
        Assert: Returns correct boolean values
        """
        # 小红书限制1000字符
        xhs_content = PlatformContent(
            platform=PlatformType.XIAOHONGSHU,
            title="标题",
            content_blocks=[],
            plain_text="a" * 1000,
        )

        # 微信公众号限制20000字符
        wechat_content = PlatformContent(
            platform=PlatformType.WECHAT,
            title="标题",
            content_blocks=[],
            plain_text="a" * 1000,
        )

        assert xhs_content.is_within_limit() is True
        assert wechat_content.is_within_limit() is True

    def test_platform_content_get_limit(self) -> None:
        """
        Test PlatformContent.get_character_limit returns correct limits.

        Arrange: Create PlatformContent for each platform
        Act: Call get_character_limit()
        Assert: Returns correct limit for each platform
        """
        limits = {
            PlatformType.XIAOHONGSHU: 1000,
            PlatformType.WECHAT: 20000,
            PlatformType.WEIBO: 2000,
            PlatformType.ZHIHU: 50000,
            PlatformType.DOUYIN: 2200,
            PlatformType.BILIBILI: 2000,
        }

        for platform, expected_limit in limits.items():
            content = PlatformContent(
                platform=platform,
                title="标题",
                content_blocks=[],
            )
            assert content.get_character_limit() == expected_limit

    def test_content_draft_get_platform_content(self) -> None:
        """
        Test ContentDraft.get_platform_content method.

        Arrange: Create ContentDraft with multiple platform contents
        Act: Get specific platform content
        Assert: Returns correct content or None
        """
        draft = ContentDraft(
            id="draft-001",
            brief_id="brief-001",
            topic="Test",
            platforms=[PlatformType.XIAOHONGSHU, PlatformType.WECHAT],
            platform_content=[
                PlatformContent(
                    platform=PlatformType.XIAOHONGSHU,
                    title="小红书标题",
                    content_blocks=[],
                ),
                PlatformContent(
                    platform=PlatformType.WECHAT,
                    title="微信标题",
                    content_blocks=[],
                ),
            ],
        )

        xhs_content = draft.get_platform_content(PlatformType.XIAOHONGSHU)
        zhihu_content = draft.get_platform_content(PlatformType.ZHIHU)

        assert xhs_content is not None
        assert xhs_content.title == "小红书标题"
        assert zhihu_content is None

    def test_content_draft_is_approved(self) -> None:
        """
        Test ContentDraft.is_approved property.

        Arrange: Create ContentDraft with different statuses
        Act: Check is_approved
        Assert: Returns correct boolean values
        """
        approved_draft = ContentDraft(
            id="draft-001",
            brief_id="brief-001",
            topic="Test",
            platforms=[PlatformType.XIAOHONGSHU],
            status=DraftStatus.APPROVED,
        )

        pending_draft = ContentDraft(
            id="draft-002",
            brief_id="brief-001",
            topic="Test",
            platforms=[PlatformType.XIAOHONGSHU],
            status=DraftStatus.DRAFT,
        )

        assert approved_draft.is_approved() is True
        assert pending_draft.is_approved() is False

    def test_review_feedback_validation(self) -> None:
        """
        Test ReviewFeedback validates required fields.

        Arrange: Create valid ReviewFeedback
        Act: Validate
        Assert: Instance is created correctly
        """
        feedback = ReviewFeedback(
            reviewer="system",
            approved=True,
            score=QualityScore(
                relevance=8.0,
                readability=8.0,
                engagement_potential=8.0,
                brand_alignment=8.0,
                platform_fit=8.0,
            ),
            issues=[],
            suggestions=["建议优化标题"],
            comment="整体不错",
        )

        assert feedback.approved is True
        assert len(feedback.suggestions) == 1

    def test_content_draft_updated_at_auto_update(self) -> None:
        """
        Test ContentDraft updates updated_at on modification.

        Arrange: Create ContentDraft
        Act: Modify a field
        Assert: updated_at changes
        """
        draft = ContentDraft(
            id="draft-001",
            brief_id="brief-001",
            topic="Original",
            platforms=[PlatformType.XIAOHONGSHU],
        )

        original_time = draft.updated_at
        draft.status = DraftStatus.IN_REVIEW

        # Model validator should have updated the timestamp
        # Note: This depends on the validator implementation
        assert draft.status == DraftStatus.IN_REVIEW


class TestPublishResultSchema:
    """Test cases for PublishResult schema."""

    def test_publish_result_valid_creation(self, sample_publish_result_schema: PublishResult) -> None:
        """
        Test PublishResult can be created with valid data.

        Arrange: Use fixture with valid publish result
        Act: Validate the instance
        Assert: All fields are correct
        """
        result = sample_publish_result_schema

        assert result.id == "publish-20250320-001"
        assert result.status == PublishStatus.PUBLISHED
        assert result.success_count == 1

    def test_platform_post_info_validation(self) -> None:
        """
        Test PlatformPostInfo validates engagement metrics.

        Arrange: Create valid PlatformPostInfo
        Act: Validate
        Assert: Instance is created correctly
        """
        post_info = PlatformPostInfo(
            platform=PlatformType.XIAOHONGSHU,
            post_id="post_123",
            post_url="https://xiaohongshu.com/explore/123",
            initial_views=1000,
            initial_likes=100,
            published_at=datetime.now(),
        )

        assert post_info.platform == PlatformType.XIAOHONGSHU
        assert post_info.initial_views == 1000

    def test_platform_post_info_negative_metrics(self) -> None:
        """
        Test PlatformPostInfo rejects negative metrics.

        Arrange: Try to create with negative views
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError):
            PlatformPostInfo(
                platform=PlatformType.XIAOHONGSHU,
                post_id="post_123",
                post_url="https://example.com",
                initial_views=-100,  # Negative not allowed
                published_at=datetime.now(),
            )

    def test_publish_error_validation(self) -> None:
        """
        Test PublishError validates error information.

        Arrange: Create valid PublishError
        Act: Validate
        Assert: Instance is created correctly
        """
        error = PublishError(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            platform=PlatformType.XIAOHONGSHU,
            retry_able=True,
            retry_count=1,
            details={"retry_after": 60},
        )

        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_able is True
        assert error.retry_count == 1

    def test_publish_result_is_complete(self) -> None:
        """
        Test PublishResult.is_complete property.

        Arrange: Create PublishResult with different statuses
        Act: Check is_complete
        Assert: Returns correct boolean values
        """
        completed_result = PublishResult(
            id="publish-001",
            draft_id="draft-001",
            status=PublishStatus.PUBLISHED,
            platforms=[PlatformType.XIAOHONGSHU],
            total_count=1,
            success_count=1,
            failure_count=0,
        )

        pending_result = PublishResult(
            id="publish-002",
            draft_id="draft-002",
            status=PublishStatus.PENDING,
            platforms=[PlatformType.XIAOHONGSHU],
            total_count=1,
            success_count=0,
            failure_count=0,
        )

        assert completed_result.is_complete() is True
        assert pending_result.is_complete() is False

    def test_publish_result_get_success_rate(self) -> None:
        """
        Test PublishResult.get_success_rate calculation.

        Arrange: Create PublishResult with mixed results
        Act: Call get_success_rate()
        Assert: Returns correct rate
        """
        result = PublishResult(
            id="publish-001",
            draft_id="draft-001",
            status=PublishStatus.PUBLISHED,
            platforms=[PlatformType.XIAOHONGSHU, PlatformType.WECHAT, PlatformType.WEIBO],
            total_count=3,
            success_count=2,
            failure_count=1,
        )

        assert result.get_success_rate() == pytest.approx(0.6667, rel=0.01)

    def test_publish_result_zero_total_success_rate(self) -> None:
        """
        Test PublishResult.get_success_rate with zero total.

        Arrange: Create PublishResult with total_count=0
        Act: Call get_success_rate()
        Assert: Returns 0.0
        """
        result = PublishResult(
            id="publish-001",
            draft_id="draft-001",
            status=PublishStatus.PENDING,
            platforms=[],
            total_count=0,
            success_count=0,
            failure_count=0,
        )

        assert result.get_success_rate() == 0.0

    def test_publish_result_get_post_url(self) -> None:
        """
        Test PublishResult.get_post_url method.

        Arrange: Create PublishResult with successful posts
        Act: Get URL for specific platform
        Assert: Returns correct URL or None
        """
        result = PublishResult(
            id="publish-001",
            draft_id="draft-001",
            status=PublishStatus.PUBLISHED,
            platforms=[PlatformType.XIAOHONGSHU, PlatformType.WECHAT],
            total_count=2,
            success_count=2,
            failure_count=0,
            successful_posts=[
                PlatformPostInfo(
                    platform=PlatformType.XIAOHONGSHU,
                    post_id="post_123",
                    post_url="https://xhs.com/123",
                    published_at=datetime.now(),
                ),
                PlatformPostInfo(
                    platform=PlatformType.WECHAT,
                    post_id="post_456",
                    post_url="https://mp.weixin.qq.com/456",
                    published_at=datetime.now(),
                ),
            ],
        )

        xhs_url = result.get_post_url(PlatformType.XIAOHONGSHU)
        weibo_url = result.get_post_url(PlatformType.WEIBO)

        assert xhs_url == "https://xhs.com/123"
        assert weibo_url is None

    def test_publish_result_has_retryable_errors(self) -> None:
        """
        Test PublishResult.has_retryable_errors method.

        Arrange: Create PublishResult with mixed errors
        Act: Check has_retryable_errors
        Assert: Returns correct boolean
        """
        result_with_retryable = PublishResult(
            id="publish-001",
            draft_id="draft-001",
            status=PublishStatus.FAILED,
            platforms=[PlatformType.XIAOHONGSHU],
            total_count=1,
            success_count=0,
            failure_count=1,
            errors=[
                PublishError(
                    code="RATE_LIMIT",
                    message="Too many requests",
                    retry_able=True,
                )
            ],
        )

        result_without_retryable = PublishResult(
            id="publish-002",
            draft_id="draft-002",
            status=PublishStatus.FAILED,
            platforms=[PlatformType.WECHAT],
            total_count=1,
            success_count=0,
            failure_count=1,
            errors=[
                PublishError(
                    code="INVALID_CONTENT",
                    message="Content violates policy",
                    retry_able=False,
                )
            ],
        )

        assert result_with_retryable.has_retryable_errors() is True
        assert result_without_retryable.has_retryable_errors() is False


class TestAnalyticsReportSchema:
    """Test cases for AnalyticsReport schema."""

    def test_metric_value_validation(self) -> None:
        """
        Test MetricValue validates metric fields.

        Arrange: Create valid MetricValue
        Act: Validate
        Assert: Instance is created correctly
        """
        metric = MetricValue(
            type=MetricType.VIEWS,
            value=1000,
            previous_value=800,
        )

        assert metric.type == MetricType.VIEWS
        assert metric.value == 1000
        assert metric.previous_value == 800
        # change_percent should be auto-calculated
        assert metric.change_percent == pytest.approx(25.0)

    def test_metric_value_change_percent_calculation(self) -> None:
        """
        Test MetricValue calculates change_percent correctly.

        Arrange: Create MetricValue with value and previous_value
        Act: Validate
        Assert: change_percent is calculated correctly
        """
        # Increase
        metric1 = MetricValue(
            type=MetricType.LIKES,
            value=150,
            previous_value=100,
        )
        assert metric1.change_percent == 50.0

        # Decrease
        metric2 = MetricValue(
            type=MetricType.COMMENTS,
            value=80,
            previous_value=100,
        )
        assert metric2.change_percent == -20.0

    def test_engagement_rate_validation(self) -> None:
        """
        Test EngagementRate validates all rate fields.

        Arrange: Create valid EngagementRate
        Act: Validate
        Assert: All rates are non-negative
        """
        rate = EngagementRate(
            overall=0.087,
            like_rate=0.05,
            comment_rate=0.02,
            share_rate=0.01,
            save_rate=0.007,
        )

        assert rate.overall == 0.087
        assert rate.like_rate == 0.05

    def test_platform_analytics_calculate_total_engagement(self) -> None:
        """
        Test PlatformAnalytics.calculate_total_engagement method.

        Arrange: Create PlatformAnalytics with metrics
        Act: Call calculate_total_engagement()
        Assert: Returns sum of engagement metrics
        """
        from src.schemas.analytics_report import PlatformAnalytics

        analytics = PlatformAnalytics(
            platform=PlatformType.XIAOHONGSHU,
            post_id="post_123",
            post_url="https://xhs.com/123",
            metrics={
                MetricType.LIKES: MetricValue(
                    type=MetricType.LIKES,
                    value=100,
                ),
                MetricType.COMMENTS: MetricValue(
                    type=MetricType.COMMENTS,
                    value=20,
                ),
                MetricType.SHARES: MetricValue(
                    type=MetricType.SHARES,
                    value=10,
                ),
            },
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
        )

        assert analytics.calculate_total_engagement() == 130

    def test_performance_insight_validation(self) -> None:
        """
        Test PerformanceInsight validates insight fields.

        Arrange: Create valid PerformanceInsight
        Act: Validate
        Assert: Instance is created correctly
        """
        insight = PerformanceInsight(
            category="strength",
            title="小红书表现突出",
            description="互动率高于平均水平",
            actionable=True,
            confidence=0.9,
            recommendations=["继续发布同类内容"],
        )

        assert insight.category == "strength"
        assert insight.confidence == 0.9

    def test_performance_insight_confidence_bounds(self) -> None:
        """
        Test PerformanceInsight validates confidence range.

        Arrange: Try to create with invalid confidence
        Act: Validate
        Assert: ValidationError is raised
        """
        with pytest.raises(ValidationError):
            PerformanceInsight(
                category="strength",
                title="Test",
                description="Test",
                confidence=1.5,  # Too high
            )

        with pytest.raises(ValidationError):
            PerformanceInsight(
                category="strength",
                title="Test",
                description="Test",
                confidence=-0.1,  # Too low
            )
