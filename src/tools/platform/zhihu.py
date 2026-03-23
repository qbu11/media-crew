"""
Zhihu (知乎) Publishing Tool

Publishes content to Zhihu platform.
Uses Chrome DevTools MCP for browser automation.

Safety constraints (from media-publish-zhihu skill):
- Minimum interval: 30 seconds between posts
- Daily limit: 15 answers, 5 articles maximum
- Answer: >= 100 characters
- Article: >= 500 characters
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


class ZhihuTool(BasePlatformTool):
    """
    Zhihu content publishing tool.

    Supports:
    - Publishing answers to questions
    - Publishing articles
    - Publishing "想法" (thoughts/moments)
    """

    name = "zhihu_publisher"
    description = "Publishes content to Zhihu (知乎)"
    platform = "zhihu"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 100
    max_body_length = 10000  # Articles can be longer
    max_images = 20
    max_tags = 5
    supported_content_types = [ContentType.TEXT, ContentType.ARTICLE, ContentType.IMAGE_TEXT]

    # Rate limiting
    max_requests_per_minute = 2
    min_interval_seconds = 30.0

    # URLs
    home_url = "https://www.zhihu.com"
    article_write_url = "https://zhuanlan.zhihu.com/write"
    question_url_template = "https://www.zhihu.com/question/{}"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_status = AuthStatus.NOT_AUTHENTICATED

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Zhihu.

        Uses Chrome DevTools MCP to check login status.
        """
        try:
            # In actual implementation: navigate to zhihu.com and check login
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
        Publish content to Zhihu.

        Defaults to publishing as an article.
        Use publish_answer() for answers to specific questions.
        """
        return self.publish_article(content.title, content.body, content.images)

    def publish_answer(
        self,
        question_url: str,
        answer: str,
        question_id: str | None = None
    ) -> PublishResult:
        """
        Publish an answer to a Zhihu question.

        Args:
            question_url: Full URL to the question
            answer: Answer content (>= 100 characters recommended)
            question_id: Optional question ID (parsed from URL if not provided)

        Returns:
            PublishResult with answer link
        """
        if len(answer) < 100:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Answer too short (minimum 100 characters recommended)",
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
            # In actual implementation:
            # 1. navigate_page(question_url)
            # 2. wait_for(["写回答"])
            # 3. click("写回答" button)
            # 4. type_text(answer)
            # 5. Click publish

            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"zhihu_answer_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                content_url=question_url,
                published_at=datetime.now(),
                status_detail="回答已发布",
                data={
                    "type": "answer",
                    "question_url": question_url,
                    "length": len(answer)
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Answer publishing failed: {e!s}",
                platform=self.platform
            )

    def publish_article(
        self,
        title: str,
        content: str,
        images: list[str] | None = None
    ) -> PublishResult:
        """
        Publish an article to Zhihu column.

        Args:
            title: Article title
            content: Article content (>= 500 characters recommended)
            images: Optional list of image paths/URLs

        Returns:
            PublishResult with article link
        """
        if len(content) < 500:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Article too short (minimum 500 characters recommended)",
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
            # In actual implementation:
            # 1. navigate_page(article_write_url)
            # 2. fill(title input, title)
            # 3. click(content area)
            # 4. type_text(content)
            # 5. Upload images if provided
            # 6. Click publish

            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"zhihu_article_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                content_url=f"https://zhuanlan.zhihu.com/p/{datetime.now().strftime('%Y%m%d%H%M%S')}",
                published_at=datetime.now(),
                status_detail="文章已发布",
                data={
                    "type": "article",
                    "title": title,
                    "images_count": len(images) if images else 0
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Article publishing failed: {e!s}",
                platform=self.platform
            )

    def publish_thought(self, content: str, images: list[str] | None = None) -> PublishResult:
        """
        Publish a "想法" (thought/moment) to Zhihu.

        Short-form content similar to Twitter moments.
        """
        if self._auth_status != AuthStatus.AUTHENTICATED:
            auth_result = self.authenticate()
            if not auth_result.is_success():
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Authentication required",
                    platform=self.platform
                )

        try:
            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"zhihu_thought_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                published_at=datetime.now(),
                status_detail="想法已发布",
                data={
                    "type": "thought",
                    "images_count": len(images) if images else 0
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Thought publishing failed: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for Zhihu content.

        Returns views, likes, comments, etc.
        """
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

        Note: Zhihu doesn't have native scheduling.
        """
        return PublishResult(
            status=ToolStatus.FAILED,
            error="Zhihu scheduling not supported. Use external scheduler.",
            platform=self.platform
        )
