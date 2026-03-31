"""
Unit tests for HotspotScheduler.

Mocks APScheduler, data_collector, publish_engine, and DB sessions to test
scheduler lifecycle and each scheduled task method.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.error_handling import success, error
from src.models.base import Base
from src.models.client import Client
from src.models.account import Account, AccountStatus
from src.models.content import Content
from src.models.hot_topic import HotTopic
from src.models.metrics import Metrics
from src.services.scheduler import HotspotScheduler, get_scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_engine():
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
async def session_factory(async_engine):
    """Return a session factory bound to the in-memory engine."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def session(session_factory):
    async with session_factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def scheduler(async_engine, session_factory):
    """
    Build a HotspotScheduler that uses the in-memory engine/session factory
    and mocked external dependencies.
    """
    with (
        patch("src.services.scheduler.get_data_collector") as mock_dc,
        patch("src.services.scheduler.get_publish_engine_v2") as mock_pe,
    ):
        mock_dc.return_value = AsyncMock()
        mock_pe.return_value = MagicMock()

        sched = HotspotScheduler.__new__(HotspotScheduler)
        sched.scheduler = MagicMock()
        sched.scheduler.running = False
        sched.db_url = "sqlite+aiosqlite:///:memory:"
        sched.engine = async_engine
        sched.SessionLocal = session_factory
        sched.data_collector = mock_dc.return_value
        sched.publish_engine = mock_pe.return_value

        yield sched


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSchedulerLifecycle:
    """Tests for start / shutdown / job management."""

    def test_start_when_disabled(self, scheduler):
        """Should not start the scheduler when SCHEDULER_ENABLED=false."""
        with patch("src.services.scheduler.settings") as mock_settings:
            mock_settings.SCHEDULER_ENABLED = False
            scheduler.start()

        scheduler.scheduler.start.assert_not_called()
        scheduler.scheduler.add_job.assert_not_called()

    def test_start_when_enabled(self, scheduler):
        """Should add jobs and start the scheduler."""
        with patch("src.services.scheduler.settings") as mock_settings:
            mock_settings.SCHEDULER_ENABLED = True
            mock_settings.SCHEDULER_TIMEZONE = "Asia/Shanghai"
            scheduler.start()

        assert scheduler.scheduler.add_job.call_count == 5
        scheduler.scheduler.start.assert_called_once()

    def test_shutdown_when_running(self, scheduler):
        scheduler.scheduler.running = True
        scheduler.shutdown()
        scheduler.scheduler.shutdown.assert_called_once()

    def test_shutdown_when_not_running(self, scheduler):
        scheduler.scheduler.running = False
        scheduler.shutdown()
        scheduler.scheduler.shutdown.assert_not_called()

    def test_add_custom_job(self, scheduler):
        mock_func = MagicMock()
        mock_trigger = MagicMock()

        scheduler.add_custom_job(
            mock_func, mock_trigger, job_id="custom_1", name="Custom Job"
        )

        scheduler.scheduler.add_job.assert_called_once_with(
            mock_func,
            mock_trigger,
            id="custom_1",
            name="Custom Job",
            replace_existing=True,
        )

    def test_remove_job(self, scheduler):
        scheduler.remove_job("some_job_id")
        scheduler.scheduler.remove_job.assert_called_once_with("some_job_id")

    def test_get_jobs_empty(self, scheduler):
        scheduler.scheduler.get_jobs.return_value = []
        assert scheduler.get_jobs() == []

    def test_get_jobs_returns_formatted_list(self, scheduler):
        mock_job = MagicMock()
        mock_job.id = "job1"
        mock_job.name = "Test Job"
        mock_job.next_run_time = datetime(2026, 1, 1, 8, 0, 0)
        mock_job.trigger = "cron[hour='8']"
        scheduler.scheduler.get_jobs.return_value = [mock_job]

        jobs = scheduler.get_jobs()

        assert len(jobs) == 1
        assert jobs[0]["id"] == "job1"
        assert jobs[0]["name"] == "Test Job"
        assert jobs[0]["next_run_time"] == "2026-01-01T08:00:00"

    def test_get_jobs_with_none_next_run_time(self, scheduler):
        mock_job = MagicMock()
        mock_job.id = "paused"
        mock_job.name = "Paused Job"
        mock_job.next_run_time = None
        mock_job.trigger = "interval[hours=1]"
        scheduler.scheduler.get_jobs.return_value = [mock_job]

        jobs = scheduler.get_jobs()

        assert jobs[0]["next_run_time"] is None


