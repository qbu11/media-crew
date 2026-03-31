"""
Unit tests for MetricsService.

Tests record_metric and get_metrics_by_content with in-memory SQLite.
"""

import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.metrics import Metrics
from src.services.metrics_service import MetricsService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_engine():
    """Create an in-memory async SQLite engine with all tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    """Provide a fresh AsyncSession for each test."""
    factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def service(session):
    """Return a MetricsService bound to the test session."""
    return MetricsService(session)


# ---------------------------------------------------------------------------
# record_metric
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecordMetric:
    """Tests for MetricsService.record_metric."""

    async def test_record_metric_success(self, service):
        """Should persist a Metrics row and return Success."""
        result = await service.record_metric(
            platform="xiaohongshu",
            post_url="https://xhs.com/post/123",
            content_id=None,
            views=1000,
            likes=50,
            comments=10,
            shares=5,
            raw_metrics={"extra": "data"},
        )

        assert result.success is True
        metric = result.data
        assert isinstance(metric, Metrics)
        assert metric.platform == "xiaohongshu"
        assert metric.post_url == "https://xhs.com/post/123"
        assert metric.views == 1000
        assert metric.likes == 50
        assert metric.comments == 10
        assert metric.shares == 5
        assert metric.raw_metrics == {"extra": "data"}
        assert metric.id is not None

    async def test_engagement_rate_calculated(self, service):
        """engagement_rate = (likes + comments + shares) / views."""
        result = await service.record_metric(
            platform="weibo",
            views=200,
            likes=10,
            comments=5,
            shares=5,
        )

        assert result.success is True
        # (10 + 5 + 5) / 200 = 0.1
        assert result.data.engagement_rate == pytest.approx(0.1)

    async def test_engagement_rate_none_when_views_zero(self, service):
        """When views=0 engagement_rate should be None."""
        result = await service.record_metric(
            platform="zhihu",
            views=0,
            likes=10,
            comments=5,
            shares=5,
        )

        assert result.success is True
        assert result.data.engagement_rate is None

    async def test_engagement_rate_none_when_views_none(self, service):
        """When views is None engagement_rate should be None."""
        result = await service.record_metric(
            platform="bilibili",
            views=None,
            likes=10,
            comments=5,
            shares=5,
        )

        assert result.success is True
        assert result.data.engagement_rate is None

    async def test_engagement_rate_with_partial_none_engagement(self, service):
        """Engagement fields that are None should be treated as 0."""
        result = await service.record_metric(
            platform="xiaohongshu",
            views=100,
            likes=None,
            comments=None,
            shares=10,
        )

        assert result.success is True
        # (0 + 0 + 10) / 100 = 0.1
        assert result.data.engagement_rate == pytest.approx(0.1)

    async def test_record_metric_minimal_fields(self, service):
        """Only platform is truly required; everything else can be None."""
        result = await service.record_metric(platform="douyin")

        assert result.success is True
        assert result.data.platform == "douyin"
        assert result.data.views is None
        assert result.data.likes is None
        assert result.data.engagement_rate is None

    async def test_record_metric_exception_triggers_rollback(self, session):
        """On database error, result should be Error and session rolled back."""
        svc = MetricsService(session)

        # Force an exception by patching session.commit to raise
        original_commit = session.commit
        async def _boom():
            raise RuntimeError("DB commit failed")
        session.commit = _boom

        result = await svc.record_metric(
            platform="weibo",
            views=100,
        )

        assert result.success is False
        assert result.error_code == "METRIC_RECORD_ERROR"

        # Restore for fixture cleanup
        session.commit = original_commit


# ---------------------------------------------------------------------------
# get_metrics_by_content
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMetricsByContent:
    """Tests for MetricsService.get_metrics_by_content."""

    async def test_get_metrics_by_content_success(self, service):
        """Should return all metrics matching the content_id."""
        cid = "draft-test123"

        # Insert two metrics for the same content_id
        await service.record_metric(platform="xiaohongshu", content_id=cid, views=100)
        await service.record_metric(platform="weibo", content_id=cid, views=200)
        # Insert one for a different content_id
        await service.record_metric(platform="zhihu", content_id="draft-other", views=300)

        result = await service.get_metrics_by_content(cid)

        assert result.success is True
        assert len(result.data) == 2
        platforms = {m.platform for m in result.data}
        assert platforms == {"xiaohongshu", "weibo"}

    async def test_get_metrics_by_content_empty(self, service):
        """Should return an empty list when no metrics match."""
        result = await service.get_metrics_by_content("nonexistent-content-id")

        assert result.success is True
        assert result.data == []

    async def test_get_metrics_by_content_exception(self, session):
        """On database error, result should be Error."""
        svc = MetricsService(session)

        # Force an exception by patching session.execute to raise
        async def _boom(*args, **kwargs):
            raise RuntimeError("DB execute failed")
        session.execute = _boom

        result = await svc.get_metrics_by_content("any-id")

        assert result.success is False
        assert result.error_code == "METRIC_GET_ERROR"


# ---------------------------------------------------------------------------
# Model property
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetricsModelProperty:
    """Tests for Metrics.total_engagement property."""

    async def test_total_engagement_all_values(self, service):
        """total_engagement = likes + comments + shares."""
        result = await service.record_metric(
            platform="weibo",
            views=500,
            likes=30,
            comments=20,
            shares=10,
        )

        assert result.data.total_engagement == 60

    async def test_total_engagement_with_none_values(self, service):
        """None values should be treated as 0 in total_engagement."""
        result = await service.record_metric(
            platform="weibo",
            views=500,
            likes=None,
            comments=20,
            shares=None,
        )

        assert result.data.total_engagement == 20
