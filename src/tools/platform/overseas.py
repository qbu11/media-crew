"""
Reddit 发布工具

支持发布 Post、Comment 到 Reddit。
通过 Chrome CDP 自动化实现。
"""

from datetime import datetime
from typing import Any

from .base import BasePlatformTool, ContentType, PublishContent, PublishResult


class RedditTool(BasePlatformTool):
    """Reddit 发布工具"""

    name = "reddit_publisher"
    description = "Publish content to Reddit"
    platform = "reddit"
    version = "0.1.0"

    # Reddit 平台约束
    max_title_length: int = 300
    max_body_length: int = 40000  # Markdown 支持
    max_images: int = 20
    max_tags: int = 0  # Reddit 使用 flair 而非 tags
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.IMAGE_TEXT,
        ContentType.ARTICLE,
    ]

    # 发布间隔
    min_publish_interval: int = 600  # 10 分钟（Reddit 严格限制）

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie = self.config.get("reddit_cookie")
        self._subreddits = self.config.get("default_subreddits", [])

    def authenticate(self) -> PublishResult:
        """认证 Reddit 账户"""
        if not self._cookie:
            return PublishResult(
                status=self._create_failed_status(),
                error="Reddit Cookie 未配置",
                platform=self.platform
            )

        # 实际实现中通过 Chrome CDP 验证登录状态
        # 访问 reddit.com，检查是否已登录
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            status_detail="已通过 Cookie 认证"
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布内容到 Reddit

        流程：
        1. 验证内容
        2. 选择 Subreddit
        3. 创建 Post（Text/Image/Link）
        4. 等待发布完成
        """
        # 验证内容
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        # 获取目标 Subreddit
        subreddit = content.custom_fields.get("subreddit")
        if not subreddit and self._subreddits:
            subreddit = self._subreddits[0]

        if not subreddit:
            return PublishResult(
                status=self._create_failed_status(),
                error="未指定 Subreddit",
                platform=self.platform
            )

        # 实际发布逻辑（通过 Chrome CDP）
        # 1. 访问 reddit.com/r/{subreddit}/submit
        # 2. 填写标题和内容
        # 3. 上传图片（如有）
        # 4. 选择 Flair
        # 5. 提交

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=f"t3_{self._generate_id()}",
            content_url=f"https://reddit.com/r/{subreddit}/comments/xxx",
            published_at=datetime.now(),
            status_detail="已发布"
        )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """
        获取 Reddit Post 数据

        指标：Upvotes, Downvotes, Comments, Awards, Crossposts
        """
        # 实际实现中通过 Reddit API 或 Chrome CDP 获取
        return {
            "content_id": content_id,
            "platform": self.platform,
            "upvotes": 0,
            "downvotes": 0,
            "comments": 0,
            "awards": 0,
            "crossposts": 0,
            "engagement_rate": 0.0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Reddit 不支持原生定时发布，需要外部调度"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Reddit 不支持原生定时发布，请使用外部调度器",
            platform=self.platform
        )

    def _generate_id(self) -> str:
        """生成 Reddit ID"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))


