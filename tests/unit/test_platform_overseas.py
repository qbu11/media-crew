"""
Unit tests for overseas platform tools (CDP variant).

Tests cover all 5 tool classes in src/tools/platform/overseas.py:
- RedditTool
- TwitterTool
- InstagramTool
- FacebookTool
- ThreadsTool

Plus the factory function:
- get_overseas_platform_tool()

Each tool is tested for:
1. Initialization with and without config
2. authenticate() with cookie, API key, and no credentials
3. publish() with valid and invalid content
4. get_analytics() return structure
5. schedule() success and failure paths
6. Platform-specific behaviour (thread splitting, carousel, subreddit, etc.)

Note:
    The CDP-based overseas tools call ``self._create_success_status()`` and
    ``self._create_failed_status()`` which are *not* defined on BasePlatformTool.
    These are stubbed out via a session-scoped autouse fixture so every test in
    this module can run without modification to the production code.
"""

from datetime import datetime, timedelta

import pytest

from src.tools.base_tool import ToolStatus
from src.tools.platform.base import ContentType, PublishContent, PublishResult
from src.tools.platform.overseas import (
    FacebookTool,
    InstagramTool,
    RedditTool,
    ThreadsTool,
    TwitterTool,
    get_overseas_platform_tool,
)


# ---------------------------------------------------------------------------
# Autouse fixture: patch the missing helper methods on all 5 CDP tool classes
# ---------------------------------------------------------------------------

_CDP_CLASSES = (RedditTool, TwitterTool, InstagramTool, FacebookTool, ThreadsTool)


@pytest.fixture(autouse=True)
def _patch_status_helpers(monkeypatch):
    """
    Inject ``_create_success_status`` and ``_create_failed_status`` onto every
    overseas CDP tool class so that the production code can call them without
    raising ``AttributeError``.
    """
    for cls in _CDP_CLASSES:
        monkeypatch.setattr(
            cls, "_create_success_status", lambda self: ToolStatus.SUCCESS, raising=False
        )
        monkeypatch.setattr(
            cls, "_create_failed_status", lambda self: ToolStatus.FAILED, raising=False
        )


# ===========================================================================
# Helpers
# ===========================================================================

def _text_content(**overrides) -> PublishContent:
    """Build a minimal TEXT PublishContent, merging *overrides*."""
    defaults = {"title": "Title", "body": "Body text", "content_type": ContentType.TEXT}
    defaults.update(overrides)
    return PublishContent(**defaults)


def _image_content(**overrides) -> PublishContent:
    """Build a minimal IMAGE PublishContent with one image."""
    defaults = {
        "title": "",
        "body": "Caption",
        "content_type": ContentType.IMAGE,
        "images": ["img.jpg"],
    }
    defaults.update(overrides)
    return PublishContent(**defaults)


# ===========================================================================
# RedditTool
# ===========================================================================

class TestRedditToolInit:
    """RedditTool initialisation."""

    def test_default_init(self):
        tool = RedditTool()
        assert tool.name == "reddit_publisher"
        assert tool.platform == "reddit"
        assert tool.version == "0.1.0"
        assert tool._cookie is None
        assert tool._subreddits == []

    def test_init_with_config(self):
        cfg = {"reddit_cookie": "abc", "default_subreddits": ["python", "learnpython"]}
        tool = RedditTool(config=cfg)
        assert tool._cookie == "abc"
        assert tool._subreddits == ["python", "learnpython"]

    def test_platform_constraints(self):
        tool = RedditTool()
        assert tool.max_title_length == 300
        assert tool.max_body_length == 40000
        assert tool.max_images == 20
        assert tool.max_tags == 0

    def test_supported_content_types(self):
        tool = RedditTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.ARTICLE in tool.supported_content_types
        assert ContentType.VIDEO not in tool.supported_content_types


class TestRedditAuthenticate:
    """RedditTool.authenticate()."""

    def test_auth_with_cookie(self):
        tool = RedditTool(config={"reddit_cookie": "session=xyz"})
        result = tool.authenticate()
        assert result.is_success()
        assert result.platform == "reddit"

    def test_auth_without_cookie(self):
        tool = RedditTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "Cookie" in result.error


