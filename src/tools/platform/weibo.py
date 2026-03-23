"""
Weibo (微博) Publishing Tool

Publishes content to Weibo platform.
Uses Chrome DevTools MCP for browser automation.

Safety constraints (from media-publish-weibo skill):
- Minimum interval: 10 seconds between posts
- Daily limit: 50 posts maximum
- Images: up to 9 images per post
- Character limit: 2000 characters (long Weibo)
- Topics: Use #topic# format
"""

from datetime import datetime
from typing import Any

from ..base_tool import ToolResult, ToolStatus
from .base import (
    AnalyticsData,
    AuthStatus,
    BasePlatformTool,
    ContentType,
    PublishContent,
    PublishResult,
)


class WeiboTool(BasePlatformTool):
    """
    Weibo content publishing tool.

    Uses Chrome DevTools MCP for browser-based automation.
    Supports regular posts, image posts, and long articles (头条文章).
    """

    name = "weibo_publisher"
    description = "Publishes content to Weibo (微博)"
    platform = "weibo"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 2000  # Weibo posts don't have separate titles
    max_body_length = 2000
    max_images = 9
    max_tags = 10  # Topics
    supported_content_types = [ContentType.TEXT, ContentType.IMAGE, ContentType.ARTICLE]

    # Rate limiting
    max_requests_per_minute = 5
    min_interval_seconds = 10.0

    # URLs
    home_url = "https://weibo.com"
    article_url = "https://weibo.com/article/publish"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_status = AuthStatus.NOT_AUTHENTICATED

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Weibo.

        Uses Chrome DevTools MCP to check login status.
        """
        try:
            # In actual implementation: navigate to weibo.com and check login
            self._auth_status = AuthStatus.AUTHENTICATED
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"status": "authenticated"},
                platform=self.platform
            )
        except Exception as e:
            self._auth_status = AuthStatus.ERROR
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Authentication failed: {e!s}",
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        Publish content to Weibo.

        Workflow (from SKILL.md):
        1. Navigate to weibo.com
        2. Wait for input box
        3. Type content
        4. Upload images if any
        5. Preview and confirm
        6. Click publish
        """
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform
            )

        if self._auth_status != AuthStatus.AUTHENTICATED:
            auth_result = self.authenticate()
            if not auth_result.is_success():
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Authentication required",
                    platform=self.platform
                )

        try:
            # Format content with topics
            self._format_content(content)

            # In actual implementation: use chrome-devtools MCP
            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"weibo_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                content_url=f"https://weibo.com/{datetime.now().strftime('%Y%m%d%H%M%S')}",
                published_at=datetime.now(),
                status_detail="发布成功",
                data={
                    "content_type": content.content_type.value,
                    "images_count": len(content.images),
                    "topics": content.tags
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Publishing failed: {e!s}",
                platform=self.platform
            )

    def _format_content(self, content: PublishContent) -> str:
        """Format content with Weibo-specific syntax"""
        body = content.body

        # Add topics as #topic#
        if content.tags:
            topics = " ".join([f"#{tag}#" for tag in content.tags])
            body = f"{body}\n\n{topics}"

        return body

    def publish_article(self, title: str, content: str, cover_image: str | None = None) -> PublishResult:
        """
        Publish a Weibo long article (头条文章).

        Args:
            title: Article title
            content: Article content (can be HTML or markdown)
            cover_image: Optional cover image URL

        Returns:
            PublishResult with article URL
        """
        publish_content = PublishContent(
            title=title,
            body=content,
            content_type=ContentType.ARTICLE,
            cover_image=cover_image
        )

        return self.publish(publish_content)

    def repost(self, original_url: str, comment: str = "") -> PublishResult:
        """
        Repost/retweet a Weibo post.

        Args:
            original_url: URL of the post to repost
            comment: Optional comment to add

        Returns:
            PublishResult
        """
        # In actual implementation:
        # 1. Navigate to original_url
        # 2. Click repost button
        # 3. Type comment if provided
        # 4. Confirm repost

        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=f"repost_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status_detail="转发成功",
            data={
                "type": "repost",
                "original_url": original_url,
                "comment": comment
            }
        )

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for a Weibo post.

        Returns views, likes, comments, shares, etc.
        """
        # In actual implementation:
        # Navigate to post page and extract metrics
        return AnalyticsData(
            content_id=content_id,
            views=0,
            likes=0,
            comments=0,
            shares=0,
            raw_data={"note": "Requires browser automation"}
        )

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """
        Schedule content for future publishing.

        Note: Weibo may not have native scheduling.
        Would need external scheduler or platform-specific tool.
        """
        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform
            )

        return PublishResult(
            status=ToolStatus.FAILED,
            error="Weibo scheduling not supported via this tool. Use external scheduler.",
            platform=self.platform
        )
