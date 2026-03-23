"""
Unit tests for database models.

Tests cover:
- Model creation and defaults
- Relationships
- Properties and computed fields
- Database operations (CRUD)
"""

from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from src.models.analytics import Analytics, AudienceInsightDB, MetricSnapshot
from src.models.base import Base, TimestampMixin
from src.models.content import Content, ContentBrief, ContentDraft, ContentType, DraftStatus
from src.models.publish_log import PlatformPost, PublishLog, PublishStatus, ScheduleType


class TestBase:
    """Test cases for Base and TimestampMixin."""

    def test_base_metadata_tables(self, test_engine) -> None:
        """
        Test that all tables are created in the database.

        Arrange: Use test_engine fixture (tables already created)
        Act: Inspect table names
        Assert: All expected tables exist
        """
        table_names = Base.metadata.tables.keys()

        expected_tables = [
            "content_briefs",
            "content_drafts",
            "contents",
            "publish_logs",
            "platform_posts",
            "analytics",
            "metric_snapshots",
            "audience_insights",
        ]

        for table in expected_tables:
            assert table in table_names, f"Table '{table}' not found"


class TestContentBriefModel:
    """Test cases for ContentBrief database model."""

    def test_content_brief_creation(self, test_session: Session) -> None:
        """
        Test ContentBrief can be created and persisted.

        Arrange: Prepare valid brief data
        Act: Create and commit to database
        Assert: Record is persisted with auto-generated ID
        """
        brief = ContentBrief(
            topic="AI创业指南",
            sub_topics=["MVP", "融资"],
            keywords=["AI", "创业"],
            target_audience=[{"segment": "entrepreneur"}],
            trending_topics=[{"keyword": "AI Agent"}],
            content_angle="技术人视角",
            tone="professional",
            suggested_content_type="article",
            primary_platform="xiaohongshu",
            secondary_platforms=["wechat"],
            key_points=["技术选型"],
            call_to_action="关注我",
            hashtags=["#AI创业"],
        )

        test_session.add(brief)
        test_session.commit()
        test_session.refresh(brief)

        assert brief.id is not None
        assert brief.id.startswith("brief-")
        assert brief.topic == "AI创业指南"

    def test_content_brief_query(self, test_session: Session) -> None:
        """
        Test ContentBrief can be queried from database.

        Arrange: Create and persist a brief
        Act: Query by topic
        Assert: Returns the correct brief
        """
        brief = ContentBrief(
            topic="查询测试",
            keywords=["test"],
            target_audience=[],
            trending_topics=[],
            content_angle="test",
            tone="professional",
            suggested_content_type="article",
            primary_platform="xiaohongshu",
            secondary_platforms=[],
            key_points=[],
            hashtags=[],
        )
        test_session.add(brief)
        test_session.commit()

        result = test_session.query(ContentBrief).filter_by(topic="查询测试").first()

        assert result is not None
        assert result.topic == "查询测试"

    def test_content_brief_relationship_with_drafts(
        self,
        test_session: Session,
        sample_content_brief,
    ) -> None:
        """
        Test ContentBrief has relationship with ContentDraft.

        Arrange: Create brief and draft
        Act: Access brief.drafts
        Assert: Draft is accessible via relationship
        """
        draft = ContentDraft(
            brief_id=sample_content_brief.id,
            status=DraftStatus.DRAFT,
            version=1,
            topic="测试草稿",
            content_type="article",
            platforms=["xiaohongshu"],
            platform_content=[],
            tone="professional",
            reviews=[],
            tags=[],
        )
        test_session.add(draft)
        test_session.commit()

        test_session.refresh(sample_content_brief)
        assert len(sample_content_brief.drafts) >= 1


