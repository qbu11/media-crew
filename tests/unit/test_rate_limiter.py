"""
Unit tests for RateLimiter.

Tests cover:
- Rate limit checking (min interval, hourly, daily)
- Publish recording
- Stats retrieval
- History persistence
- Reset functionality
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.services.rate_limiter import RateLimiter, get_rate_limiter


@pytest.fixture
def limiter(tmp_path):
    """Create a RateLimiter with a temp directory."""
    return RateLimiter(storage_dir=str(tmp_path / "rate_limits"))


class TestCheckLimit:
    def test_allowed_when_empty(self, limiter):
        result = limiter.check_limit("xiaohongshu")
        assert result["allowed"] is True
        assert result["wait_seconds"] == 0

    def test_unsupported_platform(self, limiter):
        result = limiter.check_limit("unknown_platform")
        assert result["allowed"] is False
        assert "不支持" in result["reason"]

    def test_min_interval_block(self, limiter):
        # Add a recent publish
        limiter.publish_history["xiaohongshu"].append(datetime.now())
        result = limiter.check_limit("xiaohongshu")
        assert result["allowed"] is False
        assert result["wait_seconds"] > 0
        assert "间隔" in result["reason"]

    def test_min_interval_passed(self, limiter):
        # Add a publish long enough ago
        limiter.publish_history["xiaohongshu"].append(
            datetime.now() - timedelta(seconds=120)
        )
        result = limiter.check_limit("xiaohongshu")
        assert result["allowed"] is True

    def test_hourly_limit_block(self, limiter):
        # Fill up hourly limit (xiaohongshu = 3/hour)
        now = datetime.now()
        for i in range(3):
            limiter.publish_history["xiaohongshu"].append(
                now - timedelta(minutes=10 + i * 10)
            )
        result = limiter.check_limit("xiaohongshu")
        assert result["allowed"] is False
        assert "每小时" in result["reason"]

    def test_daily_limit_block(self, limiter):
        # Fill up daily limit (xiaohongshu = 10/day)
        now = datetime.now()
        for i in range(10):
            limiter.publish_history["xiaohongshu"].append(
                now - timedelta(hours=1 + i)
            )
        result = limiter.check_limit("xiaohongshu")
        assert result["allowed"] is False
        assert "每日" in result["reason"]

    def test_weibo_limits(self, limiter):
        # Weibo has higher limits
        result = limiter.check_limit("weibo")
        assert result["allowed"] is True
        assert result["limits"]["hourly_limit"] == 5
        assert result["limits"]["daily_limit"] == 20


class TestRecordPublish:
    async def test_record(self, limiter):
        await limiter.record_publish("xiaohongshu")
        assert len(limiter.publish_history["xiaohongshu"]) == 1

    async def test_record_unsupported(self, limiter):
        await limiter.record_publish("unknown")
        assert len(limiter.publish_history["unknown"]) == 0

    async def test_record_persists(self, limiter):
        await limiter.record_publish("xiaohongshu")
        history_file = limiter._get_history_file("xiaohongshu")
        assert history_file.exists()


class TestGetStats:
    def test_stats_empty(self, limiter):
        stats = limiter.get_stats("xiaohongshu")
        assert stats["xiaohongshu"]["hourly_count"] == 0
        assert stats["xiaohongshu"]["daily_count"] == 0

    def test_stats_with_history(self, limiter):
        limiter.publish_history["xiaohongshu"].append(datetime.now())
        stats = limiter.get_stats("xiaohongshu")
        assert stats["xiaohongshu"]["hourly_count"] == 1
        assert stats["xiaohongshu"]["daily_count"] == 1
        assert stats["xiaohongshu"]["hourly_remaining"] == 2  # 3 - 1

    def test_stats_all_platforms(self, limiter):
        stats = limiter.get_stats()
        assert "xiaohongshu" in stats
        assert "weibo" in stats
        assert "zhihu" in stats

    def test_stats_unknown_platform(self, limiter):
        stats = limiter.get_stats("unknown")
        assert len(stats) == 0


class TestLoadHistory:
    async def test_load_saved(self, limiter):
        await limiter.record_publish("xiaohongshu")
        await limiter.record_publish("xiaohongshu")

        # Create new limiter with same dir
        limiter2 = RateLimiter(storage_dir=str(limiter.storage_dir))
        await limiter2.load_history()
        assert len(limiter2.publish_history["xiaohongshu"]) == 2

    async def test_load_filters_old(self, limiter):
        # Manually write old timestamps
        import json
        history_file = limiter._get_history_file("xiaohongshu")
        old_ts = (datetime.now() - timedelta(hours=25)).isoformat()
        recent_ts = datetime.now().isoformat()
        history_file.write_text(json.dumps([old_ts, recent_ts]))

        await limiter.load_history()
        # Only recent should be loaded
        assert len(limiter.publish_history["xiaohongshu"]) == 1


class TestReset:
    async def test_reset_single(self, limiter):
        limiter.publish_history["xiaohongshu"].append(datetime.now())
        limiter.publish_history["weibo"].append(datetime.now())

        await limiter.reset("xiaohongshu")
        assert len(limiter.publish_history["xiaohongshu"]) == 0
        assert len(limiter.publish_history["weibo"]) == 1

    async def test_reset_all(self, limiter):
        limiter.publish_history["xiaohongshu"].append(datetime.now())
        limiter.publish_history["weibo"].append(datetime.now())

        await limiter.reset()
        assert len(limiter.publish_history["xiaohongshu"]) == 0
        assert len(limiter.publish_history["weibo"]) == 0


class TestSingleton:
    async def test_get_rate_limiter(self):
        import src.services.rate_limiter as mod
        mod._rate_limiter = None
        rl = await get_rate_limiter()
        assert isinstance(rl, RateLimiter)
        rl2 = await get_rate_limiter()
        assert rl is rl2
        mod._rate_limiter = None
