"""
Tests for platform search tools — successful API and skill-based paths.

Covers the code paths that require mocked httpx responses or subprocess calls,
complementing the basic/fallback tests in test_platform_search.py.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.search.platform_search import (
    BilibiliSearch,
    DouyinSearch,
    SearchPost,
    SearchResponse,
    WeiboSearch,
    XiaohongshuSearch,
    ZhihuSearch,
    search_all_platforms,
)


# ============================================================================
# XiaohongshuSearch — API key path
# ============================================================================

class TestXiaohongshuSearchAPI:
    """Test XiaohongshuSearch.search() when an API key is provided."""

    def _make_api_response(self, items):
        """Helper: build a fake httpx response with the given items."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"items": items}}
        return mock_resp

    @patch("httpx.get")
    def test_search_single_item(self, mock_get):
        """One note comes back — verify SearchPost fields."""
        mock_get.return_value = self._make_api_response([
            {
                "note": {
                    "id": "note_001",
                    "title": "Test Title",
                    "desc": "Some content here",
                    "user": {"nickname": "Alice", "user_id": "u_alice"},
                    "time": "2026-03-01",
                    "liked_count": 120,
                    "comment_count": 30,
                    "share_count": 10,
                    "view_count": 5000,
                    "image_list": ["img1.jpg", "img2.jpg"],
                }
            }
        ])

        searcher = XiaohongshuSearch(api_key="test-key-123")
        result = searcher.search("keyword", limit=10, sort="hot")

        # Verify API was called correctly
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer test-key-123"
        assert call_kwargs[1]["params"]["keyword"] == "keyword"
        assert call_kwargs[1]["params"]["limit"] == 10

        # Verify response
        assert isinstance(result, SearchResponse)
        assert result.platform == "xiaohongshu"
        assert result.keyword == "keyword"
        assert result.total == 1
        assert len(result.posts) == 1

        post = result.posts[0]
        assert isinstance(post, SearchPost)
        assert post.platform == "xiaohongshu"
        assert post.post_id == "note_001"
        assert post.title == "Test Title"
        assert post.content == "Some content here"
        assert post.author == "Alice"
        assert post.author_id == "u_alice"
        assert post.publish_time == "2026-03-01"
        assert post.url == "https://www.xiaohongshu.com/explore/note_001"
        assert post.likes == 120
        assert post.comments == 30
        assert post.shares == 10
        assert post.views == 5000
        assert post.images == ["img1.jpg", "img2.jpg"]

    @patch("httpx.get")
    def test_search_multiple_items(self, mock_get):
        """Multiple notes returned."""
        items = [
            {"note": {"id": f"n{i}", "title": f"T{i}", "desc": f"D{i}",
                       "user": {"nickname": f"U{i}", "user_id": f"uid{i}"},
                       "time": "2026-01-01", "liked_count": i * 10,
                       "comment_count": i, "share_count": 0, "view_count": 0,
                       "image_list": []}}
            for i in range(5)
        ]
        mock_get.return_value = self._make_api_response(items)

        searcher = XiaohongshuSearch(api_key="key")
        result = searcher.search("multi")

        assert result.total == 5
        assert len(result.posts) == 5
        assert result.posts[2].post_id == "n2"
        assert result.posts[2].likes == 20

    @patch("httpx.get")
    def test_search_empty_items(self, mock_get):
        """API returns empty items list."""
        mock_get.return_value = self._make_api_response([])

        searcher = XiaohongshuSearch(api_key="key")
        result = searcher.search("nothing")

        assert result.total == 0
        assert result.posts == []

    @patch("httpx.get")
    def test_search_missing_fields_use_defaults(self, mock_get):
        """Note with missing fields falls back to defaults."""
        mock_get.return_value = self._make_api_response([
            {"note": {}}  # All fields missing
        ])

        searcher = XiaohongshuSearch(api_key="key")
        result = searcher.search("sparse")

        assert result.total == 1
        post = result.posts[0]
        assert post.post_id == ""
        assert post.title == ""
        assert post.content == ""
        assert post.author == ""
        assert post.author_id == ""
        assert post.likes == 0
        assert post.url == "https://www.xiaohongshu.com/explore/"

    @patch("httpx.get")
    def test_search_no_data_key(self, mock_get):
        """API response with no 'data' key — should produce empty results."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        searcher = XiaohongshuSearch(api_key="key")
        result = searcher.search("bad_response")

        assert result.total == 0
        assert result.posts == []


# ============================================================================
# XiaohongshuSearch — skill fallback path
# ============================================================================

class TestXiaohongshuSearchSkill:
    """Test XiaohongshuSearch._search_via_skill()."""

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_via_skill_runs_subprocess(self, mock_exists, mock_run):
        """Skill path exists — subprocess is invoked."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        searcher = XiaohongshuSearch(api_key="")  # No API key → skill fallback
        result = searcher.search("test_skill", limit=15)

        # subprocess.run should have been called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "python" in call_args[0]
        assert "test_skill" in call_args
        assert "--limit" in call_args
        assert "15" in call_args

        # Even with skill, current implementation returns empty (parse not implemented)
        assert isinstance(result, SearchResponse)
        assert result.platform == "xiaohongshu"

    @patch.object(Path, "exists", return_value=False)
    def test_search_via_skill_no_skill_path(self, mock_exists):
        """Skill path does not exist — returns empty."""
        searcher = XiaohongshuSearch(api_key="")
        result = searcher.search("no_skill")

        assert result.total == 0
        assert result.posts == []


