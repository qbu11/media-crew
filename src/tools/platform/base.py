"""
Base Platform Tool for Content Publishing

Provides the abstract base class that all platform-specific tools must implement.
Defines common interface for authentication, publishing, analytics, and scheduling.
"""

from abc import ABC, abstractmethod
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import random
import time
from typing import Any

from ..base_tool import BaseTool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

DEFAULT_CDP_PORT = 9222
CDP_ENDPOINT_URL = "http://localhost:{port}"


class ContentType(Enum):
    """Supported content types"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    ARTICLE = "article"
    IMAGE_TEXT = "image_text"  # Multi-image posts


class AuthStatus(Enum):
    """Authentication status"""
    AUTHENTICATED = "authenticated"
    NOT_AUTHENTICATED = "not_authenticated"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class PublishContent:
    """
    Standardized content structure for publishing.

    Attributes:
        title: Content title
        body: Main content text
        content_type: Type of content (text, image, video, article)
        images: List of image paths or URLs
        video: Video path or URL
        cover_image: Cover image for video/article
        tags: List of hashtags or topic tags
        topics: Platform-specific topic identifiers
        location: Location tag
        mentions: User mentions
        custom_fields: Platform-specific fields
    """
    title: str
    body: str
    content_type: ContentType = ContentType.TEXT
    images: list[str] = field(default_factory=list)
    video: str | None = None
    cover_image: str | None = None
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    location: str | None = None
    mentions: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "body": self.body,
            "content_type": self.content_type.value,
            "images": self.images,
            "video": self.video,
            "cover_image": self.cover_image,
            "tags": self.tags,
            "topics": self.topics,
            "location": self.location,
            "mentions": self.mentions,
            "custom_fields": self.custom_fields
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublishContent":
        """Create from dictionary"""
        if isinstance(data.get("content_type"), str):
            data["content_type"] = ContentType(data["content_type"])
        return cls(**data)


@dataclass
class PublishResult(ToolResult):
    """
    Result of a publish operation.

    Extends ToolResult with platform-specific publishing details.
    """
    content_id: str | None = None
    content_url: str | None = None
    preview_url: str | None = None
    published_at: datetime | None = None
    status_detail: str | None = None  # e.g., "审核中", "已发布"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result.update({
            "content_id": self.content_id,
            "content_url": self.content_url,
            "preview_url": self.preview_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "status_detail": self.status_detail
        })
        return result


@dataclass
class AnalyticsData:
    """
    Standardized analytics data structure.

    Attributes:
        content_id: Content identifier
        views: View count
        likes: Like count
        comments: Comment count
        shares: Share count
        favorites: Favorite/collect count
        forwards: Forward count
        engagement_rate: Engagement rate (0-1)
        reach: Estimated reach
        impressions: Impression count
        click_through_rate: CTR (0-1)
        period_start: Analytics period start
        period_end: Analytics period end
        raw_data: Platform-specific raw data
    """
    content_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    favorites: int = 0
    forwards: int = 0
    engagement_rate: float = 0.0
    reach: int = 0
    impressions: int = 0
    click_through_rate: float = 0.0
    period_start: datetime | None = None
    period_end: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "content_id": self.content_id,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "favorites": self.favorites,
            "forwards": self.forwards,
            "engagement_rate": self.engagement_rate,
            "reach": self.reach,
            "impressions": self.impressions,
            "click_through_rate": self.click_through_rate,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "raw_data": self.raw_data
        }


class BasePlatformTool(BaseTool, ABC):
    """
    Abstract base class for platform-specific publishing tools.

    All platform tools (Xiaohongshu, WeChat, Weibo, etc.) must inherit
    from this class and implement the required abstract methods.
    """

    # Platform-specific constraints (override in subclass)
    max_title_length: int = 100
    max_body_length: int = 10000
    max_images: int = 9
    max_tags: int = 10
    supported_content_types: list[ContentType] = [ContentType.TEXT, ContentType.IMAGE]

    # ── Playwright CDP helpers ─────────────────────────────────────

    def _get_cdp_port(self) -> int:
        """Get CDP port from config, default 9222."""
        return int(self.config.get("cdp_port", DEFAULT_CDP_PORT))

    def _get_cdp_endpoint(self) -> str:
        """Return the CDP endpoint URL for Playwright."""
        return CDP_ENDPOINT_URL.format(port=self._get_cdp_port())

    def _connect_browser(self) -> tuple[Any, Any]:
        """
        Connect to existing Chrome via Playwright CDP.

        Returns a (browser, playwright_instance) tuple.
        Caller must call browser.close() and playwright_instance.stop()
        in a finally block.

        Note: If connection fails, playwright_instance is cleaned up
        before the exception is re-raised. The caller should NOT call
        _cleanup_browser() when this raises an exception.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as err:
            raise RuntimeError(
                "Playwright required. Install: pip install playwright && playwright install chromium"
            ) from err

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(self._get_cdp_endpoint())
            return browser, pw
        except Exception:
            # Clean up playwright instance on connection failure
            # Caller should NOT call _cleanup_browser() when we raise
            with contextlib.suppress(Exception):
                pw.stop()
            raise

    def _find_platform_page(self, browser: Any, url_fragment: str) -> Any:
        """Find an existing page/tab in the connected browser matching url_fragment."""
        for context in browser.contexts:
            for page in context.pages:
                if url_fragment in page.url:
                    return page
        if browser.contexts and browser.contexts[0].pages:
            return browser.contexts[0].pages[0]
        return None

    def _random_delay(self, lo: float = 0.5, hi: float = 1.5) -> None:
        """Human-like random delay between actions."""
        time.sleep(random.uniform(lo, hi))

    def _cleanup_browser(self, browser: Any, pw: Any) -> None:
        """Safely close browser and playwright instance."""
        if browser:
            with contextlib.suppress(Exception):
                browser.close()
        if pw:
            with contextlib.suppress(Exception):
                pw.stop()

    def check_login_via_playwright(
        self,
        url: str,
        login_url_fragments: list[str] | None = None,
    ) -> ToolResult:
        """
        Check login status by navigating to a URL and checking for login redirects.

        Args:
            url: Platform URL to navigate to
            login_url_fragments: URL fragments that indicate a login page
                (e.g., ["/login", "/signin"])

        Returns:
            ToolResult with authentication status
        """
        if login_url_fragments is None:
            login_url_fragments = ["/login", "/signin"]

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, url.split("//")[-1].split("/")[0])
            if not page:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=(
                        f"No page found in Chrome (port {self._get_cdp_port()}). "
                        f"Please open {url} in Chrome first."
                    ),
                    platform=self.platform,
                )

            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            current_url = page.url

            for fragment in login_url_fragments:
                if fragment in current_url:
                    return ToolResult(
                        status=ToolStatus.FAILED,
                        error=(
                            f"Not logged into {self.platform}. "
                            f"Please log in at {url} first."
                        ),
                        platform=self.platform,
                        data={"authenticated": False, "url": current_url},
                    )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"authenticated": True, "url": current_url},
                platform=self.platform,
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Login check failed: {e!s}",
                platform=self.platform,
            )
        finally:
            self._cleanup_browser(browser, pw)

    @abstractmethod
    def authenticate(self) -> ToolResult:
        """
        Authenticate with the platform.

        Returns:
            ToolResult with authentication status

        Implementation notes:
        - For browser-based tools: check if logged in, prompt if not
        - For API-based tools: validate credentials, refresh token if needed
        """
        pass

    @abstractmethod
    def publish(self, content: PublishContent) -> PublishResult:
        """
        Publish content to the platform.

        Args:
            content: Content to publish

        Returns:
            PublishResult with publishing outcome

        Implementation notes:
        - Validate content against platform constraints
        - Execute publishing workflow
        - Handle platform-specific errors
        """
        pass

    @abstractmethod
    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics data for published content.

        Args:
            content_id: Platform-specific content identifier

        Returns:
            AnalyticsData with metrics

        Implementation notes:
        - Fetch analytics from platform API or browser
        - Normalize data to AnalyticsData structure
        """
        pass

    @abstractmethod
    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """
        Schedule content for future publishing.

        Args:
            content: Content to publish
            publish_time: Scheduled publish time

        Returns:
            PublishResult with scheduling outcome

        Implementation notes:
        - Use platform's native scheduling if available
        - Otherwise, return error or use external scheduler
        """
        pass

    def check_auth_status(self) -> AuthStatus:
        """
        Check current authentication status.

        Returns:
            AuthStatus indicating current state
        """
        result = self.authenticate()
        if result.is_success():
            return AuthStatus.AUTHENTICATED
        elif "expired" in (result.error or "").lower():
            return AuthStatus.EXPIRED
        elif "not authenticated" in (result.error or "").lower():
            return AuthStatus.NOT_AUTHENTICATED
        return AuthStatus.ERROR

    def validate_content(self, content: PublishContent) -> tuple[bool, str | None]:
        """
        Validate content against platform constraints.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check content type support
        if content.content_type not in self.supported_content_types:
            return False, f"Content type {content.content_type.value} not supported by {self.platform}"

        # Check title length
        if len(content.title) > self.max_title_length:
            return False, f"Title exceeds max length ({len(content.title)} > {self.max_title_length})"

        # Check body length
        if len(content.body) > self.max_body_length:
            return False, f"Body exceeds max length ({len(content.body)} > {self.max_body_length})"

        # Check image count
        if len(content.images) > self.max_images:
            return False, f"Too many images ({len(content.images)} > {self.max_images})"

        # Check tag count
        if len(content.tags) > self.max_tags:
            return False, f"Too many tags ({len(content.tags)} > {self.max_tags})"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Default execute method - publishes content.

        Override in subclass for different default behavior.
        """
        content_data = kwargs.get("content")
        if isinstance(content_data, dict):
            content = PublishContent.from_dict(content_data)
        elif isinstance(content_data, PublishContent):
            content = content_data
        else:
            return ToolResult(
                status=ToolStatus.FAILED,
                error="Invalid content parameter",
                platform=self.platform
            )

        return self.publish(content)

    def _create_success_status(self) -> ToolStatus:
        """Helper to create a success status."""
        return ToolStatus.SUCCESS

    def _create_failed_status(self) -> ToolStatus:
        """Helper to create a failed status."""
        return ToolStatus.FAILED

    def get_constraints(self) -> dict[str, Any]:
        """Get platform constraints"""
        return {
            "platform": self.platform,
            "max_title_length": self.max_title_length,
            "max_body_length": self.max_body_length,
            "max_images": self.max_images,
            "max_tags": self.max_tags,
            "supported_content_types": [ct.value for ct in self.supported_content_types]
        }
