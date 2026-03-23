"""
数据采集引擎

使用 HTTP 抓取和 HTML 解析采集各平台数据指标。
改写为异步，使用 MetricsService 存储数据。
"""

import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.error_handling import Result, success, error
from src.models.metrics import Metrics
from src.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


# ========== 平台特定的数据提取器 ==========


class PlatformMetricsExtractor:
    """平台指标提取器基类"""

    @staticmethod
    def extract_number(text: str) -> int:
        """从文本中提取数字，支持 '1.2万' 这样的格式"""
        if not text:
            return 0

        text = text.strip().replace(",", "")

        if "万" in text:
            match = re.search(r"([\d.]+)万", text)
            if match:
                return int(float(match.group(1)) * 10000)

        if "w" in text.lower():
            match = re.search(r"([\d.]+)w", text.lower())
            if match:
                return int(float(match.group(1)) * 10000)

        if "k" in text.lower():
            match = re.search(r"([\d.]+)k", text.lower())
            if match:
                return int(float(match.group(1)) * 1000)

        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0


class XiaohongshuExtractor(PlatformMetricsExtractor):
    """小红书数据提取器"""

    LIKES_PATTERNS = [
        r"点赞\s*([\d.]+[万wWkK]?)",
        r"([\d.]+[万wWkK]?)\s*点赞",
    ]
    COMMENTS_PATTERNS = [
        r"评论\s*([\d.]+[万wWkK]?)",
        r"([\d.]+[万wWkK]?)\s*评论",
    ]
    SHARES_PATTERNS = [
        r"收藏\s*([\d.]+[万wWkK]?)",
        r"([\d.]+[万wWkK]?)\s*收藏",
    ]

    @classmethod
    def extract_from_html(cls, html: str) -> dict[str, int]:
        """从 HTML 中提取数据"""
        result: dict[str, int] = {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "collected": 0,
        }

        for pattern in cls.LIKES_PATTERNS:
            matches = re.findall(pattern, html)
            if matches:
                result["likes"] = cls.extract_number(matches[0])
                break

        for pattern in cls.COMMENTS_PATTERNS:
            matches = re.findall(pattern, html)
            if matches:
                result["comments"] = cls.extract_number(matches[0])
                break

        for pattern in cls.SHARES_PATTERNS:
            matches = re.findall(pattern, html)
            if matches:
                result["shares"] = cls.extract_number(matches[0])
                result["collected"] = result["shares"]
                break

        json_match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html
        )
        if json_match:
            try:
                json.loads(json_match.group(1))
                logger.debug("Found INITIAL_STATE data")
            except (json.JSONDecodeError, KeyError):
                pass

        return result


class WeiboExtractor(PlatformMetricsExtractor):
    """微博数据提取器"""

    @classmethod
    def extract_from_html(cls, html: str) -> dict[str, int]:
        """从 HTML 中提取数据"""
        result: dict[str, int] = {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
        }

        views_match = re.search(r"阅读\s*([\d.]+[万kK]?)", html)
        if views_match:
            result["views"] = cls.extract_number(views_match.group(1))

        likes_match = re.search(r"赞\s*\((\d+)\)", html)
        if likes_match:
            result["likes"] = int(likes_match.group(1))

        comments_match = re.search(r"评论\s*\((\d+)\)", html)
        if comments_match:
            result["comments"] = int(comments_match.group(1))

        shares_match = re.search(r"转发\s*\((\d+)\)", html)
        if shares_match:
            result["shares"] = int(shares_match.group(1))

        return result


class ZhihuExtractor(PlatformMetricsExtractor):
    """知乎数据提取器"""

    @classmethod
    def extract_from_html(cls, html: str) -> dict[str, int]:
        """从 HTML 中提取数据"""
        result: dict[str, int] = {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
        }

        views_match = re.search(r'"viewCount":\s*(\d+)', html)
        if views_match:
            result["views"] = int(views_match.group(1))

        likes_match = re.search(r'"voteupCount":\s*(\d+)', html)
        if likes_match:
            result["likes"] = int(likes_match.group(1))

        comments_match = re.search(r'"commentCount":\s*(\d+)', html)
        if comments_match:
            result["comments"] = int(comments_match.group(1))

        return result


# ========== 异步 HTTP 客户端 ==========


