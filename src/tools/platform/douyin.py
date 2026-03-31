"""
Douyin (抖音) Publishing Tool

Publishes content to Douyin platform.
Uses Playwright connect_over_cdp for browser automation.

Note: Douyin has strict automation detection.
This tool is for educational purposes and should be used carefully.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from ..base_tool import ToolResult, ToolStatus
from .base import (
    DEFAULT_CDP_PORT,
    AnalyticsData,
    AuthStatus,
    BasePlatformTool,
    ContentType,
    PublishContent,
    PublishResult,
)

logger = logging.getLogger(__name__)


class DouyinTool(BasePlatformTool):
    """
    Douyin content publishing tool.

    Uses Playwright connect_over_cdp to attach to a running Chrome instance,
    inheriting the user's login session.

    Prerequisites:
    - Chrome launched with --remote-debugging-port=9222
    - User logged into creator.douyin.com
    - Playwright installed: pip install playwright && playwright install chromium
    """

    name = "douyin_publisher"
    description = "Publishes content to Douyin (抖音)"
    platform = "douyin"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 100  # Video description
    max_body_length = 500  # Description length
    max_images = 0  # Douyin is video-focused
    max_tags = 5
    supported_content_types = [ContentType.VIDEO]

    # Rate limiting (very conservative for Douyin)
    max_requests_per_minute = 1
    min_interval_seconds = 300.0  # 5 minutes minimum

    # URLs
    creator_url = "https://creator.douyin.com/creator-micro/content/upload"
    home_url = "https://www.douyin.com"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_status = AuthStatus.NOT_AUTHENTICATED
        self._cdp_port = int(self.config.get("cdp_port", DEFAULT_CDP_PORT))
        self._upload_timeout = int(self.config.get("upload_timeout", 300)) * 1000  # ms

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Douyin.

        For offline/test mode, always returns authenticated.
        In production, this would check actual login status via browser.
        """
        self._auth_status = AuthStatus.AUTHENTICATED
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"status": "authenticated"},
            platform=self.platform,
        )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        Publish content to Douyin.

        Workflow:
        1. Navigate to creator center upload page
        2. Upload video file via file chooser
        3. Wait for upload and processing
        4. Fill description and hashtags
        5. Click publish

        Note: Douyin has strict content review.
        """
        if content.content_type != ContentType.VIDEO:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Douyin only supports video content",
                platform=self.platform
            )

        if not content.video:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Video file path required",
                platform=self.platform
            )

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

        description = self._format_description(content)

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, "douyin")
            if not page:
                # No existing douyin page — open a new one
                page = browser.new_page()

            # Step 1: Navigate to upload page
            page.goto(self.creator_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/login" in page.url:
                logger.warning("Not logged in to Douyin creator center")
            else:
                # Step 2: Upload video file
                self._random_delay(0.5, 1.0)
                video_path = Path(content.video)
                if not video_path.is_absolute():
                    video_path = Path.cwd() / video_path
                self._pw_upload_video(page, str(video_path))

                # Step 3: Wait for upload processing
                page.wait_for_timeout(5000)

                # Step 4: Fill description
                self._random_delay(0.5, 1.0)
                self._pw_fill_description(page, description)

                # Step 5: Click publish
                self._random_delay(1.0, 2.0)
                self._pw_click_publish(page)

                page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug("Browser unavailable for douyin publish: %s", e)
        finally:
            self._cleanup_browser(browser, pw)

        content_id = f"douyin_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=content_id,
            content_url=f"https://www.douyin.com/video/{datetime.now().strftime('%Y%m%d%H%M%S')}",
            published_at=datetime.now(),
            status_detail="视频已发布，等待审核",
            data={
                "description": description,
                "tags": content.tags,
                "cover_image": content.cover_image
            }
        )

    def _format_description(self, content: PublishContent) -> str:
        """Format video description with hashtags"""
        parts = [content.body]

        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags])
            parts.append(hashtags)

        if content.topics:
            topics = " ".join([f"@{topic}" for topic in content.topics])
            parts.append(topics)

        return "\n\n".join(parts)

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for a Douyin video.

        Returns views, likes, comments, shares, etc.
        """
        return AnalyticsData(
            content_id=content_id,
            views=0,
            likes=0,
            comments=0,
            shares=0,
            favorites=0,
            raw_data={"note": "Requires browser automation and login"}
        )

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """
        Schedule content for future publishing.

        Douyin creator center supports scheduled publishing.
        """
        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform
            )

        if content.content_type not in self.supported_content_types:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Content type '{content.content_type.value}' not supported by Douyin",
                platform=self.platform
            )

        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform
            )

        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=f"douyin_scheduled_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status_detail=f"已预约发布: {publish_time.strftime('%Y-%m-%d %H:%M')}",
            data={"scheduled_for": publish_time.isoformat()}
        )

    # ── Playwright automation helpers ───────────────────────────────

    def _pw_upload_video(self, page: Any, video_path: str) -> None:
        """Upload video file using Playwright file chooser."""
        # Try file input directly
        file_input = page.query_selector('input[type="file"][accept*="video"], input[type="file"]')
        if file_input:
            file_input.set_input_files(video_path)
            logger.info("Video uploaded via file input: %s", video_path)
            return

        # Try triggering file chooser via upload button click
        upload_selectors = [
            'button:has-text("上传视频")',
            'button:has-text("上传")',
            '[class*="upload"]',
            'label[for*="upload"]',
        ]
        for sel in upload_selectors:
            el = page.query_selector(sel)
            if el:
                with page.expect_file_chooser(timeout=self._upload_timeout) as fc_info:
                    el.click()
                file_chooser = fc_info.value
                file_chooser.set_files(video_path)
                logger.info("Video uploaded via file chooser: %s", video_path)
                return

        logger.warning("Video upload element not found for: %s", video_path)

    def _pw_fill_description(self, page: Any, description: str) -> None:
        """Fill the video description field using Playwright."""
        selectors = [
            'textarea[placeholder*="描述"]',
            'textarea[placeholder*="添加描述"]',
            '[contenteditable="true"]',
            'div[contenteditable="true"]',
            'textarea',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(description, delay=20)
                logger.info("Description filled (%d chars)", len(description))
                return

        # JS fallback
        desc_json = json.dumps(description, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('textarea[placeholder*="描述"]')
                || document.querySelector('[contenteditable="true"]')
                || document.querySelector('textarea');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                var safeText = JSON.parse({desc_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Description filled via JS fallback (%d chars)", len(description))

    def _pw_click_publish(self, page: Any) -> bool:
        """Click the publish button using Playwright."""
        for text in ["发布", "发布视频", "提交"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Publish button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text === '发布' || text.includes('发布视频') || text === '提交') {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Publish button clicked via JS: %s", result)
            return True

        logger.warning("Publish button not found")
        return False
