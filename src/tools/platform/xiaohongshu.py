"""
Xiaohongshu (小红书) Publishing Tool

Publishes content to Xiaohongshu (Little Red Book) platform.
Uses Playwright connect_over_cdp to attach to an existing Chrome instance,
inheriting login state and avoiding bot detection.

Safety constraints (from media-publish-xiaohongshu skill):
- Minimum interval: 60 seconds between posts
- Daily limit: 10 posts maximum
- Images: 1-18 images per post
- Title: <= 20 characters
- Body: <= 1000 characters
- Tags: <= 10 tags
"""

import json
import logging
import random
import time
import urllib.request
from datetime import datetime
from pathlib import Path
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
    crewai_tool = None

logger = logging.getLogger(__name__)

# CDP connection defaults
DEFAULT_CDP_PORT = 9222
CDP_ENDPOINT_URL = "http://localhost:{port}"


class XiaohongshuTool(BasePlatformTool):
    """
    Xiaohongshu content publishing tool.

    Uses Playwright connect_over_cdp to attach to a running Chrome instance,
    inheriting the user's login session. This avoids bot detection since
    Playwright drives the real browser profile rather than a headless instance.

    Prerequisites:
    - Chrome launched with --remote-debugging-port=9222
    - User logged into xiaohongshu.com / creator.xiaohongshu.com
    - Playwright installed: pip install playwright && playwright install chromium
    """

    name = "xiaohongshu_publisher"
    description = "Publishes content to Xiaohongshu (Little Red Book)"
    platform = "xiaohongshu"
    version = "0.3.0"

    # Platform constraints
    max_title_length = 20
    max_body_length = 1000
    max_images = 18
    max_tags = 10
    supported_content_types = [ContentType.IMAGE, ContentType.VIDEO, ContentType.IMAGE_TEXT]

    # Rate limiting (strict for Xiaohongshu)
    max_requests_per_minute = 1
    min_interval_seconds = 60.0

    # URLs
    creator_url = "https://creator.xiaohongshu.com/publish/publish"
    home_url = "https://www.xiaohongshu.com"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._auth_checked = False
        self._auth_status = AuthStatus.NOT_AUTHENTICATED
        self._cdp_port = int(self.config.get("cdp_port", DEFAULT_CDP_PORT))

    # ── Playwright helpers ────────────────────────────────────────

    def _get_cdp_endpoint(self) -> str:
        """Return the CDP endpoint URL for Playwright."""
        return CDP_ENDPOINT_URL.format(port=self._cdp_port)

    def _connect_browser(self) -> Any:
        """
        Connect to existing Chrome via Playwright CDP.

        Returns a (browser, playwright_instance) tuple.
        Caller must call browser.close() and playwright_instance.stop().
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright required. Install: pip install playwright && playwright install chromium"
            )

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(self._get_cdp_endpoint())
            return browser, pw
        except Exception:
            pw.stop()
            raise

    def _find_xhs_page(self, browser: Any) -> Any:
        """Find an existing Xiaohongshu page/tab in the connected browser."""
        for context in browser.contexts:
            for page in context.pages:
                if "xiaohongshu" in page.url:
                    return page
        # No existing tab — use the first context's first page or create one
        if browser.contexts and browser.contexts[0].pages:
            return browser.contexts[0].pages[0]
        return None

    def _random_delay(self, lo: float = 0.5, hi: float = 1.5) -> None:
        """Human-like random delay."""
        time.sleep(random.uniform(lo, hi))

    # ── Legacy CDP helpers (kept for backward compat in tests) ────

    def _find_tab(self, url_fragment: str = "xiaohongshu") -> dict[str, Any] | None:
        """Find a Chrome tab whose URL contains *url_fragment* via HTTP endpoint."""
        try:
            list_url = f"http://localhost:{self._cdp_port}/json/list"
            with urllib.request.urlopen(list_url, timeout=5) as resp:
                tabs = json.loads(resp.read().decode("utf-8"))
            for tab in tabs:
                if url_fragment in tab.get("url", ""):
                    return tab
        except Exception as exc:
            logger.debug("CDP tab discovery failed: %s", exc)
        return None

    def _connect(self, ws_url: str) -> Any:
        """Legacy: create websocket connection (fallback)."""
        try:
            import websocket as ws_mod
        except ImportError:
            raise RuntimeError(
                "websocket-client package required. Install: pip install websocket-client"
            )
        return ws_mod.create_connection(ws_url, timeout=15, suppress_origin=True)

    def _send_cdp(self, ws: Any, method: str, params: dict | None = None,
                  cmd_id: int = 1) -> dict:
        """Legacy: send a CDP command via raw websocket."""
        msg = {"id": cmd_id, "method": method}
        if params:
            msg["params"] = params
        ws.send(json.dumps(msg))
        return json.loads(ws.recv())

    def _js(self, ws: Any, expression: str, cmd_id: int = 1) -> str:
        """Legacy: evaluate JS via raw websocket CDP."""
        result = self._send_cdp(ws, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
        }, cmd_id)
        return result.get("result", {}).get("result", {}).get("value", "")

    # ── Public interface ──────────────────────────────────────────

    def authenticate(self) -> ToolResult:
        """
        Check if user is logged into Xiaohongshu creator center.

        Connects to Chrome via Playwright CDP, navigates to creator URL,
        and checks whether the page redirects to login.
        """
        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_xhs_page(browser)
            if not page:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=(
                        f"No page found in Chrome (port {self._cdp_port}). "
                        "Please open https://www.xiaohongshu.com in Chrome first."
                    ),
                    platform=self.platform,
                )

            page.goto(self.creator_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            current_url = page.url

            if "/login" in current_url:
                self._auth_status = AuthStatus.NOT_AUTHENTICATED
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=(
                        "Not logged into Xiaohongshu creator center. "
                        "Please log in at https://creator.xiaohongshu.com first."
                    ),
                    platform=self.platform,
                )

            self._auth_status = AuthStatus.AUTHENTICATED
            self._auth_checked = True
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"status": "authenticated", "url": current_url},
                platform=self.platform,
            )

        except Exception as e:
            self._auth_status = AuthStatus.ERROR
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Authentication check failed: {e!s}",
                platform=self.platform,
            )
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    pw.stop()
                except Exception:
                    pass

    def publish(self, content: PublishContent) -> PublishResult:
        """
        Publish content to Xiaohongshu via Playwright browser automation.

        Workflow:
        1. Navigate to creator.xiaohongshu.com/publish/publish
        2. Upload images via file chooser
        3. Fill title and content
        4. Add tags
        5. Save as draft (not auto-publish for safety)
        """
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform,
            )

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_xhs_page(browser)
            if not page:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"No page in Chrome (port {self._cdp_port})",
                    platform=self.platform,
                )

            # Step 1: Navigate to publish page
            page.goto(self.creator_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/login" in page.url:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Not logged in. Please log in to creator center first.",
                    platform=self.platform,
                )

            # Step 2: Switch to image-text mode (default is video)
            self._pw_switch_to_image_mode(page)

            # Step 3: Wait for editor
            self._pw_wait_for_editor(page)

            # Step 4: Upload images
            if content.images:
                self._pw_upload_images(page, content.images)

            # Step 5: Fill title
            self._random_delay(0.5, 1.0)
            self._pw_fill_title(page, content.title)

            # Step 6: Fill body
            self._random_delay(0.5, 1.0)
            self._pw_fill_body(page, content.body)

            # Step 7: Add tags
            if content.tags:
                self._random_delay(0.5, 1.0)
                self._pw_add_tags(page, content.tags[:self.max_tags])

            # Step 8: Save as draft
            self._random_delay(1.0, 2.0)
            save_result = self._pw_save_draft(page)

            content_id = f"xhs_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=content_id,
                published_at=datetime.now(),
                status_detail="已保存到草稿箱" if save_result else "已填写内容（请手动保存）",
                data={
                    "title": content.title,
                    "content_type": content.content_type.value,
                    "images_count": len(content.images),
                    "tags": content.tags,
                    "draft_saved": save_result,
                },
            )

        except Exception as e:
            logger.exception("Xiaohongshu publish failed")
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Publishing failed: {e!s}",
                platform=self.platform,
            )
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    pw.stop()
                except Exception:
                    pass

    # ── Playwright automation steps ───────────────────────────────

    def _pw_switch_to_image_mode(self, page: Any) -> None:
        """Switch from default video upload to image-text upload mode."""
        result = page.evaluate("""() => {
            const els = document.querySelectorAll('span, div, a, button');
            for (const el of els) {
                if (el.textContent.trim() === '上传图文' && el.offsetParent !== null) {
                    el.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }""")
        if result == "clicked":
            page.wait_for_timeout(2000)
            logger.info("Switched to image-text upload mode")
        else:
            logger.warning("Image-text tab not found, may already be in image mode")

    def _pw_wait_for_editor(self, page: Any, timeout: int = 15000) -> None:
        """Wait for the publish editor to be ready."""
        try:
            page.wait_for_selector(
                '[class*="upload"], input[type="file"], [placeholder*="标题"]',
                timeout=timeout,
            )
        except Exception:
            logger.warning("Editor did not become ready within %dms", timeout)

    def _pw_upload_images(self, page: Any, image_paths: list[str]) -> None:
        """Upload images via Playwright file chooser."""
        abs_paths = []
        for p in image_paths:
            path = Path(p)
            if not path.is_absolute():
                path = Path.cwd() / path
            if path.exists():
                abs_paths.append(str(path))
            else:
                logger.warning("Image not found: %s", p)

        if not abs_paths:
            logger.warning("No valid image paths to upload")
            return

        # Use Playwright's set_input_files on the file input
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(abs_paths)
            page.wait_for_timeout(3000)
            logger.info("Uploaded %d images via file input", len(abs_paths))
        else:
            # Fallback: use file chooser event
            try:
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    # Click the upload area to trigger file chooser
                    upload_area = page.query_selector('[class*="upload"]')
                    if upload_area:
                        upload_area.click()
                file_chooser = fc_info.value
                file_chooser.set_files(abs_paths)
                page.wait_for_timeout(3000)
                logger.info("Uploaded %d images via file chooser", len(abs_paths))
            except Exception as e:
                logger.warning("Image upload failed: %s", e)

    def _pw_fill_title(self, page: Any, title: str) -> None:
        """Fill the title input field using Playwright."""
        selectors = [
            '[placeholder*="标题"]',
            '[class*="title"] input',
            '[class*="title"] textarea',
        ]
        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                el.fill("")
                # Type character by character for more human-like behavior
                page.keyboard.type(title, delay=50)
                logger.info("Title filled: %s", title[:20])
                return
        # JS fallback - use JSON.stringify for proper escaping
        title_json = json.dumps(title, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('[placeholder*="标题"]')
                || document.querySelector('[class*="title"] input');
            if (el) {{
                el.focus();
                el.value = '';
                // Use JSON.parse + JSON.stringify roundtrip for safe escaping
                var safeText = JSON.parse({title_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Title filled via JS fallback: %s", title[:20])

    def _pw_fill_body(self, page: Any, body: str) -> None:
        """Fill the body/content editor using Playwright."""
        selectors = [
            '[contenteditable="true"]',
            '[class*="editor"]',
            '[class*="content"] [contenteditable]',
        ]
        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                # Clear existing content
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                # Type with slight delay for human-like behavior
                page.keyboard.type(body, delay=20)
                logger.info("Body filled (%d chars)", len(body))
                return
        # JS fallback - use JSON.stringify for proper escaping
        body_json = json.dumps(body, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('[contenteditable="true"]');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                // Use JSON.parse + JSON.stringify roundtrip for safe escaping
                var safeText = JSON.parse({body_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Body filled via JS fallback (%d chars)", len(body))

    def _pw_add_tags(self, page: Any, tags: list[str]) -> None:
        """Add hashtags to the note using Playwright."""
        tag_selectors = [
            '[placeholder*="标签"]',
            '[class*="tag"] input',
            '[id*="tag"] input',
        ]
        for tag in tags:
            for sel in tag_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.keyboard.type(tag, delay=30)
                    self._random_delay(0.3, 0.6)
                    page.keyboard.press("Enter")
                    self._random_delay(0.3, 0.6)
                    break
        logger.info("Added %d tags", len(tags))

    def _pw_save_draft(self, page: Any) -> bool:
        """Click the save-as-draft button using Playwright."""
        # Try text-based button matching (XHS uses "暂存离开" for draft save)
        for text in ["暂存离开", "存草稿", "保存草稿", "保存"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                page.wait_for_timeout(2000)
                logger.info("Draft save button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text.includes('暂存') || text.includes('存草稿') || text.includes('保存')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            page.wait_for_timeout(2000)
            logger.info("Draft save button clicked via JS: %s", result)
            return True

        logger.warning("Draft save button not found")
        return False

    # ── Analytics & scheduling (placeholder) ──────────────────────

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """Get analytics for published content (requires browser automation)."""
        return AnalyticsData(
            content_id=content_id,
            views=0, likes=0, comments=0, shares=0, favorites=0,
            raw_data={"note": "Analytics requires logged-in browser session"},
        )

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """Schedule content for future publishing."""
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED, error=error_msg, platform=self.platform,
            )

        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform,
            )

        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=f"scheduled_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status_detail=f"已预约发布: {publish_time.strftime('%Y-%m-%d %H:%M')}",
            data={"scheduled_for": publish_time.isoformat()},
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
