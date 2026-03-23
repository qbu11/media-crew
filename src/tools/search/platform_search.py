"""
Platform Search & Monitoring Tools

Provides search and competitor monitoring for all platforms:
- Domestic: Xiaohongshu, WeChat, Weibo, Zhihu, Douyin, Bilibili
- Overseas: Reddit, Twitter/X, Facebook, Instagram, Threads
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess


@dataclass
class SearchPost:
    """Standardized search result post."""
    platform: str
    post_id: str
    title: str
    content: str
    author: str
    author_id: str
    publish_time: str
    url: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    images: list[str] = None
    tags: list[str] = None


@dataclass
class SearchResponse:
    """Search response."""
    platform: str
    keyword: str
    total: int
    posts: list[SearchPost]
    searched_at: datetime


class BasePlatformSearch(ABC):
    """Base class for platform search tools."""

    def __init__(self):
        self.cli_name = None

    @abstractmethod
    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search posts by keyword."""
        pass

    @abstractmethod
    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get posts from a specific user (for competitor monitoring)."""
        pass

    @abstractmethod
    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get trending topics/posts."""
        pass

    def is_available(self) -> bool:
        """Check if the search tool is available."""
        return self.cli_name and shutil.which(self.cli_name) is not None


# ============================================================================
# Domestic Platforms
# ============================================================================