class AsyncHTTPClient:
    """异步 HTTP 客户端封装"""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    async def get_page_html(self, url: str) -> str:
        """异步获取页面 HTML"""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException:
            logger.warning("页面获取超时: %s", url)
            return ""
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP 错误 %d: %s", e.response.status_code, url)
            return ""
        except Exception as e:
            logger.warning("页面获取失败: %s - %s", url, e)
            return ""


# ========== 数据采集引擎 ==========


class DataCollector:
    """异步数据采集引擎"""

    def __init__(self, db_url: str | None = None) -> None:
        self.http_client = AsyncHTTPClient()
        self.extractors: dict[str, type[PlatformMetricsExtractor]] = {
            "xiaohongshu": XiaohongshuExtractor,
            "weibo": WeiboExtractor,
            "zhihu": ZhihuExtractor,
        }
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_async_engine(self.db_url)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def collect_metrics(
        self, platform: str, post_url: str
    ) -> Result[dict[str, Any]]:
        """
        采集单个内容的数据指标

        Args:
            platform: 平台名称
            post_url: 内容链接
        """
        if platform not in self.extractors:
            return error(
                f"不支持的平台: {platform}",
                "UNSUPPORTED_PLATFORM",
            )

        html = await self.http_client.get_page_html(post_url)
        if not html:
            return error(
                f"{platform}数据采集失败：无法获取页面内容",
                "PAGE_FETCH_FAILED",
            )

        extractor = self.extractors[platform]
        metrics = extractor.extract_from_html(html)
        metrics["collected_at"] = datetime.now().isoformat()

        return success(metrics)

    async def collect_and_save(
        self,
        platform: str,
        post_url: str,
        content_id: str | None = None,
    ) -> Result[Metrics]:
        """采集数据并保存到数据库"""
        metrics_result = await self.collect_metrics(platform, post_url)
        if not metrics_result.success:
            return error(
                metrics_result.error or "采集失败",
                metrics_result.error_code or "COLLECT_ERROR",
            )

        raw_metrics = metrics_result.data

        async with self.SessionLocal() as session:
            metrics_service = MetricsService(session)
            return await metrics_service.record_metric(
                platform=platform,
                post_url=post_url,
                content_id=content_id,
                views=raw_metrics.get("views"),
                likes=raw_metrics.get("likes"),
                comments=raw_metrics.get("comments"),
                shares=raw_metrics.get("shares"),
                raw_metrics=raw_metrics,
            )

    async def batch_collect(
        self, contents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        批量采集数据

        Args:
            contents: 内容列表，每个包含 {"id": str, "platform": str, "publish_url": str}
        """
        results: list[dict[str, Any]] = []
        for content in contents:
            if not content.get("publish_url"):
                continue

            try:
                result = await self.collect_and_save(
                    platform=content["platform"],
                    post_url=content["publish_url"],
                    content_id=content.get("id"),
                )

                results.append({
                    "content_id": content.get("id"),
                    "platform": content["platform"],
                    "success": result.success,
                    "data": result.data if result.success else None,
                    "error": result.error if not result.success else None,
                })
            except Exception as e:
                logger.error("采集失败 %s: %s", content.get("id"), e)
                results.append({
                    "content_id": content.get("id"),
                    "platform": content["platform"],
                    "success": False,
                    "error": str(e),
                })

        return results


# ========== 数据分析工具 ==========


def analyze_content_performance(
    metrics_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    分析内容表现

    Args:
        metrics_history: 历史数据列表
    """
    if not metrics_history:
        return {"error": "No data"}

    if len(metrics_history) >= 2:
        latest = metrics_history[-1]
        previous = metrics_history[-2]

        likes_growth = (
            (latest["likes"] - previous["likes"])
            / max(previous["likes"], 1)
            * 100
        )
        views_growth = (
            (latest.get("views", 0) - previous.get("views", 0))
            / max(previous.get("views", 1), 1)
            * 100
        )

        return {
            "latest_likes": latest["likes"],
            "latest_views": latest.get("views", 0),
            "likes_growth_rate": round(likes_growth, 2),
            "views_growth_rate": round(views_growth, 2),
            "is_trending": likes_growth > 50 or views_growth > 50,
        }

    latest = metrics_history[-1]
    return {
        "latest_likes": latest["likes"],
        "latest_views": latest.get("views", 0),
        "likes_growth_rate": 0,
        "views_growth_rate": 0,
        "is_trending": False,
    }


_data_collector: DataCollector | None = None


def get_data_collector() -> DataCollector:
    """获取数据采集器单例"""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector
