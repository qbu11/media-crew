"""Research tools for WeChat article search and scraping.

This module provides optional integrations with wechat-search-skill
and wechat-article-spider for content research capabilities.
"""

from typing import Any


class WeChatSearchTool:
    """Wrapper for wechat-search-skill."""

    def __init__(self) -> None:
        self._tool = None
        try:
            from skills.wechat_search.scripts.search import WeChatSearcher
            self._tool = WeChatSearcher()
        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if the tool is available."""
        return self._tool is not None

    def search(
        self,
        keyword: str,
        pages: int = 3,
        days: int | None = None,
        with_content: bool = False,
    ) -> Any:
        """Search WeChat articles by keyword."""
        if not self._tool:
            raise RuntimeError("wechat-search-skill not installed")
        return self._tool.search(keyword, pages=pages, days=days, with_content=with_content)


class WeChatArticleSpider:
    """Wrapper for wechat-article-spider."""

    def __init__(self) -> None:
        self._spider = None
        try:
            from wechat_spider import WeChatSpider
            self._spider = WeChatSpider()
        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if the spider is available."""
        return self._spider is not None

    def check_login_status(self) -> dict[str, Any]:
        """Check if logged in to WeChat."""
        if not self._spider:
            return {"logged_in": False, "error": "wechat-article-spider not installed"}
        return self._spider.check_login()

    def search_account(self, keyword: str) -> list[Any]:
        """Search for WeChat accounts."""
        if not self._spider:
            raise RuntimeError("wechat-article-spider not installed")
        return self._spider.search_accounts(keyword)

    def scrape_account(
        self,
        account: str,
        pages: int = 5,
        days: int | None = None,
        with_content: bool = False,
    ) -> Any:
        """Scrape articles from an account."""
        if not self._spider:
            raise RuntimeError("wechat-article-spider not installed")
        return self._spider.scrape(account, pages=pages, days=days, with_content=with_content)

    def batch_scrape(
        self,
        accounts: list[str],
        pages: int = 3,
        days: int | None = None,
        with_content: bool = False,
    ) -> dict[str, Any]:
        """Scrape multiple accounts."""
        if not self._spider:
            raise RuntimeError("wechat-article-spider not installed")
        return self._spider.batch_scrape(accounts, pages=pages, days=days, with_content=with_content)


__all__ = ["WeChatArticleSpider", "WeChatSearchTool"]