# ============================================================================
# WeiboSearch — skill-based path
# ============================================================================

class TestWeiboSearchSkill:
    """Test WeiboSearch.search() and get_trending() with mocked skill."""

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_parses_statuses(self, mock_exists, mock_run):
        """Skill returns valid JSON with statuses — posts are parsed."""
        fake_data = {
            "statuses": [
                {
                    "id": "wb_001",
                    "text": "This is a Weibo post about AI technology and deep learning models",
                    "user": {"screen_name": "WeiboUser1", "idstr": "uid_wb1"},
                    "created_at": "Mon Jan 01 12:00:00 +0800 2026",
                    "attitudes_count": 500,
                    "comments_count": 120,
                    "reposts_count": 80,
                },
                {
                    "id": "wb_002",
                    "text": "Another post about startups",
                    "user": {"screen_name": "WeiboUser2", "idstr": "uid_wb2"},
                    "created_at": "Tue Jan 02 14:00:00 +0800 2026",
                    "attitudes_count": 200,
                    "comments_count": 50,
                    "reposts_count": 30,
                },
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = WeiboSearch()
        result = searcher.search("AI", limit=10)

        assert result.platform == "weibo"
        assert result.keyword == "AI"
        assert result.total == 2
        assert len(result.posts) == 2

        p0 = result.posts[0]
        assert p0.post_id == "wb_001"
        assert p0.title == fake_data["statuses"][0]["text"][:50]
        assert p0.content == fake_data["statuses"][0]["text"]
        assert p0.author == "WeiboUser1"
        assert p0.author_id == "uid_wb1"
        assert p0.likes == 500
        assert p0.comments == 120
        assert p0.shares == 80
        assert "uid_wb1" in p0.url
        assert "wb_001" in p0.url

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_respects_limit(self, mock_exists, mock_run):
        """When statuses exceed limit, only limit items are returned."""
        fake_data = {
            "statuses": [
                {
                    "id": f"wb_{i}",
                    "text": f"Post {i}",
                    "user": {"screen_name": f"User{i}", "idstr": f"uid{i}"},
                    "created_at": "",
                    "attitudes_count": 0,
                    "comments_count": 0,
                    "reposts_count": 0,
                }
                for i in range(10)
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = WeiboSearch()
        result = searcher.search("test", limit=3)

        assert result.total == 3
        assert len(result.posts) == 3

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_invalid_json_returns_empty(self, mock_exists, mock_run):
        """Subprocess returns non-JSON stdout — falls through to empty."""
        mock_run.return_value = MagicMock(
            stdout="not valid json", stderr="", returncode=1
        )

        searcher = WeiboSearch()
        result = searcher.search("broken")

        assert result.total == 0
        assert result.posts == []

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_get_trending_parses_hot_list(self, mock_exists, mock_run):
        """get_trending returns parsed hot_list."""
        fake_data = {
            "hot_list": [
                {"title": "Trending 1", "rank": 1, "hot_value": 9999},
                {"title": "Trending 2", "rank": 2, "hot_value": 8888},
                {"title": "Trending 3", "rank": 3, "hot_value": 7777},
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = WeiboSearch()
        result = searcher.get_trending(limit=2)

        assert len(result) == 2
        assert result[0]["title"] == "Trending 1"
        assert result[1]["rank"] == 2

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_get_trending_invalid_json_returns_empty(self, mock_exists, mock_run):
        """get_trending with bad JSON returns empty list."""
        mock_run.return_value = MagicMock(stdout="bad json", stderr="", returncode=1)

        searcher = WeiboSearch()
        result = searcher.get_trending()

        assert result == []

    @patch.object(Path, "exists", return_value=False)
    def test_get_trending_no_skill_returns_empty(self, mock_exists):
        """get_trending with no skill path returns empty list."""
        searcher = WeiboSearch()
        result = searcher.get_trending()
        assert result == []


# ============================================================================
# ZhihuSearch — skill-based path
# ============================================================================

class TestZhihuSearchSkill:
    """Test ZhihuSearch.search() and get_trending() with mocked skill."""

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_parses_results(self, mock_exists, mock_run):
        """Skill returns valid JSON with results — posts are parsed."""
        fake_data = {
            "results": [
                {
                    "id": "zh_001",
                    "title": "How to learn Python?",
                    "excerpt": "Python is a versatile language...",
                    "author": {"name": "ZhihuExpert", "id": "zid_001"},
                    "created_time": "2026-01-15T10:00:00",
                    "url": "https://www.zhihu.com/question/12345/answer/67890",
                    "voteup_count": 350,
                    "comment_count": 45,
                },
                {
                    "id": "zh_002",
                    "question": {"title": "Question from nested field"},
                    "content": "Full content that is longer than excerpt...",
                    "author": {"name": "AnotherUser", "id": "zid_002"},
                    "created_time": "2026-02-01T08:30:00",
                    "url": "https://www.zhihu.com/question/54321",
                    "voteup_count": 100,
                    "comment_count": 12,
                },
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = ZhihuSearch()
        result = searcher.search("Python", limit=20)

        assert result.platform == "zhihu"
        assert result.keyword == "Python"
        assert result.total == 2
        assert len(result.posts) == 2

        # First post — uses title directly
        p0 = result.posts[0]
        assert p0.post_id == "zh_001"
        assert p0.title == "How to learn Python?"
        assert "versatile" in p0.content
        assert p0.author == "ZhihuExpert"
        assert p0.author_id == "zid_001"
        assert p0.likes == 350
        assert p0.comments == 45
        assert p0.url == "https://www.zhihu.com/question/12345/answer/67890"

        # Second post — title falls back to question.title, content from "content"
        p1 = result.posts[1]
        assert p1.title == "Question from nested field"
        assert "Full content" in p1.content

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_respects_limit(self, mock_exists, mock_run):
        """Limit is respected when results exceed it."""
        fake_data = {
            "results": [
                {"id": f"zh_{i}", "title": f"Q{i}", "excerpt": "",
                 "author": {"name": "", "id": ""}, "created_time": "",
                 "url": "", "voteup_count": 0, "comment_count": 0}
                for i in range(10)
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = ZhihuSearch()
        result = searcher.search("test", limit=4)

        assert result.total == 4
        assert len(result.posts) == 4

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_search_invalid_json_returns_empty(self, mock_exists, mock_run):
        """Invalid JSON falls back to empty result."""
        mock_run.return_value = MagicMock(stdout="{{bad", stderr="", returncode=1)

        searcher = ZhihuSearch()
        result = searcher.search("broken")

        assert result.total == 0
        assert result.posts == []

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_get_trending_parses_hot_list(self, mock_exists, mock_run):
        """get_trending returns parsed hot_list items."""
        fake_data = {
            "hot_list": [
                {"title": "Hot topic 1", "hot_value": 5000},
                {"title": "Hot topic 2", "hot_value": 4000},
                {"title": "Hot topic 3", "hot_value": 3000},
                {"title": "Hot topic 4", "hot_value": 2000},
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(fake_data), stderr="", returncode=0
        )

        searcher = ZhihuSearch()
        result = searcher.get_trending(limit=3)

        assert len(result) == 3
        assert result[0]["title"] == "Hot topic 1"
        assert result[2]["hot_value"] == 3000

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_get_trending_invalid_json_returns_empty(self, mock_exists, mock_run):
        """get_trending with bad JSON returns empty list."""
        mock_run.return_value = MagicMock(stdout="nope", stderr="", returncode=1)

        searcher = ZhihuSearch()
        result = searcher.get_trending()

        assert result == []

    @patch.object(Path, "exists", return_value=False)
    def test_get_trending_no_skill_returns_empty(self, mock_exists):
        """No skill file — returns empty list."""
        searcher = ZhihuSearch()
        result = searcher.get_trending()
        assert result == []


# ============================================================================
# DouyinSearch — API key path
# ============================================================================

class TestDouyinSearchAPI:
    """Test DouyinSearch.search() when an API key is provided."""

    @patch("httpx.get")
    def test_search_parses_videos(self, mock_get):
        """API returns video data — verify SearchPost fields."""
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": [
                {
                    "video": {
                        "aweme_id": "dy_001",
                        "desc": "Amazing Douyin video about cooking",
                        "create_time": "1706745600",
                    },
                    "author": {
                        "nickname": "ChefWang",
                        "sec_uid": "sec_wang",
                    },
                    "statistics": {
                        "digg_count": 10000,
                        "comment_count": 800,
                        "share_count": 300,
                        "play_count": 500000,
                    },
                },
                {
                    "video": {
                        "aweme_id": "dy_002",
                        "desc": "Travel vlog",
                        "create_time": "1706832000",
                    },
                    "author": {
                        "nickname": "Traveler",
                        "sec_uid": "sec_travel",
                    },
                    "statistics": {
                        "digg_count": 5000,
                        "comment_count": 200,
                        "share_count": 100,
                        "play_count": 200000,
                    },
                },
            ]
        }
        mock_get.return_value = fake_response

        searcher = DouyinSearch(api_key="dy-key-abc")
        result = searcher.search("cooking", limit=10)

        # Verify API call
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer dy-key-abc"
        assert call_kwargs[1]["params"]["keyword"] == "cooking"
        assert call_kwargs[1]["params"]["count"] == 10

        # Verify response
        assert result.platform == "douyin"
        assert result.total == 2
        assert len(result.posts) == 2

        p0 = result.posts[0]
        assert p0.post_id == "dy_001"
        assert p0.title == "Amazing Douyin video about cooking"
        assert p0.content == "Amazing Douyin video about cooking"
        assert p0.author == "ChefWang"
        assert p0.author_id == "sec_wang"
        assert p0.likes == 10000
        assert p0.comments == 800
        assert p0.shares == 300
        assert p0.views == 500000
        assert p0.url == "https://www.douyin.com/video/dy_001"

    @patch("httpx.get")
    def test_search_empty_data(self, mock_get):
        """API returns empty data list."""
        fake_response = MagicMock()
        fake_response.json.return_value = {"data": []}
        mock_get.return_value = fake_response

        searcher = DouyinSearch(api_key="key")
        result = searcher.search("nothing")

        assert result.total == 0
        assert result.posts == []

    @patch("httpx.get")
    def test_search_missing_nested_fields(self, mock_get):
        """Video item with missing sub-dicts uses defaults."""
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": [
                {
                    "video": {},
                    "author": {},
                    "statistics": {},
                }
            ]
        }
        mock_get.return_value = fake_response

        searcher = DouyinSearch(api_key="key")
        result = searcher.search("sparse")

        assert result.total == 1
        post = result.posts[0]
        assert post.post_id == ""
        assert post.author == ""
        assert post.likes == 0

    @patch("httpx.get")
    def test_search_respects_limit(self, mock_get):
        """When API returns more than limit, only limit items are kept."""
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": [
                {"video": {"aweme_id": f"dy_{i}", "desc": f"V{i}", "create_time": ""},
                 "author": {"nickname": "", "sec_uid": ""},
                 "statistics": {"digg_count": 0, "comment_count": 0,
                                "share_count": 0, "play_count": 0}}
                for i in range(10)
            ]
        }
        mock_get.return_value = fake_response

        searcher = DouyinSearch(api_key="key")
        result = searcher.search("many", limit=5)

        assert result.total == 5
        assert len(result.posts) == 5


# ============================================================================
# BilibiliSearch — API key path
# ============================================================================

class TestBilibiliSearchAPI:
    """Test BilibiliSearch.search() when an API key is provided."""

    @patch("httpx.get")
    def test_search_parses_results(self, mock_get):
        """API returns result data — verify SearchPost fields."""
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": {
                "result": [
                    {
                        "aid": 12345678,
                        "title": '<em class="keyword">Python</em> tutorial',
                        "description": "Learn Python step by step",
                        "author": "BiliUploader",
                        "mid": 9876543,
                        "pubdate": 1706745600,
                        "like": 3000,
                        "review": 150,
                        "favorite": 800,
                        "play": 100000,
                    },
                    {
                        "aid": 87654321,
                        "title": "No highlight title",
                        "description": "Second video",
                        "author": "AnotherUp",
                        "mid": 1111111,
                        "pubdate": 1706832000,
                        "like": 1500,
                        "review": 80,
                        "favorite": 400,
                        "play": 50000,
                    },
                ]
            }
        }
        mock_get.return_value = fake_response

        searcher = BilibiliSearch(api_key="bili-key-xyz")
        result = searcher.search("Python", limit=20)

        # Verify API call
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer bili-key-xyz"
        assert call_kwargs[1]["params"]["keyword"] == "Python"

        # Verify response
        assert result.platform == "bilibili"
        assert result.total == 2
        assert len(result.posts) == 2

        p0 = result.posts[0]
        assert p0.post_id == "12345678"
        # Title should have <em> tags stripped
        assert p0.title == "Python tutorial"
        assert "<em" not in p0.title
        assert p0.content == "Learn Python step by step"
        assert p0.author == "BiliUploader"
        assert p0.author_id == "9876543"
        assert p0.publish_time == "1706745600"
        assert p0.url == "https://www.bilibili.com/video/av12345678"
        assert p0.likes == 3000
        assert p0.comments == 150
        assert p0.shares == 800  # mapped from favorite
        assert p0.views == 100000

    @patch("httpx.get")
    def test_search_empty_results(self, mock_get):
        """API returns empty result list."""
        fake_response = MagicMock()
        fake_response.json.return_value = {"data": {"result": []}}
        mock_get.return_value = fake_response

        searcher = BilibiliSearch(api_key="key")
        result = searcher.search("nothing")

        assert result.total == 0
        assert result.posts == []

    @patch("httpx.get")
    def test_search_no_result_key(self, mock_get):
        """API response missing 'result' key in data."""
        fake_response = MagicMock()
        fake_response.json.return_value = {"data": {}}
        mock_get.return_value = fake_response

        searcher = BilibiliSearch(api_key="key")
        result = searcher.search("missing_key")

        assert result.total == 0
        assert result.posts == []

    @patch("httpx.get")
    def test_search_respects_limit(self, mock_get):
        """When result list exceeds limit, only limit items are kept."""
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": {
                "result": [
                    {"aid": i, "title": f"V{i}", "description": "",
                     "author": "", "mid": 0, "pubdate": 0,
                     "like": 0, "review": 0, "favorite": 0, "play": 0}
                    for i in range(10)
                ]
            }
        }
        mock_get.return_value = fake_response

        searcher = BilibiliSearch(api_key="key")
        result = searcher.search("many", limit=4)

        assert result.total == 4
        assert len(result.posts) == 4


# ============================================================================
# search_all_platforms — exception handling
# ============================================================================

class TestSearchAllPlatformsExceptions:
    """Verify that exceptions from individual platforms don't crash the entire search."""

    @patch("src.tools.search.platform_search.PLATFORM_SEARCHERS", {
        "good_platform": MagicMock,
        "bad_platform": MagicMock,
    })
    def test_one_platform_raises_others_continue(self):
        """If one platform throws, the others still return results."""
        # Set up mocks in PLATFORM_SEARCHERS
        from src.tools.search import platform_search as mod

        good_instance = MagicMock()
        good_response = SearchResponse("good_platform", "test", 1, [
            SearchPost("good_platform", "1", "T", "C", "A", "aid", "t", "u")
        ], datetime.now())
        good_instance.search.return_value = good_response

        bad_instance = MagicMock()
        bad_instance.search.side_effect = RuntimeError("API is down")

        good_class = MagicMock(return_value=good_instance)
        bad_class = MagicMock(return_value=bad_instance)

        with patch.dict(mod.PLATFORM_SEARCHERS, {
            "good_platform": good_class,
            "bad_platform": bad_class,
        }, clear=True):
            results = search_all_platforms("test", limit=5)

        assert "good_platform" in results
        assert results["good_platform"].total == 1

        assert "bad_platform" in results
        assert results["bad_platform"].total == 0  # Fallback empty response

    def test_all_platforms_work_without_exception(self):
        """Normal call returns results for all registered platforms."""
        results = search_all_platforms("test_keyword", limit=5)

        # All registered platforms should have entries
        from src.tools.search.platform_search import PLATFORM_SEARCHERS
        for platform in PLATFORM_SEARCHERS:
            assert platform in results
            assert isinstance(results[platform], SearchResponse)

    @patch("src.tools.search.platform_search.PLATFORM_SEARCHERS", {})
    def test_empty_registry_returns_empty_dict(self):
        """No registered platforms — returns empty dict."""
        from src.tools.search import platform_search as mod

        with patch.dict(mod.PLATFORM_SEARCHERS, {}, clear=True):
            results = search_all_platforms("test")

        assert results == {}


# ============================================================================
# Edge cases and searched_at timestamp
# ============================================================================

class TestSearchTimestamps:
    """Verify that searched_at is populated correctly."""

    @patch("httpx.get")
    def test_xiaohongshu_searched_at_is_recent(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"items": []}}
        mock_get.return_value = mock_resp

        before = datetime.now()
        searcher = XiaohongshuSearch(api_key="key")
        result = searcher.search("time_test")
        after = datetime.now()

        assert before <= result.searched_at <= after

    @patch("httpx.get")
    def test_douyin_searched_at_is_recent(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_get.return_value = mock_resp

        before = datetime.now()
        searcher = DouyinSearch(api_key="key")
        result = searcher.search("time_test")
        after = datetime.now()

        assert before <= result.searched_at <= after

    @patch("subprocess.run")
    @patch.object(Path, "exists", return_value=True)
    def test_weibo_searched_at_is_recent(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"statuses": []}), stderr="", returncode=0
        )

        before = datetime.now()
        searcher = WeiboSearch()
        result = searcher.search("time_test")
        after = datetime.now()

        assert before <= result.searched_at <= after
