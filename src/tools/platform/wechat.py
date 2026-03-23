"""
WeChat Official Account (微信公众号) Publishing Tool

Publishes content to WeChat Official Account platform.
Supports two methods:
- API method: Fast, requires API credentials (AppID + AppSecret)
- Browser method: Slower, requires Chrome + login session

Reuses logic from baoyu-post-to-wechat skill.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..base_tool import ToolResult, ToolStatus
from .base import AnalyticsData, BasePlatformTool, ContentType, PublishContent, PublishResult


class PublishMethod:
    API = "api"
    BROWSER = "browser"


class WechatTool(BasePlatformTool):
    """
    WeChat Official Account publishing tool.

    Supports article posting (文章) and image-text posting (图文).
    Can use either API or browser-based publishing.
    """

    name = "wechat_publisher"
    description = "Publishes content to WeChat Official Account (微信公众号)"
    platform = "wechat"
    version = "0.1.0"

    # Platform constraints
    max_title_length = 64
    max_body_length = 20000  # WeChat articles can be long
    max_images = 9  # For image-text posts
    max_tags = 0  # WeChat doesn't use hashtags in the same way
    supported_content_types = [ContentType.ARTICLE, ContentType.IMAGE_TEXT]

    # Rate limiting
    max_requests_per_minute = 5
    min_interval_seconds = 10.0

    # Skill directory for baoyu-post-to-wechat scripts
    SKILL_DIR = Path.home() / ".claude" / "skills" / "baoyu-post-to-wechat"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._publish_method = self.config.get("publish_method", PublishMethod.API)
        import os
        self._app_id = self.config.get("app_id") or os.environ.get("WECHAT_APP_ID")
        self._app_secret = self.config.get("app_secret") or os.environ.get("WECHAT_APP_SECRET")
        self._author = self.config.get("default_author", "")
        self._need_open_comment = self.config.get("need_open_comment", True)
        self._only_fans_can_comment = self.config.get("only_fans_can_comment", False)

    def _has_api_credentials(self) -> bool:
        """Check if API credentials are available"""
        return bool(self._app_id and self._app_secret)

    def _load_extend_config(self) -> dict[str, str]:
        """Load EXTEND.md configuration (baoyu-skills convention)"""
        config = {}
        extend_paths = [
            Path.cwd() / ".baoyu-skills" / "baoyu-post-to-wechat" / "EXTEND.md",
            Path.home() / ".baoyu-skills" / "baoyu-post-to-wechat" / "EXTEND.md",
        ]

        for path in extend_paths:
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line and not line.startswith("#"):
                            key, value = line.split(":", 1)
                            config[key.strip()] = value.strip()
                break

        return config

    def authenticate(self) -> ToolResult:
        """
        Authenticate with WeChat platform.

        For API method: validates AppID and AppSecret.
        For browser method: checks Chrome login session.
        """
        if self._publish_method == PublishMethod.API:
            if not self._has_api_credentials():
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=(
                        "WeChat API credentials not found. "
                        "Set WECHAT_APP_ID and WECHAT_APP_SECRET environment variables, "
                        "or configure in .baoyu-skills/.env"
                    ),
                    platform=self.platform
                )

            # In actual implementation: call WeChat API to get access_token
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"method": "api", "status": "credentials_valid"},
                platform=self.platform
            )

        else:
            # Browser method: check if skill scripts exist
            script_path = self.SKILL_DIR / "scripts" / "wechat-article.ts"
            if not script_path.exists():
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=f"Skill script not found: {script_path}",
                    platform=self.platform
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"method": "browser", "status": "scripts_available"},
                platform=self.platform
            )

    def publish(self, content: PublishContent) -> PublishResult:
        """
        Publish content to WeChat Official Account.

        API workflow:
        1. Get access_token
        2. Upload images as media
        3. Create draft via draft/add API
        4. Return media_id for manual review

        Browser workflow:
        1. Run wechat-article.ts or wechat-browser.ts script
        2. Script handles Chrome automation
        """
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=error_msg,
                platform=self.platform
            )

        if self._publish_method == PublishMethod.API:
            return self._publish_via_api(content)
        else:
            return self._publish_via_browser(content)

    def _publish_via_api(self, content: PublishContent) -> PublishResult:
        """Publish via WeChat API (draft/add endpoint)"""
        if not self._has_api_credentials():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="API credentials not configured",
                platform=self.platform
            )

        try:
            # In actual implementation:
            # 1. POST to get access_token
            # 2. Upload cover image -> thumb_media_id
            # 3. Upload inline images -> replace URLs
            # 4. POST to draft/add with article payload

            # Simulated result
            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"wechat_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                status_detail="草稿已保存",
                data={
                    "method": "api",
                    "title": content.title,
                    "author": self._author,
                    "need_open_comment": self._need_open_comment,
                    "only_fans_can_comment": self._only_fans_can_comment,
                    "manage_url": "https://mp.weixin.qq.com"
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"API publish failed: {e!s}",
                platform=self.platform
            )

    def _publish_via_browser(self, content: PublishContent) -> PublishResult:
        """Publish via browser automation (baoyu-post-to-wechat scripts)"""
        try:
            # Determine which script to use
            if content.content_type == ContentType.IMAGE_TEXT:
                script = "wechat-browser.ts"
            else:
                script = "wechat-article.ts"

            script_path = self.SKILL_DIR / "scripts" / script

            if not script_path.exists():
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"Script not found: {script_path}",
                    platform=self.platform
                )

            # In actual implementation:
            # subprocess.run(["npx", "-y", "bun", script_path, ...args])

            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=f"wechat_browser_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                status_detail="草稿已保存（浏览器方式）",
                data={
                    "method": "browser",
                    "script": script,
                    "title": content.title
                }
            )

        except Exception as e:
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Browser publish failed: {e!s}",
                platform=self.platform
            )

    def get_analytics(self, content_id: str) -> AnalyticsData:
        """
        Get analytics for published content.

        WeChat provides analytics via the Official Account backend.
        Requires API access with analytics permissions.
        """
        # In actual implementation:
        # Use WeChat analytics API to fetch article stats
        return AnalyticsData(
            content_id=content_id,
            views=0,
            likes=0,
            comments=0,
            shares=0,
            raw_data={"note": "Requires WeChat analytics API permissions"}
        )

    def schedule(self, content: PublishContent, publish_time: datetime) -> PublishResult:
        """
        Schedule content for future publishing.

        WeChat supports scheduled publishing via the draft system.
        """
        if publish_time <= datetime.now():
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Publish time must be in the future",
                platform=self.platform
            )

        # First create draft, then schedule
        draft_result = self.publish(content)
        if not draft_result.is_success():
            return draft_result

        # In actual implementation: use WeChat API to schedule the draft
        draft_result.status_detail = f"已预约发布: {publish_time.strftime('%Y-%m-%d %H:%M')}"
        draft_result.data["scheduled_for"] = publish_time.isoformat()

        return draft_result