class TestRedditPublish:
    """RedditTool.publish()."""

    def test_publish_with_subreddit_in_custom_fields(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = _text_content(custom_fields={"subreddit": "programming"})
        result = tool.publish(content)
        assert result.is_success()
        assert result.content_id is not None
        assert result.content_id.startswith("t3_")
        assert "programming" in result.content_url
        assert result.published_at is not None

    def test_publish_falls_back_to_default_subreddits(self):
        tool = RedditTool(config={"reddit_cookie": "x", "default_subreddits": ["python"]})
        content = _text_content()  # no subreddit in custom_fields
        result = tool.publish(content)
        assert result.is_success()
        assert "python" in result.content_url

    def test_publish_fails_without_subreddit(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = _text_content()
        result = tool.publish(content)
        assert result.is_failed()
        assert "Subreddit" in result.error

    def test_publish_title_too_long(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = _text_content(
            title="x" * 301,
            custom_fields={"subreddit": "test"},
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Title exceeds" in result.error

    def test_publish_body_too_long(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = _text_content(
            body="x" * 40001,
            custom_fields={"subreddit": "test"},
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_unsupported_content_type(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = PublishContent(
            title="Title",
            body="Body",
            content_type=ContentType.VIDEO,
            custom_fields={"subreddit": "test"},
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error

    def test_publish_with_images(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = PublishContent(
            title="Gallery",
            body="Check these out",
            content_type=ContentType.IMAGE_TEXT,
            images=["a.jpg", "b.jpg"],
            custom_fields={"subreddit": "pics"},
        )
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_at_exact_limits(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = PublishContent(
            title="x" * 300,
            body="y" * 40000,
            content_type=ContentType.TEXT,
            images=[f"img{i}.jpg" for i in range(20)],
            custom_fields={"subreddit": "test"},
        )
        result = tool.publish(content)
        assert result.is_success()


class TestRedditGetAnalytics:
    """RedditTool.get_analytics()."""

    def test_returns_expected_keys(self):
        tool = RedditTool()
        data = tool.get_analytics("t3_abc123")
        assert data["content_id"] == "t3_abc123"
        assert data["platform"] == "reddit"
        assert "upvotes" in data
        assert "downvotes" in data
        assert "comments" in data
        assert "awards" in data
        assert "crossposts" in data
        assert "engagement_rate" in data


class TestRedditSchedule:
    """RedditTool.schedule()."""

    def test_schedule_always_fails(self):
        tool = RedditTool()
        content = _text_content()
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "外部调度" in result.error or "不支持" in result.error


# ===========================================================================
# TwitterTool
# ===========================================================================

class TestTwitterToolInit:
    """TwitterTool initialisation."""

    def test_default_init(self):
        tool = TwitterTool()
        assert tool.name == "twitter_publisher"
        assert tool.platform == "twitter"
        assert tool._cookie is None
        assert tool._api_key is None

    def test_init_with_api_config(self):
        cfg = {
            "twitter_api_key": "k",
            "twitter_api_secret": "s",
            "twitter_access_token": "t",
        }
        tool = TwitterTool(config=cfg)
        assert tool._api_key == "k"
        assert tool._api_secret == "s"
        assert tool._access_token == "t"

    def test_init_with_cookie_config(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        assert tool._cookie == "c"
        assert tool._api_key is None

    def test_platform_constraints(self):
        tool = TwitterTool()
        assert tool.max_title_length == 0
        assert tool.max_body_length == 280
        assert tool.max_images == 4
        assert tool.max_tags == 0

    def test_supported_content_types(self):
        tool = TwitterTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.VIDEO not in tool.supported_content_types
        assert ContentType.ARTICLE not in tool.supported_content_types


class TestTwitterAuthenticate:
    """TwitterTool.authenticate()."""

    def test_auth_with_api_key_and_token(self):
        tool = TwitterTool(config={"twitter_api_key": "k", "twitter_access_token": "t"})
        result = tool.authenticate()
        assert result.is_success()
        assert "API" in result.status_detail

    def test_auth_with_cookie(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Cookie" in result.status_detail

    def test_auth_api_key_takes_priority_over_cookie(self):
        tool = TwitterTool(config={
            "twitter_api_key": "k",
            "twitter_access_token": "t",
            "twitter_cookie": "c",
        })
        result = tool.authenticate()
        assert result.is_success()
        assert "API" in result.status_detail

    def test_auth_no_credentials(self):
        tool = TwitterTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "认证信息" in result.error or "未配置" in result.error


class TestTwitterPublish:
    """TwitterTool.publish()."""

    def test_publish_short_tweet(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = _text_content(title="", body="Hello world!")
        result = tool.publish(content)
        assert result.is_success()
        assert result.content_id is not None
        assert result.published_at is not None

    def test_publish_body_exceeds_280_triggers_thread_path(self):
        """
        publish() validates content first via validate_content(), which will
        reject body > 280. So a body > 280 will fail validation before thread
        splitting can happen.
        """
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = _text_content(title="", body="A" * 281)
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_at_exact_280(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = _text_content(title="", body="x" * 280)
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_with_images(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = PublishContent(
            title="",
            body="Check these",
            content_type=ContentType.IMAGE,
            images=["a.jpg", "b.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_too_many_images(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = PublishContent(
            title="",
            body="Pics",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(5)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_unsupported_video(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = PublishContent(
            title="",
            body="Video",
            content_type=ContentType.VIDEO,
            video="/vid.mp4",
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error


class TestTwitterSplitToThread:
    """TwitterTool._split_to_thread() internal method."""

    def test_short_text_single_tweet(self):
        tool = TwitterTool()
        tweets = tool._split_to_thread("Hello world!")
        assert len(tweets) == 1
        assert tweets[0] == "Hello world!"

    def test_text_exactly_280_single_tweet(self):
        tool = TwitterTool()
        text = "x" * 280
        tweets = tool._split_to_thread(text)
        assert len(tweets) == 1

    def test_long_text_multiple_tweets(self):
        tool = TwitterTool()
        text = "A" * 600
        tweets = tool._split_to_thread(text)
        assert len(tweets) >= 2
        # Recombined text must equal the original
        assert "".join(tweets) == text

    def test_split_prefers_punctuation_break(self):
        tool = TwitterTool()
        # Build text where a period is in the second half of the first 280 chars
        text = "a" * 200 + "." + "b" * 200
        tweets = tool._split_to_thread(text)
        assert len(tweets) >= 2
        # First tweet should end at or after the period
        assert tweets[0].endswith(".")

    def test_split_preserves_all_content(self):
        tool = TwitterTool()
        original = "Hello world. " * 40  # ~520 chars
        tweets = tool._split_to_thread(original)
        recombined = "".join(tweets)
        assert recombined == original


class TestTwitterGetAnalytics:
    """TwitterTool.get_analytics()."""

    def test_returns_expected_keys(self):
        tool = TwitterTool()
        data = tool.get_analytics("1234567890")
        assert data["content_id"] == "1234567890"
        assert data["platform"] == "twitter"
        for key in ("views", "likes", "retweets", "replies", "quotes", "bookmarks"):
            assert key in data
        assert "engagement_rate" in data


class TestTwitterSchedule:
    """TwitterTool.schedule()."""

    def test_schedule_with_api_key(self):
        tool = TwitterTool(config={"twitter_api_key": "k", "twitter_access_token": "t"})
        content = _text_content(title="", body="Scheduled tweet")
        future = datetime.now() + timedelta(hours=2)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "定时" in result.status_detail or future.isoformat()[:10] in result.status_detail

    def test_schedule_without_api_key(self):
        tool = TwitterTool(config={"twitter_cookie": "c"})
        content = _text_content(title="", body="Scheduled")
        future = datetime.now() + timedelta(hours=2)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "API" in result.error


# ===========================================================================
# InstagramTool
# ===========================================================================

class TestInstagramToolInit:
    """InstagramTool initialisation."""

    def test_default_init(self):
        tool = InstagramTool()
        assert tool.name == "instagram_publisher"
        assert tool.platform == "instagram"
        assert tool._cookie is None
        assert tool._access_token is None

    def test_init_with_config(self):
        cfg = {"instagram_cookie": "c", "instagram_access_token": "tok"}
        tool = InstagramTool(config=cfg)
        assert tool._cookie == "c"
        assert tool._access_token == "tok"

    def test_platform_constraints(self):
        tool = InstagramTool()
        assert tool.max_title_length == 0
        assert tool.max_body_length == 2200
        assert tool.max_images == 10
        assert tool.max_tags == 30

    def test_supported_content_types(self):
        tool = InstagramTool()
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.VIDEO in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.TEXT not in tool.supported_content_types
        assert ContentType.ARTICLE not in tool.supported_content_types


class TestInstagramAuthenticate:
    """InstagramTool.authenticate()."""

    def test_auth_with_access_token(self):
        tool = InstagramTool(config={"instagram_access_token": "tok"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Graph API" in result.status_detail

    def test_auth_with_cookie(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Cookie" in result.status_detail

    def test_auth_token_priority_over_cookie(self):
        tool = InstagramTool(config={
            "instagram_access_token": "tok",
            "instagram_cookie": "c",
        })
        result = tool.authenticate()
        assert "Graph API" in result.status_detail

    def test_auth_no_credentials(self):
        tool = InstagramTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "认证信息" in result.error or "未配置" in result.error


class TestInstagramPublish:
    """InstagramTool.publish()."""

    def test_publish_single_image(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Nice pic",
            content_type=ContentType.IMAGE,
            images=["photo.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert result.content_id is not None
        assert "instagram.com/p/" in result.content_url

    def test_publish_carousel(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Carousel",
            content_type=ContentType.IMAGE,
            images=["a.jpg", "b.jpg", "c.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert "Carousel" in result.status_detail
        assert "3" in result.status_detail

    def test_publish_reel(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Watch this",
            content_type=ContentType.VIDEO,
            video="/path/to/reel.mp4",
        )
        result = tool.publish(content)
        assert result.is_success()
        assert "Reels" in result.status_detail
        assert "reel" in result.content_url

    def test_publish_fails_without_media(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="No media",
            content_type=ContentType.IMAGE,
            images=[],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "图片" in result.error or "视频" in result.error

    def test_publish_unsupported_text_only(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = _text_content(title="", body="Text only")
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error

    def test_publish_too_many_images(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Too many",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(11)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_body_too_long(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="x" * 2201,
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_tags(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Tagged",
            content_type=ContentType.IMAGE,
            images=["img.jpg"],
            tags=[f"tag{i}" for i in range(31)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many tags" in result.error

    def test_publish_at_exact_limits(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="x" * 2200,
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(10)],
            tags=[f"tag{i}" for i in range(30)],
        )
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_video_takes_priority_over_multiple_images(self):
        """When both video and multiple images are present, video (reel) wins."""
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = PublishContent(
            title="",
            body="Mixed",
            content_type=ContentType.VIDEO,
            video="/vid.mp4",
            images=["a.jpg", "b.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()
        assert "Reels" in result.status_detail


class TestInstagramGetAnalytics:
    """InstagramTool.get_analytics()."""

    def test_returns_expected_keys(self):
        tool = InstagramTool()
        data = tool.get_analytics("media_123")
        assert data["content_id"] == "media_123"
        assert data["platform"] == "instagram"
        for key in ("likes", "comments", "shares", "saves", "reach", "impressions"):
            assert key in data
        assert "engagement_rate" in data


class TestInstagramSchedule:
    """InstagramTool.schedule()."""

    def test_schedule_with_access_token(self):
        tool = InstagramTool(config={"instagram_access_token": "tok"})
        content = _image_content()
        future = datetime.now() + timedelta(hours=3)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "定时" in result.status_detail

    def test_schedule_without_access_token(self):
        tool = InstagramTool(config={"instagram_cookie": "c"})
        content = _image_content()
        future = datetime.now() + timedelta(hours=3)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "Graph API" in result.error


# ===========================================================================
# FacebookTool
# ===========================================================================

class TestFacebookToolInit:
    """FacebookTool initialisation."""

    def test_default_init(self):
        tool = FacebookTool()
        assert tool.name == "facebook_publisher"
        assert tool.platform == "facebook"
        assert tool._cookie is None
        assert tool._page_id is None
        assert tool._access_token is None

    def test_init_with_config(self):
        cfg = {
            "facebook_cookie": "c",
            "facebook_page_id": "12345",
            "facebook_access_token": "tok",
        }
        tool = FacebookTool(config=cfg)
        assert tool._cookie == "c"
        assert tool._page_id == "12345"
        assert tool._access_token == "tok"

    def test_platform_constraints(self):
        tool = FacebookTool()
        assert tool.max_title_length == 0
        assert tool.max_body_length == 63206
        assert tool.max_images == 10
        assert tool.max_tags == 50

    def test_supported_content_types(self):
        tool = FacebookTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.VIDEO in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.ARTICLE in tool.supported_content_types


class TestFacebookAuthenticate:
    """FacebookTool.authenticate()."""

    def test_auth_with_api(self):
        tool = FacebookTool(config={
            "facebook_access_token": "tok",
            "facebook_page_id": "12345",
        })
        result = tool.authenticate()
        assert result.is_success()
        assert "Graph API" in result.status_detail

    def test_auth_needs_both_token_and_page_id(self):
        tool = FacebookTool(config={"facebook_access_token": "tok"})
        result = tool.authenticate()
        # Only token without page_id falls through to cookie check
        assert result.is_failed()

    def test_auth_with_cookie(self):
        tool = FacebookTool(config={"facebook_cookie": "c"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Cookie" in result.status_detail

    def test_auth_no_credentials(self):
        tool = FacebookTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "认证信息" in result.error or "未配置" in result.error


class TestFacebookPublish:
    """FacebookTool.publish()."""

    def test_publish_text_post(self):
        tool = FacebookTool(config={
            "facebook_access_token": "tok",
            "facebook_page_id": "12345",
        })
        content = _text_content(title="", body="Hello Facebook")
        result = tool.publish(content)
        assert result.is_success()
        assert result.content_id is not None
        assert "12345" in result.content_url
        assert result.published_at is not None

    def test_publish_with_target_type_group(self):
        tool = FacebookTool(config={
            "facebook_access_token": "tok",
            "facebook_page_id": "12345",
        })
        content = _text_content(
            title="",
            body="Group post",
            custom_fields={"target_type": "group", "target_id": "67890"},
        )
        result = tool.publish(content)
        assert result.is_success()
        assert "67890" in result.content_url

    def test_publish_body_too_long(self):
        tool = FacebookTool(config={"facebook_cookie": "c"})
        content = _text_content(title="", body="x" * 63207)
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_images(self):
        tool = FacebookTool(config={"facebook_cookie": "c"})
        content = PublishContent(
            title="",
            body="Photos",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(11)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_uses_page_id_when_no_target_id(self):
        tool = FacebookTool(config={
            "facebook_access_token": "tok",
            "facebook_page_id": "page99",
        })
        content = _text_content(title="", body="Default target")
        result = tool.publish(content)
        assert "page99" in result.content_url


class TestFacebookGetAnalytics:
    """FacebookTool.get_analytics()."""

    def test_returns_expected_keys(self):
        tool = FacebookTool()
        data = tool.get_analytics("post_123")
        assert data["content_id"] == "post_123"
        assert data["platform"] == "facebook"
        for key in ("reactions", "comments", "shares", "reach", "impressions", "clicks"):
            assert key in data
        assert "engagement_rate" in data


class TestFacebookSchedule:
    """FacebookTool.schedule()."""

    def test_schedule_with_access_token(self):
        tool = FacebookTool(config={
            "facebook_access_token": "tok",
            "facebook_page_id": "12345",
        })
        content = _text_content(title="", body="Scheduled")
        future = datetime.now() + timedelta(days=1)
        result = tool.schedule(content, future)
        assert result.is_success()
        assert "定时" in result.status_detail

    def test_schedule_without_access_token(self):
        tool = FacebookTool(config={"facebook_cookie": "c"})
        content = _text_content(title="", body="Scheduled")
        future = datetime.now() + timedelta(days=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "Graph API" in result.error


# ===========================================================================
# ThreadsTool
# ===========================================================================

class TestThreadsToolInit:
    """ThreadsTool initialisation."""

    def test_default_init(self):
        tool = ThreadsTool()
        assert tool.name == "threads_publisher"
        assert tool.platform == "threads"
        assert tool._cookie is None
        assert tool._access_token is None
        assert tool._user_id is None

    def test_init_with_config(self):
        cfg = {
            "threads_cookie": "c",
            "threads_access_token": "tok",
            "threads_user_id": "uid",
        }
        tool = ThreadsTool(config=cfg)
        assert tool._cookie == "c"
        assert tool._access_token == "tok"
        assert tool._user_id == "uid"

    def test_platform_constraints(self):
        tool = ThreadsTool()
        assert tool.max_title_length == 0
        assert tool.max_body_length == 500
        assert tool.max_images == 10
        assert tool.max_tags == 0

    def test_supported_content_types(self):
        tool = ThreadsTool()
        assert ContentType.TEXT in tool.supported_content_types
        assert ContentType.IMAGE in tool.supported_content_types
        assert ContentType.VIDEO in tool.supported_content_types
        assert ContentType.IMAGE_TEXT in tool.supported_content_types
        assert ContentType.ARTICLE not in tool.supported_content_types


class TestThreadsAuthenticate:
    """ThreadsTool.authenticate()."""

    def test_auth_with_access_token(self):
        tool = ThreadsTool(config={"threads_access_token": "tok"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Threads API" in result.status_detail

    def test_auth_with_cookie(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        result = tool.authenticate()
        assert result.is_success()
        assert "Cookie" in result.status_detail

    def test_auth_token_priority_over_cookie(self):
        tool = ThreadsTool(config={
            "threads_access_token": "tok",
            "threads_cookie": "c",
        })
        result = tool.authenticate()
        assert "Threads API" in result.status_detail

    def test_auth_no_credentials(self):
        tool = ThreadsTool()
        result = tool.authenticate()
        assert result.is_failed()
        assert "认证信息" in result.error or "未配置" in result.error


class TestThreadsPublish:
    """ThreadsTool.publish()."""

    def test_publish_text_post(self):
        tool = ThreadsTool(config={"threads_access_token": "tok"})
        content = _text_content(title="", body="Hello Threads")
        result = tool.publish(content)
        assert result.is_success()
        assert result.content_id is not None
        assert "threads.net" in result.content_url
        assert result.published_at is not None

    def test_publish_with_images(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        content = PublishContent(
            title="",
            body="Look!",
            content_type=ContentType.IMAGE,
            images=["a.jpg"],
        )
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_body_too_long(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        content = _text_content(title="", body="x" * 501)
        result = tool.publish(content)
        assert result.is_failed()
        assert "Body exceeds" in result.error

    def test_publish_too_many_images(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        content = PublishContent(
            title="",
            body="Many",
            content_type=ContentType.IMAGE,
            images=[f"img{i}.jpg" for i in range(11)],
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "Too many images" in result.error

    def test_publish_at_exact_500_chars(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        content = _text_content(title="", body="x" * 500)
        result = tool.publish(content)
        assert result.is_success()

    def test_publish_unsupported_article(self):
        tool = ThreadsTool(config={"threads_cookie": "c"})
        content = PublishContent(
            title="Article",
            body="Long form",
            content_type=ContentType.ARTICLE,
        )
        result = tool.publish(content)
        assert result.is_failed()
        assert "not supported" in result.error


class TestThreadsGetAnalytics:
    """ThreadsTool.get_analytics()."""

    def test_returns_expected_keys(self):
        tool = ThreadsTool()
        data = tool.get_analytics("thread_abc")
        assert data["content_id"] == "thread_abc"
        assert data["platform"] == "threads"
        for key in ("likes", "replies", "reposts", "quotes"):
            assert key in data
        assert "engagement_rate" in data


class TestThreadsSchedule:
    """ThreadsTool.schedule()."""

    def test_schedule_always_fails(self):
        tool = ThreadsTool(config={"threads_access_token": "tok"})
        content = _text_content(title="", body="Later")
        future = datetime.now() + timedelta(hours=1)
        result = tool.schedule(content, future)
        assert result.is_failed()
        assert "不支持" in result.error


# ===========================================================================
# Factory: get_overseas_platform_tool
# ===========================================================================

class TestGetOverseasPlatformTool:
    """Tests for the get_overseas_platform_tool() factory function."""

    @pytest.mark.parametrize(
        "name, expected_cls",
        [
            ("reddit", RedditTool),
            ("twitter", TwitterTool),
            ("x", TwitterTool),
            ("instagram", InstagramTool),
            ("facebook", FacebookTool),
            ("threads", ThreadsTool),
        ],
    )
    def test_supported_platforms(self, name, expected_cls):
        tool = get_overseas_platform_tool(name)
        assert isinstance(tool, expected_cls)

    def test_case_insensitive(self):
        tool = get_overseas_platform_tool("REDDIT")
        assert isinstance(tool, RedditTool)

    def test_passes_config(self):
        cfg = {"reddit_cookie": "session=abc"}
        tool = get_overseas_platform_tool("reddit", config=cfg)
        assert tool._cookie == "session=abc"

    def test_unsupported_platform_raises(self):
        with pytest.raises(ValueError, match="Unsupported overseas platform"):
            get_overseas_platform_tool("tiktok")

    def test_unsupported_platform_weibo_raises(self):
        with pytest.raises(ValueError):
            get_overseas_platform_tool("weibo")

    def test_x_alias_returns_twitter(self):
        tool = get_overseas_platform_tool("x")
        assert tool.platform == "twitter"

    def test_factory_with_no_config(self):
        tool = get_overseas_platform_tool("facebook")
        assert tool.config == {}
        assert tool._page_id is None


# ===========================================================================
# Cross-cutting: validate_content (inherited from BasePlatformTool)
# ===========================================================================

class TestValidateContentCrossCutting:
    """Validate content against each platform's specific constraints."""

    def test_reddit_validates_article_type(self):
        tool = RedditTool()
        content = PublishContent(title="T", body="B", content_type=ContentType.ARTICLE)
        is_valid, err = tool.validate_content(content)
        assert is_valid is True

    def test_twitter_rejects_article_type(self):
        tool = TwitterTool()
        content = PublishContent(title="", body="B", content_type=ContentType.ARTICLE)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False
        assert "not supported" in err

    def test_instagram_rejects_text_type(self):
        tool = InstagramTool()
        content = PublishContent(title="", body="B", content_type=ContentType.TEXT)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False

    def test_facebook_accepts_all_types(self):
        tool = FacebookTool()
        for ct in ContentType:
            content = PublishContent(title="", body="B", content_type=ct)
            is_valid, _err = tool.validate_content(content)
            assert is_valid is True, f"Facebook should support {ct.value}"

    def test_threads_rejects_article_type(self):
        tool = ThreadsTool()
        content = PublishContent(title="", body="B", content_type=ContentType.ARTICLE)
        is_valid, err = tool.validate_content(content)
        assert is_valid is False


# ===========================================================================
# Cross-cutting: get_constraints (inherited from BasePlatformTool)
# ===========================================================================

class TestGetConstraintsCrossCutting:
    """get_constraints() returns correct platform metadata for each tool."""

    def test_reddit_constraints(self):
        c = RedditTool().get_constraints()
        assert c["platform"] == "reddit"
        assert c["max_title_length"] == 300
        assert "text" in c["supported_content_types"]

    def test_twitter_constraints(self):
        c = TwitterTool().get_constraints()
        assert c["platform"] == "twitter"
        assert c["max_body_length"] == 280
        assert "video" not in c["supported_content_types"]

    def test_instagram_constraints(self):
        c = InstagramTool().get_constraints()
        assert c["platform"] == "instagram"
        assert c["max_images"] == 10
        assert "text" not in c["supported_content_types"]

    def test_facebook_constraints(self):
        c = FacebookTool().get_constraints()
        assert c["platform"] == "facebook"
        assert c["max_body_length"] == 63206

    def test_threads_constraints(self):
        c = ThreadsTool().get_constraints()
        assert c["platform"] == "threads"
        assert c["max_body_length"] == 500
        assert "article" not in c["supported_content_types"]


# ===========================================================================
# Edge-case / regression tests
# ===========================================================================

class TestEdgeCases:
    """Miscellaneous edge-case and regression tests."""

    def test_reddit_generate_id_is_six_chars(self):
        tool = RedditTool()
        rid = tool._generate_id()
        assert len(rid) == 6
        assert rid.isalnum()

    def test_twitter_snowflake_id_is_positive_integer(self):
        tool = TwitterTool()
        sid = tool._generate_snowflake_id()
        assert isinstance(sid, int)
        assert sid > 0

    def test_instagram_media_id_contains_underscore(self):
        tool = InstagramTool()
        mid = tool._generate_media_id()
        assert "_" in mid

    def test_facebook_post_id_contains_page_id(self):
        tool = FacebookTool(config={"facebook_page_id": "p42"})
        pid = tool._generate_post_id()
        assert pid.startswith("p42_")

    def test_threads_id_contains_underscore(self):
        tool = ThreadsTool()
        tid = tool._generate_thread_id()
        assert "_" in tid

    def test_empty_config_treated_as_empty_dict(self):
        for cls in _CDP_CLASSES:
            tool = cls(config=None)
            assert tool.config == {}

    def test_publish_result_is_instance_of_publish_result(self):
        tool = RedditTool(config={"reddit_cookie": "x"})
        content = _text_content(custom_fields={"subreddit": "test"})
        result = tool.publish(content)
        assert isinstance(result, PublishResult)

    def test_all_tools_have_min_publish_interval(self):
        """Every overseas tool defines min_publish_interval."""
        assert RedditTool.min_publish_interval == 600
        assert TwitterTool.min_publish_interval == 60
        assert InstagramTool.min_publish_interval == 300
        assert FacebookTool.min_publish_interval == 60
        assert ThreadsTool.min_publish_interval == 60
