"""
WeChat Article Spider - Scrape articles from specific WeChat Official Accounts

Based on: https://github.com/qbu11/wechat-article-spider
Uses WeChat Platform API with login credentials.
"""

from datetime import datetime
import json
import shutil
import subprocess
from typing import Any

from pydantic import BaseModel


class WeChatArticle(BaseModel):
    """Single WeChat article."""

    title: str
    url: str
    author: str  # 公众号名称
    publish_time: str
    summary: str = ""
    content: str = ""
    cover_image: str = ""
    read_count: int = 0
    like_count: int = 0


class WeChatAccount(BaseModel):
    """WeChat Official Account info."""

    name: str
    fakeid: str  # WeChat internal ID
    alias: str = ""  # 公众号微信号
    description: str = ""
    avatar: str = ""


class WeChatSpiderResponse(BaseModel):
    """Spider response."""

    account: WeChatAccount | None
    articles: list[WeChatArticle]
    total: int
    scraped_at: datetime


class WeChatArticleSpider:
    """
    WeChat article spider for scraping articles from specific accounts.

    Prerequisites:
    - Install the wechat-article-spider:
      ```bash
      pip install git+https://github.com/qbu11/wechat-article-spider.git
      ```
    - Login first: `wechat-spider login`
    """

    name = "wechat_spider"
    description = "Scrape articles from specific WeChat Official Accounts"

    def __init__(self):
        """Initialize the spider."""
        self.cli_path = self._find_cli()

    def _find_cli(self) -> str | None:
        """Find the wechat-spider CLI."""
        return shutil.which("wechat-spider")

    def is_available(self) -> bool:
        """Check if the CLI is installed."""
        return self.cli_path is not None

    def check_login_status(self) -> dict[str, Any]:
        """Check if logged in to WeChat."""
        if not self.is_available():
            return {"logged_in": False, "error": "wechat-spider not installed"}

        result = subprocess.run(
            [self.cli_path, "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            return {"logged_in": False, "error": result.stderr}

        try:
            data = json.loads(result.stdout)
            return {"logged_in": data.get("logged_in", False), "data": data}
        except json.JSONDecodeError:
            return {"logged_in": False, "error": "Failed to parse response"}

    def search_account(self, keyword: str) -> list[WeChatAccount]:
        """
        Search for WeChat Official Accounts.

        Args:
            keyword: Account name or keyword to search

        Returns:
            List of matching accounts
        """
        if not self.is_available():
            raise RuntimeError(
                "wechat-article-spider not installed. "
                "Run: pip install git+https://github.com/qbu11/wechat-article-spider.git"
            )

        result = subprocess.run(
            [self.cli_path, "search", keyword],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(f"Search failed: {result.stderr}")

        try:
            data = json.loads(result.stdout)
            accounts = []
            for item in data.get("accounts", []):
                accounts.append(WeChatAccount(
                    name=item.get("nickname", item.get("name", "")),
                    fakeid=item.get("fakeid", ""),
                    alias=item.get("alias", ""),
                    description=item.get("description", ""),
                    avatar=item.get("avatar", ""),
                ))
            return accounts
        except json.JSONDecodeError:
            return []

    def scrape_account(
        self,
        account: str,
        pages: int = 5,
        days: int | None = None,
        with_content: bool = False,
    ) -> WeChatSpiderResponse:
        """
        Scrape articles from a WeChat Official Account.

        Args:
            account: Account name or fakeid
            pages: Number of pages to scrape (default 5)
            days: Only include articles from last N days (optional)
            with_content: Fetch full article content (slower)

        Returns:
            WeChatSpiderResponse with articles
        """
        if not self.is_available():
            raise RuntimeError(
                "wechat-article-spider not installed. "
                "Run: pip install git+https://github.com/qbu11/wechat-article-spider.git"
            )

        # Build command
        cmd = [
            self.cli_path, "scrape", account,
            "--pages", str(pages),
        ]

        if days:
            cmd.extend(["--days", str(days)])

        if with_content:
            cmd.append("--content")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(f"Scrape failed: {result.stderr}")

        # Parse output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {"articles": []}

        articles = []
        for item in data.get("articles", []):
            articles.append(WeChatArticle(
                title=item.get("title", ""),
                url=item.get("url", item.get("link", "")),
                author=item.get("author", item.get("account_name", "")),
                publish_time=item.get("create_time", item.get("publish_time", "")),
                summary=item.get("digest", item.get("summary", "")),
                content=item.get("content", ""),
                cover_image=item.get("cover", item.get("cover_image", "")),
                read_count=item.get("read_num", 0),
                like_count=item.get("like_num", 0),
            ))

        account_info = None
        if data.get("account"):
            acc = data["account"]
            account_info = WeChatAccount(
                name=acc.get("nickname", acc.get("name", "")),
                fakeid=acc.get("fakeid", ""),
                alias=acc.get("alias", ""),
                description=acc.get("description", ""),
                avatar=acc.get("avatar", ""),
            )

        return WeChatSpiderResponse(
            account=account_info,
            articles=articles,
            total=len(articles),
            scraped_at=datetime.now(),
        )

    def batch_scrape(
        self,
        accounts: list[str],
        pages: int = 3,
        days: int | None = None,
        with_content: bool = False,
        output_dir: str | None = None,
    ) -> dict[str, WeChatSpiderResponse]:
        """
        Scrape articles from multiple accounts.

        Args:
            accounts: List of account names or fakeids
            pages: Number of pages per account
            days: Only include articles from last N days
            with_content: Fetch full article content
            output_dir: Directory to save results

        Returns:
            Dict mapping account name to response
        """
        if not self.is_available():
            raise RuntimeError("wechat-article-spider not installed")

        cmd = [
            self.cli_path, "batch", ",".join(accounts),
            "--pages", str(pages),
        ]

        if days:
            cmd.extend(["--days", str(days)])

        if with_content:
            cmd.append("--content")

        if output_dir:
            cmd.extend(["--output-dir", output_dir])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(f"Batch scrape failed: {result.stderr}")

        # Parse output
        responses = {}
        try:
            data = json.loads(result.stdout)
            for account_name, account_data in data.items():
                articles = [
                    WeChatArticle(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        author=item.get("author", ""),
                        publish_time=item.get("publish_time", ""),
                        summary=item.get("summary", ""),
                        content=item.get("content", ""),
                    )
                    for item in account_data.get("articles", [])
                ]
                responses[account_name] = WeChatSpiderResponse(
                    account=None,
                    articles=articles,
                    total=len(articles),
                    scraped_at=datetime.now(),
                )
        except json.JSONDecodeError:
            pass

        return responses


# Convenience functions
def search_wechat_accounts(keyword: str) -> list[WeChatAccount]:
    """Search for WeChat Official Accounts."""
    spider = WeChatArticleSpider()
    return spider.search_account(keyword)


def scrape_wechat_account(
    account: str,
    pages: int = 5,
    days: int | None = None,
    with_content: bool = False,
) -> WeChatSpiderResponse:
    """Scrape articles from a WeChat Official Account."""
    spider = WeChatArticleSpider()
    return spider.scrape_account(account, pages=pages, days=days, with_content=with_content)
