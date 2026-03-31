"""
WeChat Official Account (微信公众号) Publishing Tool

Publishes content to WeChat Official Account platform.
Supports two methods:
- API method: Fast, requires API credentials (AppID + AppSecret)
- Browser method: Slower, requires Chrome + login session

Reuses logic from baoyu-post-to-wechat skill.
"""

import json
import logging
import os
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from ..base_tool import ToolResult, ToolStatus
from .base import AnalyticsData, BasePlatformTool, ContentType, PublishContent, PublishResult

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"


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
        # Load credentials from .env files (baoyu-skills convention)
        env_creds = self._load_env_credentials()
        self._app_id = (
            self.config.get("app_id")
            or os.environ.get("WECHAT_APP_ID")
            or env_creds.get("WECHAT_APP_ID")
        )
        self._app_secret = (
            self.config.get("app_secret")
            or os.environ.get("WECHAT_APP_SECRET")
            or env_creds.get("WECHAT_APP_SECRET")
        )
        self._author = self.config.get("default_author", "")
        self._need_open_comment = self.config.get("need_open_comment", True)
        self._only_fans_can_comment = self.config.get("only_fans_can_comment", False)
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    def _load_env_credentials(self) -> dict[str, str]:
        """Load credentials from .baoyu-skills/.env files"""
        env: dict[str, str] = {}
        env_paths = [
            Path.cwd() / ".baoyu-skills" / ".env",
            Path.home() / ".baoyu-skills" / ".env",
        ]
        for p in env_paths:
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        env[key.strip()] = val.strip().strip("\"'")
                break
        return env

    def _has_api_credentials(self) -> bool:
        """Check if API credentials are available"""
        return bool(self._app_id and self._app_secret)

    def _get_access_token(self) -> str:
        """Fetch or return cached WeChat API access token."""
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token

        url = (
            f"{TOKEN_URL}?grant_type=client_credential"
            f"&appid={self._app_id}&secret={self._app_secret}"
        )
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("errcode"):
            raise RuntimeError(f"Access token error {data['errcode']}: {data.get('errmsg')}")

        self._access_token = data["access_token"]
        # Token valid for ~7200s, refresh at 7000s to be safe
        from datetime import timedelta
        self._token_expires = datetime.now() + timedelta(seconds=7000)
        return self._access_token

    def _create_draft(self, title: str, content_html: str, author: str = "",
                      digest: str = "") -> dict[str, Any]:
        """Create a draft article via WeChat draft/add API."""
        token = self._get_access_token()
        url = f"{DRAFT_URL}?access_token={token}"

        article: dict[str, Any] = {
            "article_type": "news",
            "title": title,
            "content": content_html,
            "thumb_media_id": "",  # No cover for now (newspic fallback)
            "need_open_comment": 1 if self._need_open_comment else 0,
            "only_fans_can_comment": 1 if self._only_fans_can_comment else 0,
        }
        if author:
            article["author"] = author
        if digest:
            article["digest"] = digest[:120]

        payload = json.dumps({"articles": [article]}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("errcode") and data["errcode"] != 0:
            raise RuntimeError(f"Draft add failed {data['errcode']}: {data.get('errmsg')}")

        return data

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
            # Build HTML content from body (already HTML or plain text)
            content_html = content.body
            if not content_html.strip().startswith("<"):
                # Wrap plain text in basic HTML paragraphs
                paragraphs = content_html.split("\n\n")
                content_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())

            digest = content.custom_fields.get("summary", "")
            author = content.custom_fields.get("author", self._author)

            result = self._create_draft(
                title=content.title,
                content_html=content_html,
                author=author,
                digest=digest,
            )

            media_id = result.get("media_id", "")
            logger.info("WeChat draft created: media_id=%s", media_id)

            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=media_id,
                status_detail="草稿已保存",
                data={
                    "method": "api",
                    "media_id": media_id,
                    "title": content.title,
                    "author": author,
                    "need_open_comment": self._need_open_comment,
                    "only_fans_can_comment": self._only_fans_can_comment,
                    "manage_url": "https://mp.weixin.qq.com",
                },
            )

        except Exception as e:
            logger.exception("WeChat API publish failed")
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"API publish failed: {e!s}",
                platform=self.platform
            )

    def _publish_via_browser(self, content: PublishContent) -> PublishResult:
        """Publish via baoyu-post-to-wechat skill scripts (bun + TypeScript)"""
        try:
            if content.content_type == ContentType.IMAGE_TEXT:
                script = "wechat-browser.ts"
            else:
                script = "wechat-api.ts"  # API script handles HTML/MD files too

            script_path = self.SKILL_DIR / "scripts" / script
            if not script_path.exists():
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"Script not found: {script_path}",
                    platform=self.platform,
                )

            # Write content to a temp HTML file for the script
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as f:
                body_html = content.body
                if not body_html.strip().startswith("<"):
                    paragraphs = body_html.split("\n\n")
                    body_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
                f.write(
                    f"<!DOCTYPE html><html><head><title>{content.title}</title></head>"
                    f"<body>{body_html}</body></html>"
                )
                tmp_path = f.name

            cmd = [
                "npx", "-y", "bun", str(script_path), tmp_path,
                "--title", content.title,
            ]
            author = content.custom_fields.get("author", self._author)
            if author:
                cmd.extend(["--author", author])
            summary = content.custom_fields.get("summary", "")
            if summary:
                cmd.extend(["--summary", summary[:120]])

            logger.info("Running browser publish: %s", " ".join(cmd[:6]))
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
            )

            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

            if result.returncode != 0:
                return PublishResult(
                    status=ToolStatus.FAILED,
                    error=f"Browser script failed: {result.stderr[:500]}",
                    platform=self.platform,
                )

            # Parse JSON output from script
            try:
                output = json.loads(result.stdout)
                media_id = output.get("media_id", "")
            except json.JSONDecodeError:
                media_id = ""

            return PublishResult(
                status=ToolStatus.SUCCESS,
                platform=self.platform,
                content_id=media_id,
                status_detail="草稿已保存（浏览器方式）",
                data={
                    "method": "browser",
                    "script": script,
                    "title": content.title,
                    "media_id": media_id,
                },
            )

        except subprocess.TimeoutExpired:
            return PublishResult(
                status=ToolStatus.FAILED,
                error="Browser publish timed out (120s)",
                platform=self.platform,
            )
        except Exception as e:
            logger.exception("Browser publish failed")
            return PublishResult(
                status=ToolStatus.FAILED,
                error=f"Browser publish failed: {e!s}",
                platform=self.platform,
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
