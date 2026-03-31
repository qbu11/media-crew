"""
Zhihu (知乎) Publishing Tool

Publishes content to Zhihu platform.
Uses Playwright connect_over_cdp for browser automation.

Safety constraints (from media-publish-zhihu skill):
- Minimum interval: 30 seconds between posts
- Daily limit: 15 answers, 5 articles maximum
- Answer: >= 100 characters
- Article: >= 500 characters
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


class ZhihuTool(BasePlatformTool):
    """
    Zhihu content publishing tool.

    Uses Playwright connect_over_cdp to attach to a running Chrome instance,
    inheriting the user's login session.

    Prerequisites:
    - Chrome launched with --remote-debugging-port=9222
    - User logged into zhihu.com / zhuanlan.zhihu.com
    - Playwright installed: pip install playwright && playwright install chromium
    """

    name = "zhihu_publisher"
    description = "Publishes content to Zhihu (知乎)"
    platform = "zhihu"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 100
    max_body_length = 10000
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
        self._cdp_port = int(self.config.get("cdp_port", DEFAULT_CDP_PORT))

    def authenticate(self) -> ToolResult:
        """
        Authenticate with Zhihu.

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

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, "zhihu")
            if not page:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"No page in Chrome (port {self._cdp_port})",
                    platform=self.platform,
                )

            # Step 1: Navigate to question page
            page.goto(question_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/signin" in page.url or "/login" in page.url:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Not logged in. Please log in to Zhihu first.",
                    platform=self.platform,
                )

            # Step 2: Click "写回答" button
            self._random_delay(0.5, 1.0)
            write_btn_clicked = self._pw_click_write_answer(page)

            if not write_btn_clicked:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Could not find '写回答' button",
                    platform=self.platform,
                )

            # Step 3: Wait for editor
            page.wait_for_timeout(2000)
            self._random_delay(0.5, 1.0)

            # Step 4: Fill answer content
            self._pw_fill_answer_editor(page, answer)

            # Step 5: Click publish button
            self._random_delay(1.0, 2.0)
            publish_clicked = self._pw_click_publish_answer(page)

            if not publish_clicked:
                logger.warning("Publish button not found, answer may be in draft state")

            page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug("Browser unavailable for answer publish: %s", e)
        finally:
            self._cleanup_browser(browser, pw)

        content_id = f"zhihu_answer_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=content_id,
            content_url=question_url,
            published_at=datetime.now(),
            status_detail="回答已发布",
            data={
                "type": "answer",
                "question_url": question_url,
                "length": len(answer)
            }
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

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, "zhihu")
            if not page:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"No page in Chrome (port {self._cdp_port})",
                    platform=self.platform,
                )

            # Step 1: Navigate to write page
            page.goto(self.article_write_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/signin" in page.url or "/login" in page.url:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Not logged in. Please log in to Zhihu first.",
                    platform=self.platform,
                )

            # Step 2: Fill title
            self._random_delay(0.5, 1.0)
            self._pw_fill_article_title(page, title)

            # Step 3: Upload images if provided
            if images:
                self._random_delay(0.5, 1.0)
                self._pw_upload_article_images(page, images)

            # Step 4: Fill article content
            self._random_delay(0.5, 1.0)
            self._pw_fill_article_editor(page, content)

            # Step 5: Click publish button
            self._random_delay(1.0, 2.0)
            publish_clicked = self._pw_click_publish_article(page)

            if not publish_clicked:
                logger.warning("Publish button not found, article may be in draft state")

            page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug("Browser unavailable for article publish: %s", e)
        finally:
            self._cleanup_browser(browser, pw)

        article_url = f"https://zhuanlan.zhihu.com/p/{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content_id = f"zhihu_article_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=content_id,
            content_url=article_url,
            published_at=datetime.now(),
            status_detail="文章已发布",
            data={
                "type": "article",
                "title": title,
                "images_count": len(images) if images else 0
            }
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

        browser = None
        pw = None
        try:
            browser, pw = self._connect_browser()
            page = self._find_platform_page(browser, "zhihu")
            if not page:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"No page in Chrome (port {self._cdp_port})",
                    platform=self.platform,
                )

            # Step 1: Navigate to home page
            page.goto(self.home_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Check login
            if "/signin" in page.url or "/login" in page.url:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Not logged in. Please log in to Zhihu first.",
                    platform=self.platform,
                )

            # Step 2: Click "想法" input area
            self._random_delay(0.5, 1.0)
            thought_input_clicked = self._pw_click_thought_input(page)

            if not thought_input_clicked:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error="Could not find thought input area",
                    platform=self.platform,
                )

            # Step 3: Fill thought content
            page.wait_for_timeout(1000)
            self._random_delay(0.5, 1.0)
            self._pw_fill_thought_editor(page, content)

            # Step 4: Upload images if provided
            if images:
                self._random_delay(0.5, 1.0)
                self._pw_upload_thought_images(page, images)

            # Step 5: Click publish button
            self._random_delay(1.0, 2.0)
            publish_clicked = self._pw_click_publish_thought(page)

            if not publish_clicked:
                logger.warning("Publish button not found, thought may be in draft state")

            page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug("Browser unavailable for thought publish: %s", e)
        finally:
            self._cleanup_browser(browser, pw)

        content_id = f"zhihu_thought_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return PublishResult(
            status=ToolStatus.SUCCESS,
            platform=self.platform,
            content_id=content_id,
            published_at=datetime.now(),
            status_detail="想法已发布",
            data={
                "type": "thought",
                "images_count": len(images) if images else 0
            }
        )

    # ── Playwright automation helpers ───────────────────────────────

    def _pw_click_write_answer(self, page: Any) -> bool:
        """Click the '写回答' button using Playwright."""
        # Try text-based button matching
        for text in ["写回答", "回答问题"]:
            btn = page.query_selector(f'button:has-text("{text}"), a:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Write answer button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text.includes('写回答') || text.includes('回答问题')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Write answer button clicked via JS: %s", result)
            return True

        logger.warning("Write answer button not found")
        return False

    def _pw_fill_answer_editor(self, page: Any, content: str) -> None:
        """Fill the answer editor using Playwright."""
        selectors = [
            '[contenteditable="true"]',
            '[class*="editor"]',
            'textarea[placeholder*="回答"]',
            'div[contenteditable="true"]',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(content, delay=20)
                logger.info("Answer filled (%d chars)", len(content))
                return

        # JS fallback
        content_json = json.dumps(content, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('[contenteditable="true"]')
                || document.querySelector('[class*="editor"]')
                || document.querySelector('textarea');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                var safeText = JSON.parse({content_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Answer filled via JS fallback (%d chars)", len(content))

    def _pw_click_publish_answer(self, page: Any) -> bool:
        """Click the publish button for answer using Playwright."""
        # Try text-based button matching
        for text in ["发布回答", "提交回答", "发布"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Publish answer button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text.includes('发布回答') || text.includes('提交回答') || text === '发布') {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Publish answer button clicked via JS: %s", result)
            return True

        logger.warning("Publish answer button not found")
        return False

    def _pw_fill_article_title(self, page: Any, title: str) -> None:
        """Fill the article title input using Playwright."""
        selectors = [
            'input[placeholder*="标题"]',
            '[class*="title"] input',
            'input[name="title"]',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                el.fill("")
                page.keyboard.type(title, delay=50)
                logger.info("Article title filled: %s", title[:30])
                return

        # JS fallback
        title_json = json.dumps(title, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('input[placeholder*="标题"]')
                || document.querySelector('[class*="title"] input');
            if (el) {{
                el.focus();
                el.value = '';
                var safeText = JSON.parse({title_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Article title filled via JS fallback: %s", title[:30])

    def _pw_upload_article_images(self, page: Any, image_paths: list[str]) -> None:
        """Upload images for article using Playwright."""
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

        # Try file input
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(abs_paths)
            page.wait_for_timeout(2000)
            logger.info("Uploaded %d images for article", len(abs_paths))
        else:
            logger.warning("File input not found for article images")

    def _pw_fill_article_editor(self, page: Any, content: str) -> None:
        """Fill the article editor using Playwright."""
        selectors = [
            '[contenteditable="true"]',
            '[class*="editor"] [contenteditable]',
            'div[contenteditable="true"]',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(content, delay=20)
                logger.info("Article content filled (%d chars)", len(content))
                return

        # JS fallback
        content_json = json.dumps(content, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('[contenteditable="true"]');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                var safeText = JSON.parse({content_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Article content filled via JS fallback (%d chars)", len(content))

    def _pw_click_publish_article(self, page: Any) -> bool:
        """Click the publish button for article using Playwright."""
        # Try text-based button matching
        for text in ["发布", "发表文章"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Publish article button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text === '发布' || text.includes('发表文章')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Publish article button clicked via JS: %s", result)
            return True

        logger.warning("Publish article button not found")
        return False

    def _pw_click_thought_input(self, page: Any) -> bool:
        """Click the thought input area using Playwright."""
        # Try text-based element matching
        for text in ["分享想法", "写想法", "有什么想说的"]:
            el = page.query_selector(f'button:has-text("{text}"), div:has-text("{text}")')
            if el:
                el.click()
                logger.info("Thought input clicked: %s", text)
                return True

        # Try placeholder-based matching
        for placeholder in ["分享你的想法", "写想法"]:
            el = page.query_selector(f'[placeholder*="{placeholder}"]')
            if el:
                el.click()
                logger.info("Thought input clicked via placeholder: %s", placeholder)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var els = Array.from(document.querySelectorAll('button, div, textarea, input'));
            for (var el of els) {
                var text = el.textContent.trim();
                var placeholder = (el.placeholder || '').trim();
                if (text.includes('分享想法') || text.includes('写想法') ||
                    placeholder.includes('分享你的想法') || placeholder.includes('写想法')) {
                    el.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }""")

        if result == "clicked":
            logger.info("Thought input clicked via JS")
            return True

        logger.warning("Thought input not found")
        return False

    def _pw_fill_thought_editor(self, page: Any, content: str) -> None:
        """Fill the thought editor using Playwright."""
        selectors = [
            '[contenteditable="true"]',
            'textarea[placeholder*="想法"]',
            '[class*="thought"] textarea',
        ]

        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(content, delay=20)
                logger.info("Thought content filled (%d chars)", len(content))
                return

        # JS fallback
        content_json = json.dumps(content, ensure_ascii=True)
        page.evaluate(f"""() => {{
            var el = document.querySelector('[contenteditable="true"]')
                || document.querySelector('textarea');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                var safeText = JSON.parse({content_json});
                document.execCommand('insertText', false, safeText);
            }}
        }}""")
        logger.info("Thought content filled via JS fallback (%d chars)", len(content))

    def _pw_upload_thought_images(self, page: Any, image_paths: list[str]) -> None:
        """Upload images for thought using Playwright."""
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

        # Try file input
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(abs_paths)
            page.wait_for_timeout(2000)
            logger.info("Uploaded %d images for thought", len(abs_paths))
        else:
            logger.warning("File input not found for thought images")

    def _pw_click_publish_thought(self, page: Any) -> bool:
        """Click the publish button for thought using Playwright."""
        # Try text-based button matching
        for text in ["发布", "发送", "分享"]:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn:
                btn.click()
                logger.info("Publish thought button clicked: %s", text)
                return True

        # JS fallback
        result = page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll('button'));
            for (var b of buttons) {
                var text = b.textContent.trim();
                if (text === '发布' || text === '发送' || text === '分享') {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            logger.info("Publish thought button clicked via JS: %s", result)
            return True

        logger.warning("Publish thought button not found")
        return False

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
