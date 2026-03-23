"""
发布重试管理器

基于 ORIG 已有的 tenacity 重试基础设施，
提供面向发布任务的高级重试逻辑。
"""

import asyncio
import logging
from typing import Any, Callable

from src.core.error_handling import retry_on_transient

logger = logging.getLogger(__name__)


class PublishRetryManager:
    """发布任务重试管理器"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def publish_with_retry(
        self,
        publish_func: Callable[..., Any],
        content_id: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        带重试的发布操作

        Args:
            publish_func: 发布函数
            content_id: 内容 ID
            **kwargs: 传递给发布函数的参数

        Returns:
            {"success": bool, "url": str, "attempts": int, "error": str}
        """
        last_error: str | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"发布内容 {content_id}, 第 {attempt}/{self.max_retries} 次尝试"
                )

                result = await publish_func(**kwargs)

                if result.get("success"):
                    return {
                        "success": True,
                        "url": result.get("url", ""),
                        "attempts": attempt,
                    }

                # 发布函数返回失败
                last_error = result.get("error", "未知错误")

                if attempt < self.max_retries:
                    delay = self.base_delay * (2.0 ** attempt)
                    delay = min(delay, 60.0)
                    logger.warning(f"发布失败: {last_error}, {delay:.1f}秒后重试...")
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = str(e)
                logger.error(f"发布异常: {e}")

                if attempt < self.max_retries:
                    delay = self.base_delay * (2.0 ** attempt)
                    delay = min(delay, 60.0)
                    await asyncio.sleep(delay)

        return {
            "success": False,
            "error": last_error or "发布失败",
            "attempts": self.max_retries,
        }


# 全局单例
_publish_retry_manager: PublishRetryManager | None = None


def get_publish_retry_manager() -> PublishRetryManager:
    """获取发布重试管理器单例"""
    global _publish_retry_manager
    if _publish_retry_manager is None:
        _publish_retry_manager = PublishRetryManager()
    return _publish_retry_manager