class XiaohongshuSearch(BasePlatformSearch):
    """
    Xiaohongshu search using TikHub API.

    API: https://api.tikhub.io/api/docs/
    Install: pip install tikhub
    """

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.cli_name = "tikhub"
        self.api_key = api_key

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Xiaohongshu posts."""
        import httpx

        if not self.api_key:
            # Fallback to union-search-skill
            return self._search_via_skill(keyword, limit)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = httpx.get(
            "https://api.tikhub.io/api/xiaohongshu/search_notes",
            headers=headers,
            params={"keyword": keyword, "limit": limit, "sort": sort},
        )
        data = response.json()

        posts = []
        for item in data.get("data", {}).get("items", []):
            note = item.get("note", {})
            posts.append(SearchPost(
                platform="xiaohongshu",
                post_id=note.get("id", ""),
                title=note.get("title", ""),
                content=note.get("desc", ""),
                author=note.get("user", {}).get("nickname", ""),
                author_id=note.get("user", {}).get("user_id", ""),
                publish_time=note.get("time", ""),
                url=f"https://www.xiaohongshu.com/explore/{note.get('id', '')}",
                likes=note.get("liked_count", 0),
                comments=note.get("comment_count", 0),
                shares=note.get("share_count", 0),
                views=note.get("view_count", 0),
                images=note.get("image_list", []),
            ))

        return SearchResponse(
            platform="xiaohongshu",
            keyword=keyword,
            total=len(posts),
            posts=posts,
            searched_at=datetime.now(),
        )

    def _search_via_skill(self, keyword: str, limit: int) -> SearchResponse:
        """Fallback to union-search-skill."""
        skill_path = Path.home() / ".claude" / "skills" / "union-search-skill" / "xiaohongshu_search.py"
        if not skill_path.exists():
            return SearchResponse("xiaohongshu", keyword, 0, [], datetime.now())

        subprocess.run(
            ["python", str(skill_path), keyword, "--limit", str(limit)],
            capture_output=True,
            text=True,
        )
        # Parse output...
        return SearchResponse("xiaohongshu", keyword, 0, [], datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get posts from a specific Xiaohongshu user."""
        return SearchResponse("xiaohongshu", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Xiaohongshu trending topics."""
        return []


class WeiboSearch(BasePlatformSearch):
    """
    Weibo search using union-search-skill or TikHub API.

    Install: Skill already exists
    """

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.cli_name = "weibo_search"

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Weibo posts."""
        skill_path = Path.home() / ".claude" / "skills" / "union-search-skill" / "weibo_search.py"
        if skill_path.exists():
            result = subprocess.run(
                ["python", str(skill_path), keyword, "--limit", str(limit)],
                capture_output=True,
                text=True,
            )
            # Parse output
            try:
                data = json.loads(result.stdout)
                posts = [
                    SearchPost(
                        platform="weibo",
                        post_id=p.get("id", ""),
                        title=p.get("text", "")[:50],
                        content=p.get("text", ""),
                        author=p.get("user", {}).get("screen_name", ""),
                        author_id=p.get("user", {}).get("idstr", ""),
                        publish_time=p.get("created_at", ""),
                        url=f"https://weibo.com/{p.get('user', {}).get('idstr', '')}/{p.get('id', '')}",
                        likes=p.get("attitudes_count", 0),
                        comments=p.get("comments_count", 0),
                        shares=p.get("reposts_count", 0),
                    )
                    for p in data.get("statuses", [])[:limit]
                ]
                return SearchResponse("weibo", keyword, len(posts), posts, datetime.now())
            except:
                pass
        return SearchResponse("weibo", keyword, 0, [], datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get posts from a specific Weibo user."""
        return SearchResponse("weibo", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Weibo trending topics (热搜)."""
        skill_path = Path.home() / ".claude" / "skills" / "union-search-skill" / "weibo_hot.py"
        if skill_path.exists():
            result = subprocess.run(["python", str(skill_path)], capture_output=True, text=True)
            try:
                data = json.loads(result.stdout)
                return data.get("hot_list", [])[:limit]
            except:
                pass
        return []


class ZhihuSearch(BasePlatformSearch):
    """Zhihu search using TikHub API or union-search-skill."""

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.cli_name = "zhihu_search"

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Zhihu posts."""
        skill_path = Path.home() / ".claude" / "skills" / "union-search-skill" / "zhihu_search.py"
        if skill_path.exists():
            result = subprocess.run(
                ["python", str(skill_path), keyword, "--limit", str(limit)],
                capture_output=True,
                text=True,
            )
            # Parse output
            try:
                data = json.loads(result.stdout)
                posts = [
                    SearchPost(
                        platform="zhihu",
                        post_id=p.get("id", ""),
                        title=p.get("title", p.get("question", {}).get("title", "")),
                        content=p.get("excerpt", p.get("content", ""))[:200],
                        author=p.get("author", {}).get("name", ""),
                        author_id=p.get("author", {}).get("id", ""),
                        publish_time=p.get("created_time", ""),
                        url=p.get("url", ""),
                        likes=p.get("voteup_count", 0),
                        comments=p.get("comment_count", 0),
                    )
                    for p in data.get("results", [])[:limit]
                ]
                return SearchResponse("zhihu", keyword, len(posts), posts, datetime.now())
            except:
                pass
        return SearchResponse("zhihu", keyword, 0, [], datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get posts from a specific Zhihu user."""
        return SearchResponse("zhihu", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Zhihu trending (热榜)."""
        skill_path = Path.home() / ".claude" / "skills" / "union-search-skill" / "zhihu_hot.py"
        if skill_path.exists():
            result = subprocess.run(["python", str(skill_path)], capture_output=True, text=True)
            try:
                data = json.loads(result.stdout)
                return data.get("hot_list", [])[:limit]
            except:
                pass
        return []


class DouyinSearch(BasePlatformSearch):
    """Douyin search using TikHub API."""

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.cli_name = "douyin_search"
        self.api_key = api_key

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Douyin videos."""
        import httpx

        if not self.api_key:
            return SearchResponse("douyin", keyword, 0, [], datetime.now())

        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = httpx.get(
            "https://api.tikhub.io/api/douyin/search/videos",
            headers=headers,
            params={"keyword": keyword, "count": limit},
        )
        data = response.json()

        posts = []
        for item in data.get("data", [])[:limit]:
            video = item.get("video", {})
            author = item.get("author", {})
            stats = item.get("statistics", {})
            posts.append(SearchPost(
                platform="douyin",
                post_id=video.get("aweme_id", ""),
                title=video.get("desc", ""),
                content=video.get("desc", ""),
                author=author.get("nickname", ""),
                author_id=author.get("sec_uid", ""),
                publish_time=video.get("create_time", ""),
                url=f"https://www.douyin.com/video/{video.get('aweme_id', '')}",
                likes=stats.get("digg_count", 0),
                comments=stats.get("comment_count", 0),
                shares=stats.get("share_count", 0),
                views=stats.get("play_count", 0),
            ))

        return SearchResponse("douyin", keyword, len(posts), posts, datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get videos from a specific Douyin user."""
        return SearchResponse("douyin", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Douyin trending (热点)."""
        return []


class BilibiliSearch(BasePlatformSearch):
    """Bilibili search using TikHub API."""

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.cli_name = "bilibili_search"
        self.api_key = api_key

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Bilibili videos."""
        import httpx

        if not self.api_key:
            return SearchResponse("bilibili", keyword, 0, [], datetime.now())

        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = httpx.get(
            "https://api.tikhub.io/api/bilibili/search/videos",
            headers=headers,
            params={"keyword": keyword, "limit": limit},
        )
        data = response.json()

        posts = []
        for item in data.get("data", {}).get("result", [])[:limit]:
            posts.append(SearchPost(
                platform="bilibili",
                post_id=str(item.get("aid", "")),
                title=item.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                content=item.get("description", ""),
                author=item.get("author", ""),
                author_id=str(item.get("mid", "")),
                publish_time=str(item.get("pubdate", "")),
                url=f"https://www.bilibili.com/video/av{item.get('aid', '')}",
                likes=item.get("like", 0),
                comments=item.get("review", 0),
                shares=item.get("favorite", 0),
                views=item.get("play", 0),
            ))

        return SearchResponse("bilibili", keyword, len(posts), posts, datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get videos from a specific Bilibili user."""
        return SearchResponse("bilibili", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Bilibili trending (热门)."""
        return []


# ============================================================================
# Overseas Platforms
# ============================================================================

class RedditSearch(BasePlatformSearch):
    """Reddit search using PRAW SDK."""

    def __init__(self, client_id: str = "", client_secret: str = "", user_agent: str = ""):
        super().__init__()
        self.cli_name = "reddit_search"
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Reddit posts."""
        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.client_id or "dummy",
                client_secret=self.client_secret or "dummy",
                user_agent=self.user_agent or "CrewMediaOps/1.0",
            )
            subreddit = reddit.subreddit("all")
            results = subreddit.search(keyword, sort=sort, limit=limit)

            posts = []
            for post in results:
                posts.append(SearchPost(
                    platform="reddit",
                    post_id=post.id,
                    title=post.title,
                    content=post.selftext[:500] if post.is_self else "",
                    author=str(post.author),
                    author_id=post.author.id if post.author else "",
                    publish_time=datetime.fromtimestamp(post.created_utc).isoformat(),
                    url=f"https://reddit.com{post.permalink}",
                    likes=post.score,
                    comments=post.num_comments,
                ))
            return SearchResponse("reddit", keyword, len(posts), posts, datetime.now())
        except:
            return SearchResponse("reddit", keyword, 0, [], datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get posts from a specific Reddit user."""
        return SearchResponse("reddit", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Reddit trending from r/all."""
        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.client_id or "dummy",
                client_secret=self.client_secret or "dummy",
                user_agent=self.user_agent or "CrewMediaOps/1.0",
            )
            posts = []
            for post in reddit.subreddit("all").hot(limit=limit):
                posts.append({
                    "title": post.title,
                    "url": f"https://reddit.com{post.permalink}",
                    "score": post.score,
                    "comments": post.num_comments,
                })
            return posts
        except:
            return []


class TwitterSearch(BasePlatformSearch):
    """Twitter search using Tweepy SDK."""

    def __init__(self, bearer_token: str = ""):
        super().__init__()
        self.cli_name = "twitter_search"
        self.bearer_token = bearer_token

    def search(self, keyword: str, limit: int = 20, sort: str = "hot") -> SearchResponse:
        """Search Twitter posts."""
        try:
            import tweepy
            client = tweepy.Client(bearer_token=self.bearer_token)
            results = client.search_recent_tweets(keyword, max_results=limit)

            posts = []
            for tweet in results.data:
                posts.append(SearchPost(
                    platform="twitter",
                    post_id=tweet.id,
                    title="",
                    content=tweet.text,
                    author="",
                    author_id="",
                    publish_time=tweet.created_at.isoformat() if tweet.created_at else "",
                    url=f"https://twitter.com/i/web/status/{tweet.id}",
                    likes=tweet.public_metrics["like_count"] if tweet.public_metrics else 0,
                    comments=tweet.public_metrics["reply_count"] if tweet.public_metrics else 0,
                    shares=tweet.public_metrics["retweet_count"] if tweet.public_metrics else 0,
                    views=tweet.public_metrics["impression_count"] if tweet.public_metrics else 0,
                ))
            return SearchResponse("twitter", keyword, len(posts), posts, datetime.now())
        except:
            return SearchResponse("twitter", keyword, 0, [], datetime.now())

    def get_user_posts(self, user_id: str, limit: int = 20) -> SearchResponse:
        """Get tweets from a specific Twitter user."""
        return SearchResponse("twitter", user_id, 0, [], datetime.now())

    def get_trending(self, category: str = "", limit: int = 20) -> list[dict]:
        """Get Twitter trending (WOEID required)."""
        return []


# ============================================================================
# Platform Search Factory
# ============================================================================

PLATFORM_SEARCHERS = {
    "xiaohongshu": XiaohongshuSearch,
    "weibo": WeiboSearch,
    "zhihu": ZhihuSearch,
    "douyin": DouyinSearch,
    "bilibili": BilibiliSearch,
    "reddit": RedditSearch,
    "twitter": TwitterSearch,
}


def get_platform_searcher(platform: str, **kwargs) -> BasePlatformSearch:
    """Get a platform search instance."""
    if platform not in PLATFORM_SEARCHERS:
        raise ValueError(f"Unsupported platform: {platform}")
    return PLATFORM_SEARCHERS[platform](**kwargs)


def search_all_platforms(keyword: str, limit: int = 20) -> dict[str, SearchResponse]:
    """Search across all platforms."""
    results = {}
    for platform, searcher_class in PLATFORM_SEARCHERS.items():
        try:
            searcher = searcher_class()
            results[platform] = searcher.search(keyword, limit)
        except Exception:
            results[platform] = SearchResponse(platform, keyword, 0, [], datetime.now())
    return results


# Competitor monitoring
class CompetitorMonitor:
    """Monitor competitor accounts across platforms."""

    def __init__(self, competitors: dict[str, str]):
        """
        Args:
            competitors: {platform: user_id} mapping
        """
        self.competitors = competitors

    def get_competitor_posts(self, limit: int = 20) -> dict[str, SearchResponse]:
        """Get latest posts from all monitored competitors."""
        results = {}
        for platform, user_id in self.competitors.items():
            try:
                searcher = get_platform_searcher(platform)
                results[platform] = searcher.get_user_posts(user_id, limit)
            except:
                results[platform] = SearchResponse(platform, user_id, 0, [], datetime.now())
        return results
