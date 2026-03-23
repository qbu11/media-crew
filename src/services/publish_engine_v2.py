"""
发布引擎 V2 - Chrome MCP 集成版

通过 Chrome DevTools MCP 实现多平台自动发布。
"""

import logging
from datetime import datetime
from typing import Any

from src.core.error_handling import Result, success, error

logger = logging.getLogger(__name__)


class ChromeMCPPublisher:
    """Chrome MCP 发布器基类"""

    def __init__(self) -> None:
        self.last_publish_time: dict[str, datetime] = {}

    async def check_rate_limit(
        self, platform: str, min_interval: int = 60
    ) -> tuple[bool, float]:
        """检查发布频率限制"""
        last_time = self.last_publish_time.get(platform)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.warning(
                    "%s 发布间隔不足，需等待 %.0f 秒", platform, wait_time
                )
                return False, wait_time
        return True, 0.0

    def update_publish_time(self, platform: str) -> None:
        """更新发布时间"""
        self.last_publish_time[platform] = datetime.now()


class XiaohongshuPublisher(ChromeMCPPublisher):
    """小红书发布器"""

    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"
    MIN_INTERVAL = 60

    async def publish(
        self,
        title: str,
        body: str,
        images: list[str],
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> Result[dict[str, Any]]:
        """
        发布小红书图文笔记

        Args:
            title: 标题（<=20字）
            body: 正文（<=1000字）
            images: 图片路径列表（1-18张）
            tags: 标签列表（<=10个）
            location: 地点（可选）
        """
        if len(title) > 20:
            return error("标题超过20字", "XHS_TITLE_TOO_LONG")
        if len(body) > 1000:
            return error("正文超过1000字", "XHS_BODY_TOO_LONG")
        if not images or len(images) > 18:
            return error("图片数量必须在1-18张之间", "XHS_INVALID_IMAGE_COUNT")
        if tags and len(tags) > 10:
            return error("标签数量不能超过10个", "XHS_TOO_MANY_TAGS")

        can_publish, wait_time = await self.check_rate_limit(
            "xiaohongshu", self.MIN_INTERVAL
        )
        if not can_publish:
            return error(
                f"发布间隔不足，请等待 {wait_time:.0f} 秒",
                "PUBLISH_RATE_LIMIT",
            )

        try:
            steps = [
                f"1. 导航到发布页面: {self.PUBLISH_URL}",
                "2. 等待页面加载完成",
                "3. 上传图片（逐张上传，模拟人工操作）",
                f"4. 填写标题: {title}",
                f"5. 输入正文: {body[:50]}...",
                f"6. 添加标签: {', '.join(tags or [])}",
                "7. 截图预览，等待用户确认",
                "8. 点击发布按钮",
                "9. 等待发布成功提示",
                "10. 获取发布链接",
            ]

            return success({
                "pending": True,
                "message": "需要通过 Chrome MCP 执行发布",
                "steps": steps,
                "platform": "xiaohongshu",
                "data": {
                    "title": title,
                    "body": body,
                    "images": images,
                    "tags": tags or [],
                    "location": location,
                },
            })

        except Exception as e:
            logger.error("小红书发布失败: %s", e)
            return error(f"发布失败: {e}", "XHS_PUBLISH_ERROR")


class WeiboPublisher(ChromeMCPPublisher):
    """微博发布器"""

    PUBLISH_URL = "https://weibo.com"
    MIN_INTERVAL = 60

    async def publish(
        self,
        body: str,
        images: list[str] | None = None,
    ) -> Result[dict[str, Any]]:
        """
        发布微博

        Args:
            body: 正文（<=2000字）
            images: 图片路径列表（<=9张）
        """
        if len(body) > 2000:
            return error("正文超过2000字", "WEIBO_BODY_TOO_LONG")
        if images and len(images) > 9:
            return error("图片数量不能超过9张", "WEIBO_TOO_MANY_IMAGES")

        can_publish, wait_time = await self.check_rate_limit(
            "weibo", self.MIN_INTERVAL
        )
        if not can_publish:
            return error(
                f"发布间隔不足，请等待 {wait_time:.0f} 秒",
                "PUBLISH_RATE_LIMIT",
            )

        try:
            steps = [
                f"1. 导航到微博首页: {self.PUBLISH_URL}",
                "2. 点击发微博输入框",
                f"3. 输入正文: {body[:50]}...",
                "4. 上传图片（如果有）",
                "5. 截图预览，等待用户确认",
                "6. 点击发送按钮",
                "7. 等待发布成功",
                "8. 获取微博链接",
            ]

            return success({
                "pending": True,
                "message": "需要通过 Chrome MCP 执行发布",
                "steps": steps,
                "platform": "weibo",
                "data": {
                    "body": body,
                    "images": images or [],
                },
            })

        except Exception as e:
            logger.error("微博发布失败: %s", e)
            return error(f"发布失败: {e}", "WEIBO_PUBLISH_ERROR")


class ZhihuPublisher(ChromeMCPPublisher):
    """知乎发布器"""

    ARTICLE_URL = "https://zhuanlan.zhihu.com/write"
    ANSWER_URL = "https://www.zhihu.com"
    MIN_INTERVAL = 60

    async def publish_article(
        self,
        title: str,
        body: str,
        tags: list[str] | None = None,
    ) -> Result[dict[str, Any]]:
        """
        发布知乎文章

        Args:
            title: 标题
            body: 正文（支持 Markdown）
            tags: 标签列表
        """
        can_publish, wait_time = await self.check_rate_limit(
            "zhihu", self.MIN_INTERVAL
        )
        if not can_publish:
            return error(
                f"发布间隔不足，请等待 {wait_time:.0f} 秒",
                "PUBLISH_RATE_LIMIT",
            )

        try:
            steps = [
                f"1. 导航到文章编辑页: {self.ARTICLE_URL}",
                "2. 等待编辑器加载",
                f"3. 填写标题: {title}",
                f"4. 输入正文: {body[:50]}...",
                "5. 添加话题标签",
                "6. 截图预览，等待用户确认",
                "7. 点击发布按钮",
                "8. 等待发布成功",
                "9. 获取文章链接",
            ]

            return success({
                "pending": True,
                "message": "需要通过 Chrome MCP 执行发布",
                "steps": steps,
                "platform": "zhihu",
                "content_type": "article",
                "data": {
                    "title": title,
                    "body": body,
                    "tags": tags or [],
                },
            })

        except Exception as e:
            logger.error("知乎文章发布失败: %s", e)
            return error(f"发布失败: {e}", "ZHIHU_PUBLISH_ERROR")


class PublishEngineV2:
    """统一发布引擎 V2"""

    def __init__(self) -> None:
        self.xiaohongshu = XiaohongshuPublisher()
        self.weibo = WeiboPublisher()
        self.zhihu = ZhihuPublisher()

        self.PLATFORMS: dict[str, dict[str, Any]] = {
            "xiaohongshu": {
                "name": "小红书",
                "publisher": self.xiaohongshu,
                "content_types": ["post", "video"],
            },
            "weibo": {
                "name": "微博",
                "publisher": self.weibo,
                "content_types": ["post", "article"],
            },
            "zhihu": {
                "name": "知乎",
                "publisher": self.zhihu,
                "content_types": ["answer", "article", "idea"],
            },
        }

    async def publish(
        self,
        platform: str,
        account: dict[str, Any] | None,
        content: dict[str, Any],
    ) -> Result[dict[str, Any]]:
        """
        统一发布接口

        Args:
            platform: 平台名称（xiaohongshu/weibo/zhihu）
            account: 账号信息（可选，使用当前登录账号）
            content: 内容信息
        """
        if platform not in self.PLATFORMS:
            return error(
                f"不支持的平台: {platform}",
                "UNSUPPORTED_PLATFORM",
            )

        publisher = self.PLATFORMS[platform]["publisher"]

        try:
            if platform == "xiaohongshu":
                return await publisher.publish(
                    title=content.get("title", ""),
                    body=content["body"],
                    images=content.get("images", []),
                    tags=content.get("tags", []),
                    location=content.get("location"),
                )

            elif platform == "weibo":
                return await publisher.publish(
                    body=content["body"],
                    images=content.get("images", []),
                )

            elif platform == "zhihu":
                content_type = content.get("content_type", "article")
                if content_type == "article":
                    return await publisher.publish_article(
                        title=content.get("title", ""),
                        body=content["body"],
                        tags=content.get("tags", []),
                    )
                else:
                    return error(
                        f"不支持的内容类型: {content_type}",
                        "UNSUPPORTED_CONTENT_TYPE",
                    )

            return error(
                f"Publisher not implemented for {platform}",
                "NOT_IMPLEMENTED",
            )

        except Exception as e:
            logger.error("发布失败 [%s]: %s", platform, e)
            return error(f"发布失败: {e}", "PUBLISH_ERROR")


_publish_engine: PublishEngineV2 | None = None


def get_publish_engine_v2() -> PublishEngineV2:
    """获取发布引擎单例"""
    global _publish_engine
    if _publish_engine is None:
        _publish_engine = PublishEngineV2()
    return _publish_engine
