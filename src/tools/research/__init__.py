"""
Research Tools for TopicResearcher Agent

Provides tools for:
- Hot search / trending topics
- WeChat article search (keyword-based)
- WeChat account spider (account-based)
"""

from .wechat_search import (
    WeChatSearchResponse,
    WeChatSearchResult,
    WeChatSearchTool,
    search_wechat_articles,
)
from .wechat_spider import WeChatAccount, WeChatArticle, WeChatArticleSpider, WeChatSpiderResponse

__all__ = [
    "WeChatAccount",
    "WeChatArticle",
    # WeChat Spider (account-based)
    "WeChatArticleSpider",
    "WeChatSearchResponse",
    "WeChatSearchResult",
    # WeChat Search (keyword-based)
    "WeChatSearchTool",
    "WeChatSpiderResponse",
    "search_wechat_articles",
]
