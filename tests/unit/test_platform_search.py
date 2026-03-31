"""
Tests for platform search tools.

Covers:
- SearchPost and SearchResponse dataclasses
- BasePlatformSearch.is_available
- All platform search classes: init, search, get_user_posts, get_trending
- Factory functions: get_platform_searcher, search_all_platforms
- CompetitorMonitor
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.tools.search.platform_search import (
    BasePlatformSearch,
    BilibiliSearch,
    CompetitorMonitor,
    DouyinSearch,
    PLATFORM_SEARCHERS,
    RedditSearch,
    SearchPost,
    SearchResponse,
    TwitterSearch,
    WeiboSearch,
    XiaohongshuSearch,
    ZhihuSearch,
    get_platform_searcher,
    search_all_platforms,
)


# ============ Data Models ============

class TestSearchPost:
    def test_create(self):
        p = SearchPost(
            platform="xiaohongshu",
            post_id="123",
            title="Test",
            content="Content",
            author="Auth",
            author_id="a1",
            publish_time="2026-01-01",
            url="http://example.com",
        )
        assert p.likes == 0
        assert p.comments == 0
        assert p.views == 0
        assert p.images is None
        assert p.tags is None

    def test_with_metrics(self):
        p = SearchPost(
            platform="weibo",
            post_id="456",
            title="T",
            content="C",
            author="A",
            author_id="a2",
            publish_time="2026-01-01",
            url="http://example.com",
            likes=100,
            comments=50,
            shares=20,
            views=1000,
            images=["img1.jpg"],
            tags=["tag1"],
        )
        assert p.likes == 100
        assert p.images == ["img1.jpg"]


class TestSearchResponse:
    def test_create(self):
        r = SearchResponse(
            platform="xiaohongshu",
            keyword="test",
            total=0,
            posts=[],
            searched_at=datetime.now(),
        )
        assert r.total == 0
        assert r.posts == []


# ============ BasePlatformSearch ============

class TestBasePlatformSearch:
    def test_is_available_no_cli(self):
        class TestSearch(BasePlatformSearch):
            def search(self, keyword, limit=20, sort="hot"):
                return SearchResponse("test", keyword, 0, [], datetime.now())
            def get_user_posts(self, user_id, limit=20):
                return SearchResponse("test", user_id, 0, [], datetime.now())
            def get_trending(self, category="", limit=20):
                return []

        s = TestSearch()
        assert not s.is_available()

    @patch("shutil.which", return_value="/usr/bin/test_cli")
    def test_is_available_with_cli(self, mock_which):
        class TestSearch(BasePlatformSearch):
            def search(self, keyword, limit=20, sort="hot"):
                return SearchResponse("test", keyword, 0, [], datetime.now())
            def get_user_posts(self, user_id, limit=20):
                return SearchResponse("test", user_id, 0, [], datetime.now())
            def get_trending(self, category="", limit=20):
                return []

        s = TestSearch()
        s.cli_name = "test_cli"
        assert s.is_available() is True


# ============ XiaohongshuSearch ============

class TestXiaohongshuSearch:
    def test_init(self):
        s = XiaohongshuSearch()
        assert s.cli_name == "tikhub"

    def test_search_no_api_key_no_skill(self):
        s = XiaohongshuSearch(api_key="")
        result = s.search("test")
        assert result.platform == "xiaohongshu"
        assert result.total == 0

    def test_get_user_posts(self):
        s = XiaohongshuSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending(self):
        s = XiaohongshuSearch()
        result = s.get_trending()
        assert result == []


# ============ WeiboSearch ============

class TestWeiboSearch:
    def test_init(self):
        s = WeiboSearch()
        assert s.cli_name == "weibo_search"

    def test_search_no_skill(self):
        s = WeiboSearch()
        result = s.search("test")
        assert result.platform == "weibo"
        assert result.total == 0

    def test_get_user_posts(self):
        s = WeiboSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending_no_skill(self):
        s = WeiboSearch()
        result = s.get_trending()
        assert result == []


# ============ ZhihuSearch ============

class TestZhihuSearch:
    def test_init(self):
        s = ZhihuSearch()
        assert s.cli_name == "zhihu_search"

    def test_search_no_skill(self):
        s = ZhihuSearch()
        result = s.search("test")
        assert result.platform == "zhihu"

    def test_get_user_posts(self):
        s = ZhihuSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending_no_skill(self):
        s = ZhihuSearch()
        result = s.get_trending()
        assert result == []


# ============ DouyinSearch ============

class TestDouyinSearch:
    def test_init(self):
        s = DouyinSearch()
        assert s.cli_name == "douyin_search"

    def test_search_no_api_key(self):
        s = DouyinSearch(api_key="")
        result = s.search("test")
        assert result.platform == "douyin"
        assert result.total == 0

    def test_get_user_posts(self):
        s = DouyinSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending(self):
        s = DouyinSearch()
        result = s.get_trending()
        assert result == []


# ============ BilibiliSearch ============

class TestBilibiliSearch:
    def test_init(self):
        s = BilibiliSearch()
        assert s.cli_name == "bilibili_search"

    def test_search_no_api_key(self):
        s = BilibiliSearch(api_key="")
        result = s.search("test")
        assert result.platform == "bilibili"
        assert result.total == 0

    def test_get_user_posts(self):
        s = BilibiliSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending(self):
        s = BilibiliSearch()
        result = s.get_trending()
        assert result == []


# ============ RedditSearch ============

class TestRedditSearch:
    def test_init(self):
        s = RedditSearch()
        assert s.cli_name == "reddit_search"

    def test_search_no_praw(self):
        s = RedditSearch()
        result = s.search("test")
        assert result.platform == "reddit"
        assert result.total == 0

    def test_get_user_posts(self):
        s = RedditSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending_no_praw(self):
        s = RedditSearch()
        result = s.get_trending()
        assert result == []


# ============ TwitterSearch ============

class TestTwitterSearch:
    def test_init(self):
        s = TwitterSearch()
        assert s.cli_name == "twitter_search"

    def test_search_no_tweepy(self):
        s = TwitterSearch()
        result = s.search("test")
        assert result.platform == "twitter"
        assert result.total == 0

    def test_get_user_posts(self):
        s = TwitterSearch()
        result = s.get_user_posts("user1")
        assert result.total == 0

    def test_get_trending(self):
        s = TwitterSearch()
        result = s.get_trending()
        assert result == []


# ============ Factory ============

class TestPlatformSearcherFactory:
    def test_get_valid_platform(self):
        searcher = get_platform_searcher("xiaohongshu")
        assert isinstance(searcher, XiaohongshuSearch)

    def test_get_invalid_platform(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_platform_searcher("nonexistent")

    def test_registry_has_all_platforms(self):
        expected = {"xiaohongshu", "weibo", "zhihu", "douyin", "bilibili", "reddit", "twitter"}
        assert expected == set(PLATFORM_SEARCHERS.keys())

    def test_search_all_platforms(self):
        results = search_all_platforms("test", limit=5)
        assert "xiaohongshu" in results
        assert "weibo" in results
        assert "twitter" in results
        for k, v in results.items():
            assert isinstance(v, SearchResponse)


# ============ CompetitorMonitor ============

class TestCompetitorMonitor:
    def test_init(self):
        monitor = CompetitorMonitor({"xiaohongshu": "user1", "weibo": "user2"})
        assert len(monitor.competitors) == 2

    def test_get_competitor_posts(self):
        monitor = CompetitorMonitor({"xiaohongshu": "user1"})
        results = monitor.get_competitor_posts(limit=5)
        assert "xiaohongshu" in results

    def test_get_competitor_posts_invalid_platform(self):
        monitor = CompetitorMonitor({"invalid_platform": "user1"})
        results = monitor.get_competitor_posts()
        assert "invalid_platform" in results
        assert results["invalid_platform"].total == 0
