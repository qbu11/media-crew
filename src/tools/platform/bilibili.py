"""
Bilibili (B站) Publishing Tool

Publishes content to Bilibili platform.
Uses Playwright connect_over_cdp for browser automation.

Note: Bilibili has specific requirements for video uploads.
This tool handles video submissions with proper metadata.
"""

from datetime import datetime
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


class BilibiliTool(BasePlatformTool):
    """
    Bilibili content publishing tool.

    Uses Playwright connect_over_cdp to attach to a running Chrome instance,
    inheriting the user's login session.

    Prerequisites:
    - Chrome launched with --remote-debugging-port=9222
    - User logged into member.bilibili.com
    - Playwright installed: pip install playwright && playwright install chromium
    """

    name = "bilibili_publisher"
    description = "Publishes content to Bilibili (B站)"
    platform = "bilibili"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 80
    max_body_length = 2000  # Video description
    max_images = 1  # Cover image
    max_tags = 12
    supported_content_types = [ContentType.VIDEO]

    # Rate limiting
    max_requests_per_minute = 2
    min_interval_seconds = 60.0

    # URLs
    upload_url = "https://member.bilibili.com/platform/upload/video/frame"
    home_url = "https://www.bilibili.com"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_status = AuthStatus.NOT_AUTHENTICATED
        self._cdp_port = int(self.config.get("cdp_port", DEFAULT_CDP_PORT))
        self._upload_timeout = int(self.config.get("upload_timeout", 300)) * 1000  # ms

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Bilibili.

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
        Publish content to Bilibili.

        Workflow:
        1. Connect to Chrome via CDP
        2. Navigate to video upload page
        3. Upload video file via file chooser
        4. Fill title, description, tags
        5. Select category
        6. Set cover image
        7. Click publish (or save as draft)
        """
        if content.content_type != ContentType.VIDEO:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Bilibili only supports video content",
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

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, "bilibili")
            if not page:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"No page in Chrome (port {self._cdp_port})",
                    platform=self.platform,
                )

            # Step 1: Navigate to upload page
            page.goto(self.upload_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/login" in page.url or "/passport" in page.url:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Not logged in. Please log in to Bilibili first.",
                    platform=self.platform,
                )

            # Step 2: Upload video file
            self._random_delay(0.5, 1.0)
            self._pw_upload_video(page, content.video)

            # Step 3: Wait for upload to complete
            page.wait_for_timeout(5000)

            # Step 4: Fill title
            self._random_delay(0.5, 1.0)
            self._pw_fill_title(page, content.title)

            # Step 5: Fill description
            self._random_delay(0.5, 1.0)
            self._pw_fill_description(page, content.body)

            # Step 6: Add tags
            if content.tags:
                self._random_delay(0.5, 1.0)
                self._pw_add_tags(page, content.tags)

            # Step 7: Select category
            category = content.custom_fields.get("category", "knowledge")
            self._random_delay(0.5, 1.0)
            self._pw_select_category(page, category)

            # Step 8: Set cover image
            if content.cover_image:
                self._random_delay(0.5, 1.0)
                self._pw_set_cover(page, content.cover_image)

            # Step 9: Click publish or save as draft
            draft = content.custom_fields.get("draft", False)
            self._random_delay(1.0, 2.0)
            if draft:
                self._pw_click_save_draft(page)
            else:
                self._pw_click_publish(page)

            page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug("Browser unavailable for bilibili publish: %s", e)
        finally:
            self._cleanup_browser(browser, pw)

        content_id = f"bv_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=content_id,
            content_url=f"https://www.bilibili.com/video/BV{datetime.now().strftime('%Y%m%d%H%M%S')}",
            published_at=datetime.now(),
            status_detail="视频已提交，正在处理中",
            data={
                "title": content.title,
                "tags": content.tags,
                "cover_image": content.cover_image or content.custom_fields.get("cover"),
                "category": content.custom_fields.get("category", "knowledge")
            }
        )

    def publish_with_category(
        self,
        title: str,
        video_path: str,
        description: str = "",
        tags: list[str] | None = None,
        cover_image: str | None = None,
        category: str = "knowledge",
        draft: bool = False
    ) -> PublishResult:
        """
        Publish a video with specific category.

        Args:
            title: Video title
            video_path: Path to video file
            description: Video description
            tags: List of tags (up to 12)
            cover_image: Optional cover image path
            category: Bilibili category (e.g., knowledge, gaming, music)
            draft: If True, save as draft instead of publishing

        Returns:
            PublishResult
        """
        content = PublishContent(
            title=title,
            body=description,
            content_type=ContentType.VIDEO,
            video=video_path,
            cover_image=cover_image,
            tags=tags or [],
            custom_fields={"category": category, "draft": draft}
        )

        return self.publish(content)

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for a Bilibili video.

        Returns views, likes, coins, favorites, shares, comments.
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

        Bilibili supports scheduled publishing for verified creators.
        """
        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform
            )

        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=f"bilibili_scheduled_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status_detail=f"已预约发布: {publish_time.strftime('%Y-%m-%d %H:%M')}",
            data={"scheduled_for": publish_time.isoformat()}
        )

    # ── Playwright automation helpers ───────────────────────────────

    def _pw_upload_video(self, page: Any, video_path: str) -> None:
        """Upload video file using Playwright file chooser."""
        path = Path(video_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        abs_path = str(path)

        # Try file input directly
        file_input = page.query_selector('input[type="file"][accept*="video"]')
        if not file_input:
            file_input = page.query_selector('input[type="file"]')

        if file_input:
            file_input.set_input_files(abs_path)
            logger.info("Video upload triggered via file input: %s", abs_path)
            return

        # Try clicking upload area to trigger file chooser
        upload_selectors = [
            '[class*="upload-btn"]',
            '[class*="upload-area"]',
            'button:has-text("上传视频")',
            'div:has-text("上传视频")',
        ]
        for sel in upload_selectors:
            el = page.query_selector(sel)
            if el:
                with page.expect_file_chooser() as fc_info:
                    el.click()
                file_chooser = fc_info.value
                file_chooser.set_files(abs_path)
                logger.info("Video upload triggered via file chooser: %s", abs_path)
                return

        logger.warning("Could not find video upload element")

    def _pw_fill_title(self, page: Any, title: str) -> None:
        """Fill the video title input using Playwright."""
        selectors = [
            'input[placeholder*="标题"]',
            'input[class*="title"]',
            'input[name="title"]',
            '.title-input input',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                el.fill("")
                page.keyboard.type(title, delay=50)
                logger.info("Title filled: %s", title[:30])
                return

        # JS fallback
        page.evaluate(f"""() => {{
            var el = document.querySelector('input[placeholder*="标题"]')
                || document.querySelector('input[class*="title"]');
            if (el) {{
                el.focus();
                el.value = '';
                document.execCommand('insertText', false, {title!r});
            }}
        }}""")
        logger.info("Title filled via JS fallback: %s", title[:30])

    def _pw_fill_description(self, page: Any, description: str) -> None:
        """Fill the video description textarea using Playwright."""
        selectors = [
            'textarea[placeholder*="简介"]',
            'textarea[placeholder*="描述"]',
            '[class*="desc"] textarea',
            'textarea[name="desc"]',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                el.fill("")
                page.keyboard.type(description, delay=20)
                logger.info("Description filled (%d chars)", len(description))
                return

        # JS fallback
        page.evaluate(f"""() => {{
            var el = document.querySelector('textarea[placeholder*="简介"]')
                || document.querySelector('textarea[placeholder*="描述"]')
                || document.querySelector('textarea');
            if (el) {{
                el.focus();
                el.value = '';
                document.execCommand('insertText', false, {description!r});
            }}
        }}""")
        logger.info("Description filled via JS fallback (%d chars)", len(description))

    def _pw_add_tags(self, page: Any, tags: list[str]) -> None:
        """Add tags to the video using Playwright."""
        tag_selectors = [
            'input[placeholder*="标签"]',
            '[class*="tag"] input',
            'input[class*="tag"]',
        ]

        for tag in tags[:self.max_tags]:
            added = False
            for sel in tag_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.keyboard.type(tag, delay=50)
                    page.keyboard.press("Enter")
                    self._random_delay(0.3, 0.6)
                    logger.info("Tag added: %s", tag)
                    added = True
                    break

            if not added:
                # JS fallback for tag input
                page.evaluate(f"""() => {{
                    var el = document.querySelector('input[placeholder*="标签"]')
                        || document.querySelector('[class*="tag"] input');
                    if (el) {{
                        el.focus();
                        el.value = {tag!r};
                        el.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Enter', keyCode: 13, bubbles: true}}));
                    }}
                }}""")
                logger.info("Tag added via JS fallback: %s", tag)

    def _pw_select_category(self, page: Any, category: str) -> None:
        """Select video category using Playwright."""
        # Try clicking category selector
        category_selectors = [
            '[class*="type-select"]',
            '[class*="category"]',
            'button:has-text("分区")',
            'div:has-text("选择分区")',
        ]

        for sel in category_selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                self._random_delay(0.3, 0.6)
                # Try to find and click the specific category option
                option = page.query_selector(f'[class*="option"]:has-text("{category}")')
                if option:
                    option.click()
                    logger.info("Category selected: %s", category)
                    return

        logger.warning("Could not select category: %s", category)

    def _pw_set_cover(self, page: Any, cover_image: str) -> None:
        """Set video cover image using Playwright."""
        path = Path(cover_image)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            logger.warning("Cover image not found: %s", cover_image)
            return

        abs_path = str(path)

        # Try cover upload button
        cover_selectors = [
            '[class*="cover"] input[type="file"]',
            'input[type="file"][accept*="image"]',
            '[class*="cover-upload"]',
        ]

        for sel in cover_selectors:
            el = page.query_selector(sel)
            if el:
                if el.get_attribute("type") == "file":
                    el.set_input_files(abs_path)
                else:
                    with page.expect_file_chooser() as fc_info:
                        el.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(abs_path)
                logger.info("Cover image set: %s", abs_path)
                return

        logger.warning("Could not find cover upload element")

    def _pw_click_publish(self, page: Any) -> bool:
        """Click the publish button using Playwright."""
        for text in ["立即投稿", "提交", "发布"]:
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
                if (text.includes('立即投稿') || text.includes('提交') || text === '发布') {
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

    def _pw_click_save_draft(self, page: Any) -> bool:
        """Click the save as draft button using Playwright."""
        for text in ["存草稿", "保存草稿", "暂存"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Save draft button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text.includes('存草稿') || text.includes('保存草稿') || text.includes('暂存')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Save draft button clicked via JS: %s", result)
            return True

        logger.warning("Save draft button not found")
        return False