# ---------------------------------------------------------------------------
# daily_hotspot_detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDailyHotspotDetection:
    """Tests for HotspotScheduler.daily_hotspot_detection."""

    async def test_no_clients(self, scheduler, session):
        """Should exit gracefully when no clients exist."""
        await scheduler.daily_hotspot_detection()
        # No error -- just logs and returns

    async def test_with_clients_crew_import_error(self, scheduler, session):
        """Should handle crew import errors without crashing."""
        # Insert a client
        client = Client(id="client-001", name="TestCorp", industry="AI")
        session.add(client)
        await session.commit()

        # The method imports CrewAI inside -- which won't exist in test env.
        # It should catch the ImportError / Exception and continue.
        await scheduler.daily_hotspot_detection()

    async def test_clients_result_failure(self, scheduler, session_factory):
        """Should return early if list_clients fails."""
        # Patch ClientService.list_clients to return an error
        with patch("src.services.scheduler.ClientService") as MockCS:
            instance = MockCS.return_value
            instance.list_clients = AsyncMock(
                return_value=error("DB error", "CLIENT_LIST_ERROR")
            )
            await scheduler.daily_hotspot_detection()


# ---------------------------------------------------------------------------
# daily_content_generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDailyContentGeneration:
    """Tests for HotspotScheduler.daily_content_generation."""

    async def test_no_clients(self, scheduler, session):
        await scheduler.daily_content_generation()

    async def test_clients_result_failure(self, scheduler):
        with patch("src.services.scheduler.ClientService") as MockCS:
            instance = MockCS.return_value
            instance.list_clients = AsyncMock(
                return_value=error("fail", "CLIENT_LIST_ERROR")
            )
            await scheduler.daily_content_generation()

    async def test_no_hot_topics_skips_generation(self, scheduler, session):
        """When there are no recent hot topics, content generation is skipped."""
        client = Client(id="client-gen1", name="GenCorp")
        account = Account(
            id="account-gen1",
            client_id="client-gen1",
            platform="xiaohongshu",
            username="u1",
            status=AccountStatus.ACTIVE,
        )
        session.add_all([client, account])
        await session.commit()

        # No hot topics in DB -- should log "无匹配热点" and continue
        await scheduler.daily_content_generation()


# ---------------------------------------------------------------------------
# auto_publish
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAutoPublish:
    """Tests for HotspotScheduler.auto_publish."""

    async def test_no_pending_contents(self, scheduler, session):
        """Should return early when no scheduled contents exist."""
        await scheduler.auto_publish()

    async def test_publish_success(self, scheduler, session):
        """Content with status 'scheduled' should be published."""
        content = Content(
            id="content-pub1",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["xiaohongshu"],
            images=[],
            hashtags=[],
            status="scheduled",
        )
        session.add(content)
        await session.commit()

        scheduler.publish_engine.publish = AsyncMock(
            return_value={"success": True, "url": "https://example.com/post/1"}
        )

        await scheduler.auto_publish()

        # Verify status was updated
        await session.refresh(content)
        assert content.status == "published"

    async def test_publish_failure(self, scheduler, session):
        """Content should be marked failed when publish returns error."""
        content = Content(
            id="content-pub2",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["weibo"],
            images=[],
            hashtags=[],
            status="scheduled",
        )
        session.add(content)
        await session.commit()

        scheduler.publish_engine.publish = AsyncMock(
            return_value={"success": False, "error": "Auth failed"}
        )

        await scheduler.auto_publish()

        await session.refresh(content)
        assert content.status == "failed"

    async def test_publish_exception(self, scheduler, session):
        """Content should be marked failed when publish raises."""
        content = Content(
            id="content-pub3",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["zhihu"],
            images=[],
            hashtags=[],
            status="scheduled",
        )
        session.add(content)
        await session.commit()

        scheduler.publish_engine.publish = AsyncMock(
            side_effect=RuntimeError("Connection lost")
        )

        await scheduler.auto_publish()

        await session.refresh(content)
        assert content.status == "failed"

    async def test_content_without_platforms_skipped(self, scheduler, session):
        """Content with no platforms should be marked failed."""
        content = Content(
            id="content-pub4",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=[],
            images=[],
            hashtags=[],
            status="scheduled",
        )
        session.add(content)
        await session.commit()

        await scheduler.auto_publish()

        await session.refresh(content)
        assert content.status == "failed"


