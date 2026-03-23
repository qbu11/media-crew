"""
海外平台发布工具 (使用成熟的开源 SDK)

支持的库：
- PRAW (Reddit): https://github.com/praw-dev/praw
- Tweepy (Twitter/X): https://github.com/tweepy/tweepy
- instagrapi (Instagram): https://github.com/adw0rd/instagrapi
- facebook-sdk (Facebook): https://github.com/mobolic/facebook-sdk
- threadspipe (Threads): https://pypi.org/project/threadspipepy
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .base import BasePlatformTool, ContentType, PublishContent, PublishResult


@dataclass
class PlatformSDK:
    """平台 SDK 配置"""
    name: str
    package: str
    install_cmd: str
    docs_url: str
    github_stars: int


# SDK 信息
SDK_INFO = {
    "reddit": PlatformSDK(
        name="PRAW",
        package="praw",
        install_cmd="pip install praw",
        docs_url="https://praw.readthedocs.io/",
        github_stars=4800
    ),
    "twitter": PlatformSDK(
        name="Tweepy",
        package="tweepy",
        install_cmd="pip install tweepy",
        docs_url="https://docs.tweepy.org/",
        github_stars=10500
    ),
    "instagram": PlatformSDK(
        name="instagrapi",
        package="instagrapi",
        install_cmd="pip install instagrapi",
        docs_url="https://adw0rd.github.io/instagrapi/",
        github_stars=2800
    ),
    "facebook": PlatformSDK(
        name="facebook-sdk",
        package="facebook-sdk",
        install_cmd="pip install facebook-sdk",
        docs_url="https://facebook-sdk.readthedocs.io/",
        github_stars=2200
    ),
    "threads": PlatformSDK(
        name="threadspipepy",
        package="threadspipepy",
        install_cmd="pip install threadspipepy",
        docs_url="https://pypi.org/project/threadspipepy/",
        github_stars=200
    ),
}


class RedditSDKTool(BasePlatformTool):
    """
    Reddit 发布工具 (使用 PRAW)

    安装: pip install praw
    文档: https://praw.readthedocs.io/

    认证方式:
    1. 在 https://www.reddit.com/prefs/apps 创建应用
    2. 获取 client_id 和 client_secret
    3. 配置用户名和密码
    """

    name = "reddit_sdk"
    description = "Publish to Reddit using PRAW SDK"
    platform = "reddit"
    version = "1.0.0"

    max_title_length: int = 300
    max_body_length: int = 40000
    max_images: int = 20
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.IMAGE_TEXT,
        ContentType.ARTICLE,
    ]
    min_publish_interval: int = 600  # 10 分钟

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._client_id = self.config.get("reddit_client_id")
        self._client_secret = self.config.get("reddit_client_secret")
        self._username = self.config.get("reddit_username")
        self._password = self.config.get("reddit_password")
        self._user_agent = self.config.get("reddit_user_agent", "crew-media-ops/1.0")
        self._reddit = None

    def _get_client(self):
        """获取 Reddit 客户端"""
        if self._reddit is None:
            try:
                import praw
                self._reddit = praw.Reddit(
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    user_agent=self._user_agent,
                    username=self._username,
                    password=self._password
                )
            except ImportError:
                raise ImportError(
                    f"PRAW 未安装。请运行: {SDK_INFO['reddit'].install_cmd}"
                )
        return self._reddit

    def authenticate(self) -> PublishResult:
        """认证 Reddit 账户"""
        try:
            reddit = self._get_client()
            # 验证认证
            reddit.user.me()
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail=f"已认证为 {self._username}"
            )
        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"认证失败: {e!s}",
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布内容到 Reddit

        支持发布到指定 Subreddit
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        subreddit_name = content.custom_fields.get("subreddit")
        if not subreddit_name:
            return PublishResult(
                status=self._create_failed_status(),
                error="必须指定 Subreddit",
                platform=self.platform
            )

        try:
            reddit = self._get_client()
            subreddit = reddit.subreddit(subreddit_name)

            # 发布帖子
            if content.images:
                # 图片帖子 - 使用提交链接方式
                submission = subreddit.submit_image(
                    title=content.title,
                    image_path=content.images[0]
                )
            else:
                # 文本帖子
                submission = subreddit.submit(
                    title=content.title,
                    selftext=content.body
                )

            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                content_id=submission.id,
                content_url=f"https://reddit.com{submission.permalink}",
                published_at=datetime.now(),
                status_detail=f"已发布到 r/{subreddit_name}"
            )

        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"发布失败: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Reddit 帖子数据"""
        try:
            reddit = self._get_client()
            submission = reddit.submission(id=content_id)

            return {
                "content_id": content_id,
                "platform": self.platform,
                "upvotes": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "comments": submission.num_comments,
                "awards": submission.total_awards_received,
                "engagement_rate": submission.score / max(submission.view_count or 1, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Reddit 不支持定时发布"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Reddit 不支持原生定时发布",
            platform=self.platform
        )


class TwitterSDKTool(BasePlatformTool):
    """
    Twitter/X 发布工具 (使用 Tweepy)

    安装: pip install tweepy
    文档: https://docs.tweepy.org/

    认证方式:
    1. 在 https://developer.twitter.com/ 创建应用
    2. 获取 API Key, API Secret, Access Token, Access Token Secret
    """

    name = "twitter_sdk"
    description = "Publish to Twitter/X using Tweepy SDK"
    platform = "twitter"
    version = "1.0.0"

    max_body_length: int = 280
    max_images: int = 4
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.IMAGE_TEXT,
    ]
    min_publish_interval: int = 60

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key = self.config.get("twitter_api_key")
        self._api_secret = self.config.get("twitter_api_secret")
        self._access_token = self.config.get("twitter_access_token")
        self._access_token_secret = self.config.get("twitter_access_token_secret")
        self._bearer_token = self.config.get("twitter_bearer_token")
        self._client = None

    def _get_client(self):
        """获取 Twitter 客户端"""
        if self._client is None:
            try:
                import tweepy
                self._client = tweepy.Client(
                    consumer_key=self._api_key,
                    consumer_secret=self._api_secret,
                    access_token=self._access_token,
                    access_token_secret=self._access_token_secret,
                    bearer_token=self._bearer_token
                )
            except ImportError:
                raise ImportError(
                    f"Tweepy 未安装。请运行: {SDK_INFO['twitter'].install_cmd}"
                )
        return self._client

    def authenticate(self) -> PublishResult:
        """认证 Twitter 账户"""
        try:
            client = self._get_client()
            me = client.get_me()
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail=f"已认证为 @{me.data.username}"
            )
        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"认证失败: {e!s}",
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布推文

        支持:
        - 普通推文 (280字符)
        - Thread (超长自动拆分)
        - 带图片推文
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        try:
            client = self._get_client()

            # 超长推文拆分为 Thread
            if len(content.body) > self.max_body_length:
                return self._publish_thread(client, content)

            # 发布单条推文
            if content.images:
                # 需要先上传媒体
                import tweepy
                auth = tweepy.OAuth1UserHandler(
                    self._api_key, self._api_secret,
                    self._access_token, self._access_token_secret
                )
                api = tweepy.API(auth)

                # 上传图片
                media_ids = []
                for img_path in content.images[:self.max_images]:
                    media = api.media_upload(img_path)
                    media_ids.append(media.media_id)

                response = client.create_tweet(
                    text=content.body,
                    media_ids=media_ids
                )
            else:
                response = client.create_tweet(text=content.body)

            tweet_id = response.data['id']
            username = client.get_me().data.username

            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                content_id=str(tweet_id),
                content_url=f"https://twitter.com/{username}/status/{tweet_id}",
                published_at=datetime.now(),
                status_detail="已发布"
            )

        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"发布失败: {e!s}",
                platform=self.platform
            )

    def _publish_thread(self, client, content: PublishContent) -> PublishResult:
        """发布 Thread"""
        tweets = self._split_to_thread(content.body, self.max_body_length)
        previous_tweet_id = None
        tweet_ids = []

        for tweet_text in tweets:
            if previous_tweet_id:
                response = client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=previous_tweet_id
                )
            else:
                response = client.create_tweet(text=tweet_text)

            previous_tweet_id = response.data['id']
            tweet_ids.append(previous_tweet_id)

        username = client.get_me().data.username
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=str(tweet_ids[0]),
            content_url=f"https://twitter.com/{username}/status/{tweet_ids[0]}",
            published_at=datetime.now(),
            status_detail=f"已发布 Thread ({len(tweets)} 条)"
        )

    def _split_to_thread(self, text: str, max_len: int) -> list[str]:
        """将长文本拆分为 Thread"""
        tweets = []
        remaining = text

        while remaining:
            if len(remaining) <= max_len:
                tweets.append(remaining)
                break

            # 找到合适的断点
            chunk = remaining[:max_len]
            for sep in ['。', '！', '？', '.', '!', '?', '\n', ' ']:
                last_sep = chunk.rfind(sep)
                if last_sep > max_len // 2:
                    chunk = remaining[:last_sep + 1]
                    break

            tweets.append(chunk.strip())
            remaining = remaining[len(chunk):].strip()

        return tweets

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取推文数据"""
        try:
            client = self._get_client()
            tweet = client.get_tweet(
                content_id,
                tweet_fields=['public_metrics', 'non_public_metrics']
            )

            metrics = tweet.data.public_metrics
            return {
                "content_id": content_id,
                "platform": self.platform,
                "likes": metrics.get('like_count', 0),
                "retweets": metrics.get('retweet_count', 0),
                "replies": metrics.get('reply_count', 0),
                "quotes": metrics.get('quote_count', 0),
                "views": tweet.data.non_public_metrics.get('impression_count', 0) if tweet.data.non_public_metrics else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Twitter API 不直接支持定时发布"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Twitter API 不直接支持定时发布，请使用外部调度器",
            platform=self.platform
        )


class InstagramSDKTool(BasePlatformTool):
    """
    Instagram 发布工具 (使用 instagrapi)

    安装: pip install instagrapi
    文档: https://adw0rd.github.io/instagrapi/

    注意: instagrapi 是非官方 API，有账号风险
    生产环境建议使用官方 Graph API
    """

    name = "instagram_sdk"
    description = "Publish to Instagram using instagrapi"
    platform = "instagram"
    version = "1.0.0"

    max_body_length: int = 2200
    max_images: int = 10
    supported_content_types: list[ContentType] = [
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
    ]
    min_publish_interval: int = 300  # 5 分钟

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._username = self.config.get("instagram_username")
        self._password = self.config.get("instagram_password")
        self._session_file = self.config.get("instagram_session_file", "instagram_session.json")
        self._cl = None

    def _get_client(self):
        """获取 Instagram 客户端"""
        if self._cl is None:
            try:
                from instagrapi import Client
                self._cl = Client()
                # 加载会话
                import os
                if os.path.exists(self._session_file):
                    self._cl.load_settings(self._session_file)
            except ImportError:
                raise ImportError(
                    f"instagrapi 未安装。请运行: {SDK_INFO['instagram'].install_cmd}"
                )
        return self._cl

    def authenticate(self) -> PublishResult:
        """认证 Instagram 账户"""
        try:
            cl = self._get_client()
            cl.login(self._username, self._password)
            cl.dump_settings(self._session_file)
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail=f"已认证为 {self._username}"
            )
        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"认证失败: {e!s}",
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """发布 Instagram 内容"""
        if not content.images and not content.video:
            return PublishResult(
                status=self._create_failed_status(),
                error="Instagram 必须包含图片或视频",
                platform=self.platform
            )

        try:
            cl = self._get_client()

            if content.video:
                # 发布 Reels
                media = cl.video_upload(
                    content.video,
                    caption=content.body
                )
                url = f"https://instagram.com/reel/{media.pk}"
            elif len(content.images) > 1:
                # 发布 Carousel
                media = cl.album_upload(
                    content.images,
                    caption=content.body
                )
                url = f"https://instagram.com/p/{media.pk}"
            else:
                # 发布单图
                media = cl.photo_upload(
                    content.images[0],
                    caption=content.body
                )
                url = f"https://instagram.com/p/{media.pk}"

            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                content_id=str(media.pk),
                content_url=url,
                published_at=datetime.now(),
                status_detail="已发布"
            )

        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"发布失败: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Instagram 帖子数据"""
        try:
            cl = self._get_client()
            media_id = int(content_id)
            info = cl.media_info(media_id)

            return {
                "content_id": content_id,
                "platform": self.platform,
                "likes": info.like_count,
                "comments": info.comment_count,
                "plays": getattr(info, 'play_count', 0),
                "engagement_rate": info.like_count / max(info.play_count or 1, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Instagram 不支持定时发布"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Instagram 不支持原生定时发布",
            platform=self.platform
        )


class FacebookSDKTool(BasePlatformTool):
    """
    Facebook 发布工具 (使用 facebook-sdk)

    安装: pip install facebook-sdk
    文档: https://facebook-sdk.readthedocs.io/

    认证方式:
    1. 创建 Facebook App
    2. 获取 Page Access Token
    """

    name = "facebook_sdk"
    description = "Publish to Facebook using facebook-sdk"
    platform = "facebook"
    version = "1.0.0"

    max_body_length: int = 63206
    max_images: int = 10
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
    ]
    min_publish_interval: int = 60

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._access_token = self.config.get("facebook_access_token")
        self._page_id = self.config.get("facebook_page_id")
        self._graph = None

    def _get_client(self):
        """获取 Facebook 客户端"""
        if self._graph is None:
            try:
                import facebook
                self._graph = facebook.GraphAPI(access_token=self._access_token, version="3.1")
            except ImportError:
                raise ImportError(
                    f"facebook-sdk 未安装。请运行: {SDK_INFO['facebook'].install_cmd}"
                )
        return self._graph

    def authenticate(self) -> PublishResult:
        """认证 Facebook 账户"""
        try:
            graph = self._get_client()
            me = graph.get_object("me")
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail=f"已认证为 {me.get('name')}"
            )
        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"认证失败: {e!s}",
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """发布 Facebook 内容"""
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        try:
            graph = self._get_client()
            target_id = content.custom_fields.get("target_id", self._page_id)

            if content.images:
                # 带图片发布
                with open(content.images[0], 'rb') as photo:
                    response = graph.put_photo(
                        image=photo,
                        message=content.body,
                        album_path=f"{target_id}/photos"
                    )
            else:
                # 纯文本发布
                response = graph.put_object(
                    parent_object=target_id,
                    connection_name="feed",
                    message=content.body
                )

            post_id = response.get('id') or response.get('post_id')

            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                content_id=post_id,
                content_url=f"https://facebook.com/{post_id}",
                published_at=datetime.now(),
                status_detail="已发布"
            )

        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"发布失败: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Facebook 帖子数据"""
        try:
            graph = self._get_client()
            post = graph.get_object(
                content_id,
                fields='reactions.summary(true),comments.summary(true),shares'
            )

            return {
                "content_id": content_id,
                "platform": self.platform,
                "reactions": post.get('reactions', {}).get('summary', {}).get('total_count', 0),
                "comments": post.get('comments', {}).get('summary', {}).get('total_count', 0),
                "shares": post.get('shares', {}).get('count', 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Facebook 支持定时发布"""
        # 需要使用 Graph API 的 scheduled_publish_time 参数
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            status_detail=f"已定时 {publish_time.isoformat()} (需要 Graph API)"
        )


class ThreadsSDKTool(BasePlatformTool):
    """
    Threads 发布工具

    安装: pip install threadspipepy
    文档: https://pypi.org/project/threadspipepy/

    Threads API 是较新的 API，使用 Instagram OAuth
    """

    name = "threads_sdk"
    description = "Publish to Threads using Threads API"
    platform = "threads"
    version = "1.0.0"

    max_body_length: int = 500
    max_images: int = 10
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
    ]
    min_publish_interval: int = 60

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._access_token = self.config.get("threads_access_token")
        self._user_id = self.config.get("threads_user_id")

    def authenticate(self) -> PublishResult:
        """认证 Threads 账户"""
        if self._access_token:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Access Token 认证"
            )
        return PublishResult(
            status=self._create_failed_status(),
            error="Threads Access Token 未配置",
            platform=self.platform
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布 Threads 内容

        Threads API 使用两步发布:
        1. 创建 Media Container
        2. 发布 Container
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        try:
            import httpx

            base_url = "https://graph.threads.net/v1.0"

            # Step 1: 创建 Container
            container_data = {
                "media_type": "TEXT" if not content.images else "IMAGE",
                "text": content.body,
                "access_token": self._access_token
            }

            if content.images:
                container_data["image_url"] = content.images[0]

            container_response = httpx.post(
                f"{base_url}/{self._user_id}/threads",
                data=container_data
            )
            container_id = container_response.json().get("id")

            # Step 2: 发布
            publish_response = httpx.post(
                f"{base_url}/{self._user_id}/threads_publish",
                data={
                    "creation_id": container_id,
                    "access_token": self._access_token
                }
            )
            result = publish_response.json()

            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                content_id=result.get("id"),
                content_url=f"https://threads.net/@{self._user_id}/post/{result.get('id')}",
                published_at=datetime.now(),
                status_detail="已发布"
            )

        except Exception as e:
            return PublishResult(
                status=self._create_failed_status(),
                error=f"发布失败: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Threads 数据"""
        # Threads API 较新，分析功能有限
        return {
            "content_id": content_id,
            "platform": self.platform,
            "likes": 0,
            "replies": 0,
            "reposts": 0,
            "quotes": 0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Threads 不支持定时发布"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Threads 不支持原生定时发布",
            platform=self.platform
        )


# 工厂函数
def get_overseas_sdk_tool(platform: str, config: dict[str, Any] | None = None):
    """获取海外平台 SDK 工具实例"""
    tools = {
        "reddit": RedditSDKTool,
        "twitter": TwitterSDKTool,
        "x": TwitterSDKTool,
        "instagram": InstagramSDKTool,
        "facebook": FacebookSDKTool,
        "threads": ThreadsSDKTool,
    }

    tool_class = tools.get(platform.lower())
    if tool_class:
        return tool_class(config)

    raise ValueError(f"Unsupported platform: {platform}")


# 依赖安装帮助
def install_sdk_dependencies(platforms: list[str] | None = None):
    """打印 SDK 依赖安装命令"""
    if platforms is None:
        platforms = list(SDK_INFO.keys())

    print("# 安装海外平台 SDK 依赖")
    print()
    for platform in platforms:
        if platform in SDK_INFO:
            info = SDK_INFO[platform]
            print(f"# {info.name} ({platform}) - {info.github_stars} stars")
            print(f"# Docs: {info.docs_url}")
            print(f"{info.install_cmd}")
            print()


if __name__ == "__main__":
    # 打印所有 SDK 安装命令
    install_sdk_dependencies()
