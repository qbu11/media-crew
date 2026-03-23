"""
发布限流器

防止触发平台风控，控制发布频率
"""

from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any

import aiofiles

logger = logging.getLogger(__name__)


class RateLimiter:
    """发布限流器"""

    # 平台限制配置
    LIMITS: dict[str, dict[str, int]] = {
        "xiaohongshu": {
            "min_interval": 60,      # 最小间隔 60 秒
            "hourly_limit": 3,       # 每小时最多 3 条
            "daily_limit": 10,       # 每日最多 10 条
        },
        "weibo": {
            "min_interval": 60,
            "hourly_limit": 5,
            "daily_limit": 20,
        },
        "zhihu": {
            "min_interval": 60,
            "hourly_limit": 2,
            "daily_limit": 5,
        },
    }

    def __init__(self, storage_dir: str | None = None):
        """
        初始化限流器

        Args:
            storage_dir: 限流记录存储目录
        """
        if storage_dir is None:
            storage_dir = "data/rate_limits"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self.publish_history: defaultdict[str, list[datetime]] = defaultdict(list)

    def _get_history_file(self, platform: str) -> Path:
        """获取历史记录文件路径"""
        return self.storage_dir / f"{platform}_history.json"

    async def load_history(self) -> None:
        """加载历史记录"""
        for platform in self.LIMITS:
            history_file = self._get_history_file(platform)
            if history_file.exists():
                try:
                    async with aiofiles.open(
                        history_file, encoding="utf-8"
                    ) as f:
                        content = await f.read()
                        data = json.loads(content)
                        # 只保留最近 24 小时的记录
                        cutoff = datetime.now() - timedelta(hours=24)
                        self.publish_history[platform] = [
                            datetime.fromisoformat(ts)
                            for ts in data
                            if datetime.fromisoformat(ts) > cutoff
                        ]
                except Exception as e:
                    logger.error(f"加载历史记录失败 {platform}: {e}")

    async def _save_history(self, platform: str) -> None:
        """保存历史记录"""
        try:
            history_file = self._get_history_file(platform)
            timestamps = [
                ts.isoformat() for ts in self.publish_history[platform]
            ]
            async with aiofiles.open(history_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(timestamps, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"保存历史记录失败 {platform}: {e}")

    def check_limit(
        self, platform: str, username: str | None = None
    ) -> dict[str, Any]:
        """
        检查是否可以发布

        Args:
            platform: 平台名称
            username: 用户名（可选，用于多账号管理）

        Returns:
            限流检查结果
        """
        if platform not in self.LIMITS:
            return {
                "allowed": False,
                "reason": f"不支持的平台: {platform}",
                "wait_seconds": 0,
                "limits": {},
            }

        limits = self.LIMITS[platform]
        now = datetime.now()

        # 清理过期记录
        cutoff_24h = now - timedelta(hours=24)
        self.publish_history[platform] = [
            ts for ts in self.publish_history[platform] if ts > cutoff_24h
        ]

        history = self.publish_history[platform]

        # 1. 检查最小间隔
        if history:
            last_publish = max(history)
            elapsed = (now - last_publish).total_seconds()
            min_interval = limits["min_interval"]

            if elapsed < min_interval:
                wait_seconds = int(min_interval - elapsed)
                return {
                    "allowed": False,
                    "reason": f"发布间隔不足，需等待 {wait_seconds} 秒",
                    "wait_seconds": wait_seconds,
                    "limits": limits,
                    "last_publish": last_publish.isoformat(),
                }

        # 2. 检查每小时限制
        cutoff_1h = now - timedelta(hours=1)
        hourly_count = len([ts for ts in history if ts > cutoff_1h])
        hourly_limit = limits["hourly_limit"]

        if hourly_count >= hourly_limit:
            oldest_in_hour = min([ts for ts in history if ts > cutoff_1h])
            wait_seconds = int(
                (oldest_in_hour + timedelta(hours=1) - now).total_seconds()
            )
            return {
                "allowed": False,
                "reason": f"每小时发布数量已达上限 ({hourly_count}/{hourly_limit})",
                "wait_seconds": wait_seconds,
                "limits": limits,
                "hourly_count": hourly_count,
            }

        # 3. 检查每日限制
        daily_count = len([ts for ts in history if ts > cutoff_24h])
        daily_limit = limits["daily_limit"]

        if daily_count >= daily_limit:
            oldest_in_day = min([ts for ts in history if ts > cutoff_24h])
            wait_seconds = int(
                (oldest_in_day + timedelta(hours=24) - now).total_seconds()
            )
            return {
                "allowed": False,
                "reason": f"每日发布数量已达上限 ({daily_count}/{daily_limit})",
                "wait_seconds": wait_seconds,
                "limits": limits,
                "daily_count": daily_count,
            }

        # 通过所有检查
        return {
            "allowed": True,
            "reason": "可以发布",
            "wait_seconds": 0,
            "limits": limits,
            "hourly_count": hourly_count,
            "daily_count": daily_count,
        }

    async def record_publish(
        self, platform: str, username: str | None = None
    ) -> None:
        """
        记录发布

        Args:
            platform: 平台名称
            username: 用户名（可选）
        """
        if platform not in self.LIMITS:
            logger.warning(f"不支持的平台: {platform}")
            return

        now = datetime.now()
        self.publish_history[platform].append(now)
        await self._save_history(platform)

        logger.info(f"记录发布: {platform} at {now.isoformat()}")

    def get_stats(self, platform: str | None = None) -> dict[str, Any]:
        """
        获取发布统计

        Args:
            platform: 平台名称，如果为 None 则返回所有平台

        Returns:
            统计信息
        """
        now = datetime.now()
        cutoff_1h = now - timedelta(hours=1)
        cutoff_24h = now - timedelta(hours=24)

        if platform:
            platforms = [platform] if platform in self.LIMITS else []
        else:
            platforms = list(self.LIMITS.keys())

        stats: dict[str, Any] = {}

        for p in platforms:
            history = self.publish_history[p]
            limits = self.LIMITS[p]

            hourly_count = len([ts for ts in history if ts > cutoff_1h])
            daily_count = len([ts for ts in history if ts > cutoff_24h])

            last_publish = max(history) if history else None
            next_available = None

            if last_publish:
                min_interval = limits["min_interval"]
                next_available = last_publish + timedelta(seconds=min_interval)

            stats[p] = {
                "hourly_count": hourly_count,
                "hourly_limit": limits["hourly_limit"],
                "hourly_remaining": max(0, limits["hourly_limit"] - hourly_count),
                "daily_count": daily_count,
                "daily_limit": limits["daily_limit"],
                "daily_remaining": max(0, limits["daily_limit"] - daily_count),
                "last_publish": (
                    last_publish.isoformat() if last_publish else None
                ),
                "next_available": (
                    next_available.isoformat() if next_available else None
                ),
            }

        return stats

    async def reset(self, platform: str | None = None) -> None:
        """
        重置限流记录（仅用于测试）

        Args:
            platform: 平台名称，如果为 None 则重置所有平台
        """
        if platform:
            self.publish_history[platform] = []
            await self._save_history(platform)
            logger.info(f"已重置限流记录: {platform}")
        else:
            for p in self.LIMITS:
                self.publish_history[p] = []
                await self._save_history(p)
            logger.info("已重置所有平台的限流记录")


# 全局单例
_rate_limiter: RateLimiter | None = None


async def get_rate_limiter() -> RateLimiter:
    """获取限流器单例（首次使用时自动加载历史记录）"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        await _rate_limiter.load_history()
    return _rate_limiter
