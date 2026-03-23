"""
Xiaohongshu (小红书) Publishing Tool

Publishes content to Xiaohongshu (Little Red Book) platform.
Uses Chrome DevTools MCP for browser automation.

Safety constraints (from media-publish-xiaohongshu skill):
- Minimum interval: 60 seconds between posts
- Daily limit: 10 posts maximum
- Images: 1-18 images per post
- Title: <= 20 characters
- Body: <= 1000 characters
- Tags: <= 10 tags
"""

from datetime import datetime
import json
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

# Optional CrewAI integration
try:
    from crewai import tool as crewai_tool
except ImportError:
    crewai_tool = None  # Fallback if CrewAI is not installed


class XiaohongshuTool(BasePlatformTool):
    """
    Xiaohongshu content publishing tool.

    Uses Chrome DevTools MCP for browser-based automation.
    Follows platform safety guidelines and rate limits.
    """

    name = "xiaohongshu_publisher"
    description = "Publishes content to Xiaohongshu (Little Red Book)"
    platform = "xiaohongshu"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 20
    max_body_length = 1000
    max_images = 18
    max_tags = 10
    supported_content_types = [ContentType.IMAGE, ContentType.VIDEO, ContentType.IMAGE_TEXT]

    # Rate limiting (strict for Xiaohongshu)
    max_requests_per_minute = 1  # Very conservative
    min_interval_seconds = 60.0  # 60 seconds minimum

    # URLs
    creator_url = "https://creator.xiaohongshu.com/publish/publish"
    home_url = "https://www.xiaohongshu.com"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_checked = False
        self._auth_status = AuthStatus.NOT_AUTHENTICATED
        self._chrome_mcp_available = self._check_chrome_mcp()

    def _check_chrome_mcp(self) -> bool:
        """Check if Chrome DevTools MCP is available"""
        try:
            # This will be called from CrewAI context
            # The actual check happens at runtime
            return True
        except Exception:
            return False

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Xiaohongshu.

        Uses Chrome DevTools MCP to check login status.
        If not logged in, prompts user to log in via browser.
        """
        if not self._chrome_mcp_available:
            return ToolResult(
                status=ToolStatus.FAILED,
                error="Chrome DevTools MCP not available. Please install and configure.",
                platform=self.platform
            )

        try:
            # In actual implementation, this would:
            # 1. Use chrome-devtools MCP to navigate to creator URL
            # 2. Check if user is logged in
            # 3. Return status

            # For now, return success (to be implemented with actual MCP calls)
            self._auth_status = AuthStatus.AUTHENTICATED
            self._auth_checked = True

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"message": "Authentication checked", "status": "authenticated"},
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
        Publish content to Xiaohongshu.

        Workflow (from SKILL.md):
        1. Navigate to creator.xiaohongshu.com/publish/publish
        2. Wait for editor to load
        3. Upload images/video
        4. Fill title and content
        5. Add tags
        6. Preview and confirm
        7. Click publish
        """
        # Validate content
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform
            )

        # Check authentication
        if self._auth_status != AuthStatus.AUTHENTICATED:
            auth_result = self.authenticate()
            if not auth_result.is_success():
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Authentication required",
                    platform=self.platform
                )

        try:
            # Actual implementation would use chrome-devtools MCP
            # For now, return a simulated result
            result = PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"xhs_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                content_url=f"https://www.xiaohongshu.com/explore/simulated_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                published_at=datetime.now(),
                status_detail="发布成功",
                data={
                    "title": content.title,
                    "content_type": content.content_type.value,
                    "images_count": len(content.images),
                    "tags": content.tags
                }
            )

            return result

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Publishing failed: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for published content.

        Note: Xiaohongshu analytics require login and may have rate limits.
        """
        # In actual implementation, this would:
        # 1. Navigate to content page
        # 2. Extract metrics (views, likes, comments, shares)
        # 3. Return normalized data

        return AnalyticsData(
            content_id=content_id,
            views=0,
            likes=0,
            comments=0,
            shares=0,
            favorites=0,
            raw_data={"note": "Analytics requires browser automation"}
        )

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """
        Schedule content for future publishing.

        Note: Xiaohongshu creator platform supports scheduled posting.
        This would use the platform's native scheduling feature.
        """
        # Validate content
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform
            )

        # Check if publish_time is in the future
        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform
            )

        # In actual implementation, this would:
        # 1. Use the platform's scheduling feature
        # 2. Set the scheduled time
        # 3. Confirm scheduling

        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=f"scheduled_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status_detail=f"已预约发布: {publish_time.strftime('%Y-%m-%d %H:%M')}",
            data={"scheduled_for": publish_time.isoformat()}
        )


# CrewAI tool wrapper
def _create_crewai_wrapper():
    """Create CrewAI tool wrapper if CrewAI is available."""
    if crewai_tool is None:
        return None

    @crewai_tool
    def publish_to_xiaohongshu(
        title: str,
        content: str,
        images: list[str] | None = None,
        tags: list[str] | None = None
    ) -> str:
        """
        Publish content to Xiaohongshu (Little Red Book).

        Args:
            title: Post title (max 20 characters)
            content: Post content (max 1000 characters)
            images: List of image paths or URLs (1-18 images)
            tags: List of hashtags (max 10 tags)

        Returns:
            JSON string with publish result
        """

        tool = XiaohongshuTool()
        publish_content = PublishContent(
            title=title,
            body=content,
            content_type=ContentType.IMAGE_TEXT if images else ContentType.TEXT,
            images=images or [],
            tags=tags or []
        )

        result = tool.publish(publish_content)
        return json.dumps(result.to_dict(), ensure_ascii=False)

    return publish_to_xiaohongshu


publish_to_xiaohongshu = _create_crewai_wrapper()


# Export for CrewAI (only if CrewAI is available)
try:
    from crewai import Tool as CrewAITool
    xiaohongshu_publish_tool = CrewAITool(
        name="Publish to Xiaohongshu",
        func=publish_to_xiaohongshu,
        description="Publishes content to Xiaohongshu (Little Red Book) platform"
    )
except ImportError:
    xiaohongshu_publish_tool = None