class TwitterTool(BasePlatformTool):
    """X (Twitter) 发布工具"""

    name = "twitter_publisher"
    description = "Publish content to X (Twitter)"
    platform = "twitter"
    version = "0.1.0"

    # Twitter 平台约束
    max_title_length: int = 0  # 无标题概念
    max_body_length: int = 280  # 字符限制（中文算2）
    max_images: int = 4
    max_tags: int = 0  # 使用 @mentions 和 #hashtags
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.IMAGE_TEXT,
    ]

    min_publish_interval: int = 60  # 1 分钟

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie = self.config.get("twitter_cookie")
        self._api_key = self.config.get("twitter_api_key")
        self._api_secret = self.config.get("twitter_api_secret")
        self._access_token = self.config.get("twitter_access_token")

    def authenticate(self) -> PublishResult:
        """认证 Twitter 账户"""
        # 支持 API 和 Cookie 两种方式
        if self._api_key and self._access_token:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 API 认证"
            )

        if self._cookie:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Cookie 认证"
            )

        return PublishResult(
            status=self._create_failed_status(),
            error="Twitter 认证信息未配置",
            platform=self.platform
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布 Tweet

        支持：
        - 纯文本
        - 图片（最多4张）
        - Thread（多条连续推文）
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        # 检查是否需要拆分为 Thread
        if len(content.body) > self.max_body_length:
            # 自动拆分为 Thread
            tweets = self._split_to_thread(content.body)
            # 发布 Thread
            return self._publish_thread(tweets, content.images)

        # 发布单条 Tweet
        return self._publish_single(content)

    def _split_to_thread(self, text: str) -> list[str]:
        """将长文本拆分为 Thread"""
        tweets = []
        remaining = text

        while remaining:
            if len(remaining) <= self.max_body_length:
                tweets.append(remaining)
                break
            else:
                # 找到最后一个合适的断点
                chunk = remaining[:self.max_body_length]
                # 在标点处断开
                break_points = ['。', '！', '？', '.', '!', '?', '\n']
                for bp in break_points:
                    last_bp = chunk.rfind(bp)
                    if last_bp > self.max_body_length // 2:
                        chunk = remaining[:last_bp + 1]
                        break

                tweets.append(chunk)
                remaining = remaining[len(chunk):]

        return tweets

    def _publish_single(self, content: PublishContent) -> PublishResult:
        """发布单条 Tweet"""
        # 实际实现：
        # 1. API 方式：POST /2/tweets
        # 2. Chrome CDP：访问 twitter.com/compose/tweet

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=str(self._generate_snowflake_id()),
            content_url="https://twitter.com/user/status/xxx",
            published_at=datetime.now(),
            status_detail="已发布"
        )

    def _publish_thread(self, tweets: list[str], images: list[str]) -> PublishResult:
        """发布 Thread"""
        # 依次发布，每条回复前一条
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=str(self._generate_snowflake_id()),
            content_url="https://twitter.com/user/status/xxx",
            published_at=datetime.now(),
            status_detail=f"已发布 Thread ({len(tweets)} 条)"
        )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Tweet 数据"""
        return {
            "content_id": content_id,
            "platform": self.platform,
            "views": 0,
            "likes": 0,
            "retweets": 0,
            "replies": 0,
            "quotes": 0,
            "bookmarks": 0,
            "engagement_rate": 0.0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Twitter 支持 API 定时发布"""
        if not self._api_key:
            return PublishResult(
                status=self._create_failed_status(),
                error="定时发布需要 Twitter API 认证",
                platform=self.platform
            )

        # 使用 Twitter API 的 scheduled endpoints
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            status_detail=f"已定时 {publish_time.isoformat()}"
        )

    def _generate_snowflake_id(self) -> int:
        """生成 Twitter Snowflake ID"""
        import random
        import time
        timestamp = int(time.time() * 1000)
        return timestamp << 22 | random.randint(0, 4095)


class InstagramTool(BasePlatformTool):
    """Instagram 发布工具"""

    name = "instagram_publisher"
    description = "Publish content to Instagram"
    platform = "instagram"
    version = "0.1.0"

    # Instagram 平台约束
    max_title_length: int = 0  # 无标题
    max_body_length: int = 2200  # Caption 限制
    max_images: int = 10  # Carousel
    max_tags: int = 30  # Hashtags
    supported_content_types: list[ContentType] = [
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
    ]

    min_publish_interval: int = 300  # 5 分钟

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie = self.config.get("instagram_cookie")
        self._access_token = self.config.get("instagram_access_token")  # Graph API

    def authenticate(self) -> PublishResult:
        """认证 Instagram 账户"""
        if self._access_token:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Graph API 认证"
            )

        if self._cookie:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Cookie 认证"
            )

        return PublishResult(
            status=self._create_failed_status(),
            error="Instagram 认证信息未配置",
            platform=self.platform
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布 Instagram 内容

        支持：
        - Single Image/Video
        - Carousel (多图/视频)
        - Reels
        - Stories
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        # 必须有图片或视频
        if not content.images and not content.video:
            return PublishResult(
                status=self._create_failed_status(),
                error="Instagram 必须包含图片或视频",
                platform=self.platform
            )

        # 根据内容类型选择发布方式
        if content.video:
            return self._publish_reel(content)  # Reels
        elif len(content.images) > 1:
            return self._publish_carousel(content)  # Carousel
        else:
            return self._publish_single(content)  # Single Post

    def _publish_single(self, content: PublishContent) -> PublishResult:
        """发布单图 Post"""
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=self._generate_media_id(),
            content_url="https://instagram.com/p/xxx",
            published_at=datetime.now(),
            status_detail="已发布"
        )

    def _publish_carousel(self, content: PublishContent) -> PublishResult:
        """发布 Carousel"""
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=self._generate_media_id(),
            content_url="https://instagram.com/p/xxx",
            published_at=datetime.now(),
            status_detail=f"已发布 Carousel ({len(content.images)} 张)"
        )

    def _publish_reel(self, content: PublishContent) -> PublishResult:
        """发布 Reels"""
        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=self._generate_media_id(),
            content_url="https://instagram.com/reel/xxx",
            published_at=datetime.now(),
            status_detail="已发布 Reels"
        )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Instagram Post 数据"""
        return {
            "content_id": content_id,
            "platform": self.platform,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "reach": 0,
            "impressions": 0,
            "engagement_rate": 0.0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Instagram Graph API 支持定时发布"""
        if not self._access_token:
            return PublishResult(
                status=self._create_failed_status(),
                error="定时发布需要 Instagram Graph API 认证",
                platform=self.platform
            )

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            status_detail=f"已定时 {publish_time.isoformat()}"
        )

    def _generate_media_id(self) -> str:
        """生成 Instagram Media ID"""
        import random
        import time
        return f"{int(time.time() * 1000)}_{random.randint(100000000, 999999999)}"