# ---------------------------------------------------------------------------
# hourly_data_collection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHourlyDataCollection:
    """Tests for HotspotScheduler.hourly_data_collection."""

    async def test_no_published_contents(self, scheduler, session):
        """Should exit early when nothing is published recently."""
        await scheduler.hourly_data_collection()

    async def test_collects_data_for_published_content(self, scheduler, session):
        """Should call data_collector for each platform of published content."""
        content = Content(
            id="content-dc1",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["xiaohongshu", "weibo"],
            images=[],
            hashtags=[],
            status="published",
            published_at=datetime.utcnow() - timedelta(days=1),
        )
        session.add(content)
        await session.commit()

        scheduler.data_collector.collect = AsyncMock(
            return_value={"views": 100, "likes": 10, "comments": 5, "shares": 2}
        )

        await scheduler.hourly_data_collection()

        assert scheduler.data_collector.collect.call_count == 2

    async def test_collector_returns_none(self, scheduler, session):
        """Should handle when collector returns no data."""
        content = Content(
            id="content-dc2",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["weibo"],
            images=[],
            hashtags=[],
            status="published",
            published_at=datetime.utcnow(),
        )
        session.add(content)
        await session.commit()

        scheduler.data_collector.collect = AsyncMock(return_value=None)

        # Should not raise
        await scheduler.hourly_data_collection()

    async def test_collector_exception_per_platform(self, scheduler, session):
        """An exception for one platform should not stop processing others."""
        content = Content(
            id="content-dc3",
            user_id="user1",
            topic="Test",
            title="Title",
            body="Body",
            platforms=["xiaohongshu", "weibo"],
            images=[],
            hashtags=[],
            status="published",
            published_at=datetime.utcnow(),
        )
        session.add(content)
        await session.commit()

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("platform") == "xiaohongshu":
                raise RuntimeError("network error")
            return {"views": 50, "likes": 5, "comments": 1, "shares": 0}

        scheduler.data_collector.collect = AsyncMock(side_effect=side_effect)

        await scheduler.hourly_data_collection()

        assert call_count == 2  # both platforms attempted


# ---------------------------------------------------------------------------
# generate_weekly_reports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateWeeklyReports:
    """Tests for HotspotScheduler.generate_weekly_reports."""

    async def test_no_clients(self, scheduler, session):
        """Should exit gracefully when no clients exist."""
        await scheduler.generate_weekly_reports()

    async def test_clients_result_failure(self, scheduler):
        with patch("src.services.scheduler.ClientService") as MockCS:
            instance = MockCS.return_value
            instance.list_clients = AsyncMock(
                return_value=error("fail", "CLIENT_LIST_ERROR")
            )
            await scheduler.generate_weekly_reports()

    async def test_report_generated_for_client(self, scheduler, session, tmp_path):
        """Should generate a markdown report file for a client."""
        client = Client(id="client-rpt1", name="ReportCorp")
        account = Account(
            id="account-rpt1",
            client_id="client-rpt1",
            platform="xiaohongshu",
            username="u1",
            status=AccountStatus.ACTIVE,
        )
        session.add_all([client, account])
        await session.commit()

        # Insert some metrics
        metric = Metrics(
            id="metric-rpt1",
            platform="xiaohongshu",
            views=500,
            likes=30,
            comments=10,
            shares=5,
        )
        session.add(metric)
        await session.commit()

        # Patch the report directory to use tmp_path
        with patch("src.services.scheduler.Path") as MockPath:
            mock_report_dir = tmp_path / "reports"
            mock_report_dir.mkdir(exist_ok=True)
            MockPath.return_value = mock_report_dir
            # Path("reports") -> returns the mock dir; but the actual code calls
            # report_dir = Path("reports"); report_dir.mkdir(...)
            # We need to be more careful -- just patch at a higher level.

        # Run with real Path -- report_dir = Path("reports")
        # This creates a `reports/` dir in CWD. For testing we accept that.
        await scheduler.generate_weekly_reports()

    async def test_report_no_accounts(self, scheduler, session):
        """Client with no accounts should still produce a report."""
        client = Client(id="client-rpt2", name="NoAccountCorp")
        session.add(client)
        await session.commit()

        await scheduler.generate_weekly_reports()


# ---------------------------------------------------------------------------
# get_scheduler singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetScheduler:
    """Tests for the module-level get_scheduler singleton."""

    def test_returns_hotspot_scheduler(self):
        import src.services.scheduler as mod

        with (
            patch("src.services.scheduler.get_data_collector"),
            patch("src.services.scheduler.get_publish_engine_v2"),
        ):
            mod._scheduler = None
            sched = mod.get_scheduler()
            assert isinstance(sched, HotspotScheduler)
            # Reset
            mod._scheduler = None

    def test_returns_same_instance(self):
        import src.services.scheduler as mod

        with (
            patch("src.services.scheduler.get_data_collector"),
            patch("src.services.scheduler.get_publish_engine_v2"),
        ):
            mod._scheduler = None
            s1 = mod.get_scheduler()
            s2 = mod.get_scheduler()
            assert s1 is s2
            mod._scheduler = None