class TestContentDraftModel:
    """Test cases for ContentDraft database model."""

    def test_content_draft_creation(
        self,
        test_session: Session,
        sample_content_brief,
    ) -> None:
        """
        Test ContentDraft can be created and persisted.

        Arrange: Prepare valid draft data with brief reference
        Act: Create and commit to database
        Assert: Record is persisted with auto-generated ID
        """
        draft = ContentDraft(
            brief_id=sample_content_brief.id,
            status=DraftStatus.DRAFT,
            version=1,
            topic="AI创业指南",
            content_type="article",
            platforms=["xiaohongshu", "wechat"],
            platform_content=[
                {
                    "platform": "xiaohongshu",
                    "title": "测试标题",
                    "plain_text": "测试内容",
                }
            ],
            tone="professional",
            reviews=[],
            tags=["AI", "创业"],
            category="创业经验",
        )

        test_session.add(draft)
        test_session.commit()
        test_session.refresh(draft)

        assert draft.id is not None
        assert draft.id.startswith("draft-")
        assert draft.status == DraftStatus.DRAFT

    def test_content_draft_is_approved_property(
        self,
        test_session: Session,
        sample_content_brief,
    ) -> None:
        """
        Test ContentDraft.is_approved property.

        Arrange: Create drafts with different statuses
        Act: Check is_approved property
        Assert: Returns correct boolean values
        """
        approved_draft = ContentDraft(
            brief_id=sample_content_brief.id,
            status=DraftStatus.APPROVED,
            version=1,
            topic="Approved",
            content_type="article",
            platforms=["xiaohongshu"],
            platform_content=[],
            tone="professional",
            reviews=[],
            tags=[],
        )

        pending_draft = ContentDraft(
            brief_id=sample_content_brief.id,
            status=DraftStatus.DRAFT,
            version=1,
            topic="Pending",
            content_type="article",
            platforms=["xiaohongshu"],
            platform_content=[],
            tone="professional",
            reviews=[],
            tags=[],
        )

        test_session.add_all([approved_draft, pending_draft])
        test_session.commit()

        assert approved_draft.is_approved is True
        assert pending_draft.is_approved is False

    def test_content_draft_cascade_delete(
        self,
        test_session: Session,
        sample_content_brief,
    ) -> None:
        """
        Test ContentDraft is deleted when ContentBrief is deleted.

        Arrange: Create brief with draft
        Act: Delete the brief
        Assert: Draft is also deleted (cascade)
        """
        draft = ContentDraft(
            brief_id=sample_content_brief.id,
            status=DraftStatus.DRAFT,
            version=1,
            topic="Cascade Test",
            content_type="article",
            platforms=["xiaohongshu"],
            platform_content=[],
            tone="professional",
            reviews=[],
            tags=[],
        )
        test_session.add(draft)
        test_session.commit()
        draft_id = draft.id

        test_session.delete(sample_content_brief)
        test_session.commit()

        result = test_session.query(ContentDraft).filter_by(id=draft_id).first()
        assert result is None


class TestContentModel:
    """Test cases for Content database model."""

    def test_content_creation(self, test_session: Session) -> None:
        """
        Test Content can be created and persisted.

        Arrange: Prepare valid content data
        Act: Create and commit to database
        Assert: Record is persisted with defaults
        """
        content = Content(
            topic="AI创业指南",
            content_type="article",
            platforms=["xiaohongshu", "wechat"],
            user_id="user-001",
        )

        test_session.add(content)
        test_session.commit()
        test_session.refresh(content)

        assert content.id is not None
        assert content.id.startswith("content-")
        assert content.total_views == 0
        assert content.total_likes == 0

    def test_content_with_metrics(self, test_session: Session) -> None:
        """
        Test Content can store performance metrics.

        Arrange: Create content with metrics
        Act: Persist and query
        Assert: Metrics are stored correctly
        """
        content = Content(
            topic="热门内容",
            content_type="article",
            platforms=["xiaohongshu"],
            user_id="user-001",
            total_views=15000,
            total_likes=1200,
            total_comments=89,
            total_shares=34,
        )

        test_session.add(content)
        test_session.commit()
        test_session.refresh(content)

        assert content.total_views == 15000
        assert content.total_likes == 1200


class TestPublishLogModel:
    """Test cases for PublishLog database model."""

    def test_publish_log_creation(
        self,
        test_session: Session,
        sample_content_draft,
    ) -> None:
        """
        Test PublishLog can be created and persisted.

        Arrange: Prepare valid publish log data
        Act: Create and commit to database
        Assert: Record is persisted with defaults
        """
        log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.PENDING,
            schedule_type=ScheduleType.IMMEDIATE,
            platforms=["xiaohongshu"],
            successful_posts=[],
            failed_platforms=[],
            errors=[],
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.id is not None
        assert log.id.startswith("publish-")
        assert log.status == PublishStatus.PENDING
        assert log.retry_attempts == 0

    def test_publish_log_is_complete_property(
        self,
        test_session: Session,
        sample_content_draft,
    ) -> None:
        """
        Test PublishLog.is_complete property.

        Arrange: Create logs with different statuses
        Act: Check is_complete property
        Assert: Returns correct boolean values
        """
        published_log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.PUBLISHED,
            platforms=["xiaohongshu"],
            successful_posts=[],
            failed_platforms=[],
            errors=[],
        )

        pending_log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.PENDING,
            platforms=["xiaohongshu"],
            successful_posts=[],
            failed_platforms=[],
            errors=[],
        )

        failed_log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.FAILED,
            platforms=["xiaohongshu"],
            successful_posts=[],
            failed_platforms=["xiaohongshu"],
            errors=[{"code": "API_ERROR", "message": "Failed"}],
        )

        test_session.add_all([published_log, pending_log, failed_log])
        test_session.commit()

        assert published_log.is_complete is True
        assert pending_log.is_complete is False
        assert failed_log.is_complete is True

    def test_publish_log_success_rate_property(
        self,
        test_session: Session,
        sample_content_draft,
    ) -> None:
        """
        Test PublishLog.success_rate property.

        Arrange: Create log with mixed results
        Act: Check success_rate property
        Assert: Returns correct rate
        """
        log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.PUBLISHED,
            platforms=["xiaohongshu", "wechat", "weibo"],
            successful_posts=[],
            failed_platforms=["weibo"],
            errors=[],
            success_count=2,
            failure_count=1,
        )

        test_session.add(log)
        test_session.commit()

        assert log.success_rate == pytest.approx(0.6667, rel=0.01)

    def test_publish_log_zero_success_rate(
        self,
        test_session: Session,
        sample_content_draft,
    ) -> None:
        """
        Test PublishLog.success_rate with zero total.

        Arrange: Create log with zero counts
        Act: Check success_rate property
        Assert: Returns 0.0
        """
        log = PublishLog(
            draft_id=sample_content_draft.id,
            status=PublishStatus.PENDING,
            platforms=[],
            successful_posts=[],
            failed_platforms=[],
            errors=[],
            success_count=0,
            failure_count=0,
        )

        test_session.add(log)
        test_session.commit()

        assert log.success_rate == 0.0