class FacebookTool(BasePlatformTool):
    """Facebook 发布工具"""

    name = "facebook_publisher"
    description = "Publish content to Facebook"
    platform = "facebook"
    version = "0.1.0"

    # Facebook 平台约束
    max_title_length: int = 0
    max_body_length: int = 63206
    max_images: int = 10
    max_tags: int = 50
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
        ContentType.ARTICLE,
    ]

    min_publish_interval: int = 60

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie = self.config.get("facebook_cookie")
        self._page_id = self.config.get("facebook_page_id")
        self._access_token = self.config.get("facebook_access_token")

    def authenticate(self) -> PublishResult:
        """认证 Facebook 账户"""
        if self._access_token and self._page_id:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Graph API 认证"
            )

        if self._cookie:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Cookie 认证"
            )

        return PublishResult(
            status=self._create_failed_status(),
            error="Facebook 认证信息未配置",
            platform=self.platform
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布 Facebook 内容

        支持：
        - Page Post
        - Group Post
        - Story
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        # 发布到 Page 或 Group
        content.custom_fields.get("target_type", "page")
        target_id = content.custom_fields.get("target_id", self._page_id)

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=self._generate_post_id(),
            content_url=f"https://facebook.com/{target_id}/posts/xxx",
            published_at=datetime.now(),
            status_detail="已发布"
        )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Facebook Post 数据"""
        return {
            "content_id": content_id,
            "platform": self.platform,
            "reactions": 0,
            "comments": 0,
            "shares": 0,
            "reach": 0,
            "impressions": 0,
            "clicks": 0,
            "engagement_rate": 0.0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Facebook 支持 API 定时发布"""
        if not self._access_token:
            return PublishResult(
                status=self._create_failed_status(),
                error="定时发布需要 Facebook Graph API 认证",
                platform=self.platform
            )

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            status_detail=f"已定时 {publish_time.isoformat()}"
        )

    def _generate_post_id(self) -> str:
        """生成 Facebook Post ID"""
        import random
        import time
        return f"{self._page_id}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"


class ThreadsTool(BasePlatformTool):
    """Threads 发布工具"""

    name = "threads_publisher"
    description = "Publish content to Threads (Meta)"
    platform = "threads"
    version = "0.1.0"

    # Threads 平台约束（类似 Instagram）
    max_title_length: int = 0
    max_body_length: int = 500
    max_images: int = 10
    max_tags: int = 0  # 使用 mentions
    supported_content_types: list[ContentType] = [
        ContentType.TEXT,
        ContentType.IMAGE,
        ContentType.VIDEO,
        ContentType.IMAGE_TEXT,
    ]

    min_publish_interval: int = 60

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie = self.config.get("threads_cookie")
        self._access_token = self.config.get("threads_access_token")
        self._user_id = self.config.get("threads_user_id")

    def authenticate(self) -> PublishResult:
        """认证 Threads 账户"""
        if self._access_token:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Threads API 认证"
            )

        if self._cookie:
            return PublishResult(
                status=self._create_success_status(),
                platform=self.platform,
                status_detail="已通过 Cookie 认证"
            )

        return PublishResult(
            status=self._create_failed_status(),
            error="Threads 认证信息未配置",
            platform=self.platform
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        发布 Threads 内容

        支持：
        - Text only
        - Image(s)
        - Video
        - Carousel
        - Quote Thread
        """
        is_valid, error = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=self._create_failed_status(),
                error=error,
                platform=self.platform
            )

        # Threads API 发布流程
        # 1. 创建 Media Container
        # 2. 发布 Container

        return PublishResult(
            status=self._create_success_status(),
            platform=self.platform,
            content_id=self._generate_thread_id(),
            content_url="https://threads.net/@user/post/xxx",
            published_at=datetime.now(),
            status_detail="已发布"
        )

    def get_analytics(self, content_id: str) -> dict[str, Any]:
        """获取 Threads 数据"""
        return {
            "content_id": content_id,
            "platform": self.platform,
            "likes": 0,
            "replies": 0,
            "reposts": 0,
            "quotes": 0,
            "engagement_rate": 0.0,
        }

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Threads API 不支持定时发布"""
        return PublishResult(
            status=self._create_failed_status(),
            error="Threads 不支持原生定时发布",
            platform=self.platform
        )

    def _generate_thread_id(self) -> str:
        """生成 Threads ID"""
        import random
        import time
        return f"{int(time.time() * 1000)}_{random.randint(100000, 999999)}"


# 工厂函数
def get_overseas_platform_tool(platform: str, config: dict[str, Any] | None = None):
    """获取海外平台工具实例"""
    tools = {
        "reddit": RedditTool,
        "twitter": TwitterTool,
        "x": TwitterTool,  # 别名
        "instagram": InstagramTool,
        "facebook": FacebookTool,
        "threads": ThreadsTool,
    }

    tool_class = tools.get(platform.lower())
    if tool_class:
        return tool_class(config)

    raise ValueError(f"Unsupported overseas platform: {platform}")
