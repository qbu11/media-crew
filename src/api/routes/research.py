"""Research API routes - WeChat search and spider."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/research", tags=["Research"])


class KeywordSearchRequest(BaseModel):
    """Request for keyword-based article search."""

    keyword: str
    pages: int = 3
    days: int | None = None
    with_content: bool = False


class AccountScrapeRequest(BaseModel):
    """Request for account-based article scraping."""

    account: str
    pages: int = 5
    days: int | None = None
    with_content: bool = False


class BatchScrapeRequest(BaseModel):
    """Request for batch account scraping."""

    accounts: list[str]
    pages: int = 3
    days: int | None = None
    with_content: bool = False


@router.get("/status")
async def get_research_status() -> dict[str, Any]:
    """Check availability of research tools."""
    from src.tools.research import WeChatArticleSpider, WeChatSearchTool

    search_tool = WeChatSearchTool()
    spider = WeChatArticleSpider()

    return {
        "wechat_search": {
            "available": search_tool.is_available(),
            "description": "Search WeChat articles by keyword (Sougou-based)",
        },
        "wechat_spider": {
            "available": spider.is_available(),
            "login_status": spider.check_login_status() if spider.is_available() else None,
            "description": "Scrape articles from specific WeChat accounts (login required)",
        },
    }


@router.post("/wechat/search")
async def search_wechat_articles(request: KeywordSearchRequest) -> dict[str, Any]:
    """Search WeChat articles by keyword."""
    from src.tools.research import WeChatSearchTool

    tool = WeChatSearchTool()

    if not tool.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "wechat-search-skill not installed. "
                "Run: git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search && "
                "pip install -r ~/.claude/skills/wechat-search/scripts/requirements.txt"
            ),
        )

    try:
        result = tool.search(
            keyword=request.keyword,
            pages=request.pages,
            days=request.days,
            with_content=request.with_content,
        )
        return {
            "success": True,
            "keyword": result.keyword,
            "total": result.total,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "author": r.author,
                    "account_id": r.account_id,
                    "publish_time": r.publish_time,
                    "summary": r.summary,
                    "content": r.content[:500] if r.content else "",  # Truncate for API
                }
                for r in result.results
            ],
            "searched_at": result.searched_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/wechat/accounts")
async def search_wechat_accounts(keyword: str) -> dict[str, Any]:
    """Search for WeChat Official Accounts."""
    from src.tools.research import WeChatArticleSpider

    spider = WeChatArticleSpider()

    if not spider.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "wechat-article-spider not installed. "
                "Run: pip install git+https://github.com/qbu11/wechat-article-spider.git"
            ),
        )

    try:
        accounts = spider.search_account(keyword)
        return {
            "success": True,
            "keyword": keyword,
            "total": len(accounts),
            "accounts": [
                {
                    "name": a.name,
                    "fakeid": a.fakeid,
                    "alias": a.alias,
                    "description": a.description[:200] if a.description else "",
                }
                for a in accounts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/wechat/scrape")
async def scrape_wechat_account(request: AccountScrapeRequest) -> dict[str, Any]:
    """Scrape articles from a WeChat Official Account."""
    from src.tools.research import WeChatArticleSpider

    spider = WeChatArticleSpider()

    if not spider.is_available():
        raise HTTPException(
            status_code=503,
            detail="wechat-article-spider not installed",
        )

    # Check login
    login_status = spider.check_login_status()
    if not login_status.get("logged_in"):
        raise HTTPException(
            status_code=401,
            detail="Not logged in to WeChat. Run: wechat-spider login",
        )

    try:
        result = spider.scrape_account(
            account=request.account,
            pages=request.pages,
            days=request.days,
            with_content=request.with_content,
        )
        return {
            "success": True,
            "account": {
                "name": result.account.name if result.account else request.account,
                "fakeid": result.account.fakeid if result.account else None,
            },
            "total": result.total,
            "articles": [
                {
                    "title": a.title,
                    "url": a.url,
                    "publish_time": a.publish_time,
                    "summary": a.summary,
                    "content": a.content[:1000] if a.content else "",  # Truncate
                    "read_count": a.read_count,
                    "like_count": a.like_count,
                }
                for a in result.articles
            ],
            "scraped_at": result.scraped_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/wechat/batch")
async def batch_scrape_accounts(request: BatchScrapeRequest) -> dict[str, Any]:
    """Scrape articles from multiple WeChat accounts."""
    from src.tools.research import WeChatArticleSpider

    spider = WeChatArticleSpider()

    if not spider.is_available():
        raise HTTPException(
            status_code=503,
            detail="wechat-article-spider not installed",
        )

    login_status = spider.check_login_status()
    if not login_status.get("logged_in"):
        raise HTTPException(
            status_code=401,
            detail="Not logged in to WeChat",
        )

    try:
        results = spider.batch_scrape(
            accounts=request.accounts,
            pages=request.pages,
            days=request.days,
            with_content=request.with_content,
        )
        return {
            "success": True,
            "accounts": {
                name: {
                    "total": resp.total,
                    "articles": [
                        {"title": a.title, "url": a.url, "publish_time": a.publish_time}
                        for a in resp.articles[:10]  # Limit per account
                    ],
                }
                for name, resp in results.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