class TestPlatformPostModel:
    """Test cases for PlatformPost database model."""

    def test_platform_post_creation(
        self,
        test_session: Session,
        sample_publish_log,
    ) -> None:
        """
        Test PlatformPost can be created and persisted.

        Arrange: Prepare valid platform post data
        Act: Create and commit to database
        Assert: Record is persisted correctly
        """
        post = PlatformPost(
            publish_log_id=sample_publish_log.id,
            platform="xiaohongshu",
            post_id="64a1b2c3d4e5f6g7h8i9j0",
            post_url="https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
            initial_views=0,
            initial_likes=0,
            post_metadata={"source": "api"},
        )

        test_session.add(post)
        test_session.commit()
        test_session.refresh(post)

        assert post.id is not None
        assert post.id.startswith("post-")
        assert post.platform == "xiaohongshu"


class TestAnalyticsModel:
    """Test cases for Analytics database model."""

    def test_analytics_creation(self, test_session: Session) -> None:
        """
        Test Analytics can be created and persisted.

        Arrange: Prepare valid analytics data
        Act: Create and commit to database
        Assert: Record is persisted with defaults
        """
        analytics = Analytics(
            period="7d",
            period_start=datetime(2025, 3, 13),
            period_end=datetime(2025, 3, 20),
            platform_analytics=[
                {
                    "platform": "xiaohongshu",
                    "metrics": {"views": 15000, "likes": 1200},
                }
            ],
            total_views=15000,
            total_likes=1200,
            total_comments=89,
            total_shares=34,
            avg_engagement_rate=8.7,
            insights=[{"category": "strength", "title": "表现突出"}],
            top_insights=[{"category": "strength", "title": "表现突出"}],
            next_steps=["发布系列内容"],
            follow_up_topics=["AI融资"],
        )

        test_session.add(analytics)
        test_session.commit()
        test_session.refresh(analytics)

        assert analytics.id is not None
        assert analytics.id.startswith("analytics-")
        assert analytics.total_views == 15000

    def test_analytics_total_engagement_property(self, test_session: Session) -> None:
        """
        Test Analytics.total_engagement property.

        Arrange: Create analytics with engagement metrics
        Act: Access total_engagement property
        Assert: Returns sum of likes + comments + shares
        """
        analytics = Analytics(
            period="7d",
            period_start=datetime(2025, 3, 13),
            period_end=datetime(2025, 3, 20),
            platform_analytics=[],
            total_views=15000,
            total_likes=1200,
            total_comments=89,
            total_shares=34,
            avg_engagement_rate=8.7,
            insights=[],
            top_insights=[],
            next_steps=[],
            follow_up_topics=[],
        )

        test_session.add(analytics)
        test_session.commit()

        assert analytics.total_engagement == 1200 + 89 + 34


class TestMetricSnapshotModel:
    """Test cases for MetricSnapshot database model."""

    def test_metric_snapshot_creation(self, test_session: Session) -> None:
        """
        Test MetricSnapshot can be created and persisted.

        Arrange: Create analytics record first, then snapshot
        Act: Create and commit to database
        Assert: Record is persisted correctly
        """
        analytics = Analytics(
            period="7d",
            period_start=datetime(2025, 3, 13),
            period_end=datetime(2025, 3, 20),
            platform_analytics=[],
            insights=[],
            top_insights=[],
            next_steps=[],
            follow_up_topics=[],
        )
        test_session.add(analytics)
        test_session.commit()

        snapshot = MetricSnapshot(
            analytics_id=analytics.id,
            platform="xiaohongshu",
            post_id="post_123",
            views=1000,
            likes=100,
            comments=10,
            shares=5,
            saves=20,
            recorded_at=datetime.now(),
        )

        test_session.add(snapshot)
        test_session.commit()
        test_session.refresh(snapshot)

        assert snapshot.id is not None
        assert snapshot.id.startswith("snap-")
        assert snapshot.views == 1000
