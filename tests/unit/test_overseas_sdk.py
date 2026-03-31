"""
Tests for overseas_sdk module.

Covers:
- PlatformSDK dataclass and SDK_INFO
- RedditSDKTool, TwitterSDKTool, InstagramSDKTool, FacebookSDKTool, ThreadsSDKTool
- Factory: get_overseas_sdk_tool
- install_sdk_dependencies
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.tools.base_tool import ToolStatus
from src.tools.platform.overseas_sdk import (
    FacebookSDKTool,
    InstagramSDKTool,
    PlatformSDK,
    RedditSDKTool,
    SDK_INFO,
    ThreadsSDKTool,
    TwitterSDKTool,
    get_overseas_sdk_tool,
    install_sdk_dependencies,
)
from src.tools.platform.base import ContentType, PublishContent


# ============ PlatformSDK & SDK_INFO ============


class TestPlatformSDK:
    def test_create(self):
        sdk = PlatformSDK(name="Test", package="test", install_cmd="pip install test", docs_url="http://docs", github_stars=100)
        assert sdk.name == "Test"
        assert sdk.package == "test"

    def test_sdk_info_all_platforms(self):
        expected = {"reddit", "twitter", "instagram", "facebook", "threads"}
        assert expected == set(SDK_INFO.keys())

    def test_sdk_info_fields(self):
        for platform, info in SDK_INFO.items():
            assert info.name
            assert info.package
            assert info.install_cmd.startswith("pip install")
            assert info.docs_url.startswith("http")
            assert info.github_stars > 0


# ============ RedditSDKTool ============


class TestRedditSDKTool:
    def test_init_default(self):
        tool = RedditSDKTool()
        assert tool.platform == "reddit"
        assert tool.max_title_length == 300
        assert tool._reddit is None

    def test_init_with_config(self):
        tool = RedditSDKTool({"reddit_client_id": "cid", "reddit_username": "user"})
        assert tool._client_id == "cid"
        assert tool._username == "user"

    def test_get_client_import_error(self):
        tool = RedditSDKTool()
        with patch.dict("sys.modules", {"praw": None}):
            with pytest.raises(ImportError, match="PRAW 未安装"):
                tool._get_client()

    def test_authenticate_failure(self):
        tool = RedditSDKTool()
        mock_reddit = MagicMock()
        mock_reddit.user.me.side_effect = Exception("auth failed")
        tool._reddit = mock_reddit
        result = tool.authenticate()
        assert result.status.value == "failed"

    def test_authenticate_success(self):
        tool = RedditSDKTool({"reddit_username": "testuser"})
        mock_reddit = MagicMock()
        mock_reddit.user.me.return_value = MagicMock()
        tool._reddit = mock_reddit
        result = tool.authenticate()
        assert result.status.value == "success"

    def test_publish_no_subreddit(self):
        tool = RedditSDKTool()
        mock_reddit = MagicMock()
        tool._reddit = mock_reddit
        content = PublishContent(title="Test", body="Body")
        result = tool.publish(content)
        assert result.status.value == "failed"
        assert "Subreddit" in result.error

    def test_publish_text_success(self):
        tool = RedditSDKTool()
        mock_submission = MagicMock()
        mock_submission.id = "abc123"
        mock_submission.permalink = "/r/test/comments/abc123/title"
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit.return_value = mock_submission
        tool._reddit = mock_reddit
        content = PublishContent(title="Test", body="Body", custom_fields={"subreddit": "test"})
        result = tool.publish(content)
        assert result.status.value == "success"
        assert result.content_id == "abc123"

    def test_publish_image_success(self):
        tool = RedditSDKTool()
        mock_submission = MagicMock()
        mock_submission.id = "img123"
        mock_submission.permalink = "/r/test/comments/img123/title"
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit_image.return_value = mock_submission
        tool._reddit = mock_reddit
        content = PublishContent(title="Test", body="Body", images=["img.jpg"], custom_fields={"subreddit": "test"})
        result = tool.publish(content)
        assert result.status.value == "success"

    def test_publish_exception(self):
        tool = RedditSDKTool()
        mock_reddit = MagicMock()
        mock_reddit.subreddit.side_effect = Exception("API error")
        tool._reddit = mock_reddit
        content = PublishContent(title="Test", body="Body", custom_fields={"subreddit": "test"})
        result = tool.publish(content)
        assert result.status.value == "failed"

    def test_get_analytics_success(self):
        tool = RedditSDKTool()
        mock_submission = MagicMock()
        mock_submission.score = 100
        mock_submission.upvote_ratio = 0.95
        mock_submission.num_comments = 50
        mock_submission.total_awards_received = 2
        mock_submission.view_count = 1000
        mock_reddit = MagicMock()
        mock_reddit.submission.return_value = mock_submission
        tool._reddit = mock_reddit
        result = tool.get_analytics("abc")
        assert result["upvotes"] == 100
        assert result["comments"] == 50

    def test_get_analytics_error(self):
        tool = RedditSDKTool()
        mock_reddit = MagicMock()
        mock_reddit.submission.side_effect = Exception("not found")
        tool._reddit = mock_reddit
        result = tool.get_analytics("abc")
        assert "error" in result

    def test_schedule(self):
        tool = RedditSDKTool()
        result = tool.schedule(PublishContent(title="T", body="B"), datetime.now())
        assert result.status.value == "failed"
        assert "不支持" in result.error


# ============ TwitterSDKTool ============


class TestTwitterSDKTool:
    def test_init(self):
        tool = TwitterSDKTool()
        assert tool.platform == "twitter"
        assert tool.max_body_length == 280

    def test_init_with_config(self):
        tool = TwitterSDKTool({"twitter_api_key": "key", "twitter_bearer_token": "bearer"})
        assert tool._api_key == "key"
        assert tool._bearer_token == "bearer"

    def test_get_client_import_error(self):
        tool = TwitterSDKTool()
        with patch.dict("sys.modules", {"tweepy": None}):
            with pytest.raises(ImportError, match="Tweepy 未安装"):
                tool._get_client()

    def test_authenticate_success(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_client.get_me.return_value = MagicMock(data=MagicMock(username="testuser"))
        tool._client = mock_client
        result = tool.authenticate()
        assert result.status.value == "success"
        assert "testuser" in result.status_detail

    def test_authenticate_failure(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_client.get_me.side_effect = Exception("auth error")
        tool._client = mock_client
        result = tool.authenticate()
        assert result.status.value == "failed"

    def test_publish_text(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": "12345"})
        mock_client.get_me.return_value = MagicMock(data=MagicMock(username="user"))
        tool._client = mock_client
        content = PublishContent(title="", body="Short tweet")
        result = tool.publish(content)
        assert result.status.value == "success"
        assert result.content_id == "12345"

    def test_publish_exception(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_client.create_tweet.side_effect = Exception("rate limited")
        tool._client = mock_client
        content = PublishContent(title="", body="Test")
        result = tool.publish(content)
        assert result.status.value == "failed"

    def test_split_to_thread(self):
        tool = TwitterSDKTool()
        text = "A" * 300  # Over 280 limit
        tweets = tool._split_to_thread(text, 280)
        assert len(tweets) >= 2
        # All text should be preserved
        assert sum(len(t) for t in tweets) == 300

    def test_split_to_thread_with_punctuation(self):
        tool = TwitterSDKTool()
        text = "A" * 200 + "。" + "B" * 200
        tweets = tool._split_to_thread(text, 280)
        assert len(tweets) >= 2

    def test_get_analytics_success(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_tweet_data = MagicMock()
        mock_tweet_data.public_metrics = {"like_count": 10, "retweet_count": 5, "reply_count": 2, "quote_count": 1}
        mock_tweet_data.non_public_metrics = {"impression_count": 1000}
        mock_client.get_tweet.return_value = MagicMock(data=mock_tweet_data)
        tool._client = mock_client
        result = tool.get_analytics("123")
        assert result["likes"] == 10

    def test_get_analytics_error(self):
        tool = TwitterSDKTool()
        mock_client = MagicMock()
        mock_client.get_tweet.side_effect = Exception("not found")
        tool._client = mock_client
        result = tool.get_analytics("123")
        assert "error" in result

    def test_schedule(self):
        tool = TwitterSDKTool()
        result = tool.schedule(PublishContent(title="", body="T"), datetime.now())
        assert result.status.value == "failed"


# ============ InstagramSDKTool ============


class TestInstagramSDKTool:
    def test_init(self):
        tool = InstagramSDKTool()
        assert tool.platform == "instagram"
        assert tool.max_images == 10

    def test_init_with_config(self):
        tool = InstagramSDKTool({"instagram_username": "user", "instagram_password": "pass"})
        assert tool._username == "user"

    def test_get_client_import_error(self):
        tool = InstagramSDKTool()
        with patch.dict("sys.modules", {"instagrapi": None}):
            with pytest.raises(ImportError, match="instagrapi 未安装"):
                tool._get_client()

    def test_authenticate_success(self):
        tool = InstagramSDKTool({"instagram_username": "user", "instagram_password": "pass"})
        mock_cl = MagicMock()
        tool._cl = mock_cl
        result = tool.authenticate()
        assert result.status.value == "success"

    def test_authenticate_failure(self):
        tool = InstagramSDKTool({"instagram_username": "user", "instagram_password": "pass"})
        mock_cl = MagicMock()
        mock_cl.login.side_effect = Exception("bad password")
        tool._cl = mock_cl
        result = tool.authenticate()
        assert result.status.value == "failed"

    def test_publish_no_media(self):
        tool = InstagramSDKTool()
        content = PublishContent(title="", body="No image")
        result = tool.publish(content)
        assert result.status.value == "failed"
        assert "图片或视频" in result.error

    def test_publish_single_image(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_cl.photo_upload.return_value = MagicMock(pk="12345")
        tool._cl = mock_cl
        content = PublishContent(title="", body="Caption", images=["img.jpg"])
        result = tool.publish(content)
        assert result.status.value == "success"

    def test_publish_carousel(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_cl.album_upload.return_value = MagicMock(pk="12345")
        tool._cl = mock_cl
        content = PublishContent(title="", body="Caption", images=["img1.jpg", "img2.jpg"])
        result = tool.publish(content)
        assert result.status.value == "success"

    def test_publish_video(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_cl.video_upload.return_value = MagicMock(pk="12345")
        tool._cl = mock_cl
        content = PublishContent(title="", body="Caption", video="video.mp4")
        result = tool.publish(content)
        assert result.status.value == "success"
        assert "reel" in result.content_url

    def test_publish_exception(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_cl.photo_upload.side_effect = Exception("upload failed")
        tool._cl = mock_cl
        content = PublishContent(title="", body="Caption", images=["img.jpg"])
        result = tool.publish(content)
        assert result.status.value == "failed"

    def test_get_analytics_success(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_info = MagicMock()
        mock_info.like_count = 100
        mock_info.comment_count = 50
        mock_info.play_count = 1000
        mock_cl.media_info.return_value = mock_info
        tool._cl = mock_cl
        result = tool.get_analytics("12345")
        assert result["likes"] == 100

    def test_get_analytics_error(self):
        tool = InstagramSDKTool()
        mock_cl = MagicMock()
        mock_cl.media_info.side_effect = Exception("not found")
        tool._cl = mock_cl
        result = tool.get_analytics("12345")
        assert "error" in result

    def test_schedule(self):
        tool = InstagramSDKTool()
        result = tool.schedule(PublishContent(title="", body="T", images=["i.jpg"]), datetime.now())
        assert result.status.value == "failed"


# ============ FacebookSDKTool ============


class TestFacebookSDKTool:
    def test_init(self):
        tool = FacebookSDKTool()
        assert tool.platform == "facebook"
        assert tool.max_body_length == 63206

    def test_init_with_config(self):
        tool = FacebookSDKTool({"facebook_access_token": "token", "facebook_page_id": "page1"})
        assert tool._access_token == "token"
        assert tool._page_id == "page1"

    def test_get_client_import_error(self):
        tool = FacebookSDKTool()
        with patch.dict("sys.modules", {"facebook": None}):
            with pytest.raises(ImportError, match="facebook-sdk 未安装"):
                tool._get_client()

    def test_authenticate_success(self):
        tool = FacebookSDKTool()
        mock_graph = MagicMock()
        mock_graph.get_object.return_value = {"name": "Test Page"}
        tool._graph = mock_graph
        result = tool.authenticate()
        assert result.status.value == "success"

    def test_authenticate_failure(self):
        tool = FacebookSDKTool()
        mock_graph = MagicMock()
        mock_graph.get_object.side_effect = Exception("invalid token")
        tool._graph = mock_graph
        result = tool.authenticate()
        assert result.status.value == "failed"

    def test_publish_text(self):
        tool = FacebookSDKTool({"facebook_page_id": "page1"})
        mock_graph = MagicMock()
        mock_graph.put_object.return_value = {"id": "page1_12345"}
        tool._graph = mock_graph
        content = PublishContent(title="", body="Text post")
        result = tool.publish(content)
        assert result.status.value == "success"

    def test_publish_exception(self):
        tool = FacebookSDKTool({"facebook_page_id": "page1"})
        mock_graph = MagicMock()
        mock_graph.put_object.side_effect = Exception("API error")
        tool._graph = mock_graph
        content = PublishContent(title="", body="Text post")
        result = tool.publish(content)
        assert result.status.value == "failed"

    def test_get_analytics_success(self):
        tool = FacebookSDKTool()
        mock_graph = MagicMock()
        mock_graph.get_object.return_value = {
            "reactions": {"summary": {"total_count": 50}},
            "comments": {"summary": {"total_count": 10}},
            "shares": {"count": 5},
        }
        tool._graph = mock_graph
        result = tool.get_analytics("post1")
        assert result["reactions"] == 50

    def test_get_analytics_error(self):
        tool = FacebookSDKTool()
        mock_graph = MagicMock()
        mock_graph.get_object.side_effect = Exception("error")
        tool._graph = mock_graph
        result = tool.get_analytics("post1")
        assert "error" in result

    def test_schedule(self):
        tool = FacebookSDKTool()
        result = tool.schedule(PublishContent(title="", body="T"), datetime.now())
        assert result.status.value == "success"


# ============ ThreadsSDKTool ============


class TestThreadsSDKTool:
    def test_init(self):
        tool = ThreadsSDKTool()
        assert tool.platform == "threads"
        assert tool.max_body_length == 500

    def test_authenticate_with_token(self):
        tool = ThreadsSDKTool({"threads_access_token": "token123"})
        result = tool.authenticate()
        assert result.status.value == "success"

    def test_authenticate_no_token(self):
        tool = ThreadsSDKTool()
        result = tool.authenticate()
        assert result.status.value == "failed"

    def test_publish_text(self):
        tool = ThreadsSDKTool({"threads_access_token": "token", "threads_user_id": "user1"})
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=MagicMock(return_value={"id": "container1"})),
                MagicMock(json=MagicMock(return_value={"id": "thread1"})),
            ]
            content = PublishContent(title="", body="Hello Threads")
            result = tool.publish(content)
            assert result.status.value == "success"

    def test_publish_with_image(self):
        tool = ThreadsSDKTool({"threads_access_token": "token", "threads_user_id": "user1"})
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=MagicMock(return_value={"id": "container1"})),
                MagicMock(json=MagicMock(return_value={"id": "thread1"})),
            ]
            content = PublishContent(title="", body="Image thread", images=["img.jpg"])
            result = tool.publish(content)
            assert result.status.value == "success"

    def test_publish_exception(self):
        tool = ThreadsSDKTool({"threads_access_token": "token", "threads_user_id": "user1"})
        with patch("httpx.post", side_effect=Exception("network error")):
            content = PublishContent(title="", body="Test")
            result = tool.publish(content)
            assert result.status.value == "failed"

    def test_get_analytics(self):
        tool = ThreadsSDKTool()
        result = tool.get_analytics("thread1")
        assert result["platform"] == "threads"
        assert result["likes"] == 0

    def test_schedule(self):
        tool = ThreadsSDKTool()
        result = tool.schedule(PublishContent(title="", body="T"), datetime.now())
        assert result.status.value == "failed"


# ============ Factory ============


class TestGetOverseasSDKTool:
    def test_reddit(self):
        tool = get_overseas_sdk_tool("reddit")
        assert isinstance(tool, RedditSDKTool)

    def test_twitter(self):
        tool = get_overseas_sdk_tool("twitter")
        assert isinstance(tool, TwitterSDKTool)

    def test_x_alias(self):
        tool = get_overseas_sdk_tool("x")
        assert isinstance(tool, TwitterSDKTool)

    def test_instagram(self):
        tool = get_overseas_sdk_tool("instagram")
        assert isinstance(tool, InstagramSDKTool)

    def test_facebook(self):
        tool = get_overseas_sdk_tool("facebook")
        assert isinstance(tool, FacebookSDKTool)

    def test_threads(self):
        tool = get_overseas_sdk_tool("threads")
        assert isinstance(tool, ThreadsSDKTool)

    def test_case_insensitive(self):
        tool = get_overseas_sdk_tool("REDDIT")
        assert isinstance(tool, RedditSDKTool)

    def test_invalid(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_overseas_sdk_tool("tiktok")

    def test_with_config(self):
        tool = get_overseas_sdk_tool("reddit", {"reddit_client_id": "cid"})
        assert tool._client_id == "cid"


# ============ install_sdk_dependencies ============


class TestInstallSDKDependencies:
    def test_all_platforms(self, capsys):
        install_sdk_dependencies()
        output = capsys.readouterr().out
        assert "PRAW" in output
        assert "Tweepy" in output
        assert "instagrapi" in output

    def test_specific_platforms(self, capsys):
        install_sdk_dependencies(["reddit", "twitter"])
        output = capsys.readouterr().out
        assert "PRAW" in output
        assert "Tweepy" in output
        assert "instagrapi" not in output

    def test_unknown_platform_skipped(self, capsys):
        install_sdk_dependencies(["unknown"])
        output = capsys.readouterr().out
        assert output.strip() == "# 安装海外平台 SDK 依赖"
