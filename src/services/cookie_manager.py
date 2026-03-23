"""
Cookie 管理模块

负责管理多平台账号的 Cookie 持久化和登录态检测
"""

import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

import aiofiles

from src.core.config import settings
from src.core.error_handling import Result, success, error
from src.core.exceptions import CrewException

logger = logging.getLogger(__name__)


class CookieManagerException(CrewException):
    """Cookie 管理器异常"""


class CookieManager:
    """Cookie 管理器"""

    # 各平台的关键 Cookie 名称
    PLATFORM_KEY_COOKIES = {
        "xiaohongshu": ["web_session", "xsecappid", "a1", "webId"],
        "weibo": ["SUB", "SUBP", "ALF"],
        "zhihu": ["z_c0", "d_c0", "q_c1"],
        "bilibili": ["SESSDATA", "bili_jct", "DedeUserID"],
        "douyin": ["sessionid", "sessionid_ss", "sid_guard"],
    }

    # 各平台的登录 URL
    PLATFORM_LOGIN_URLS = {
        "xiaohongshu": "https://creator.xiaohongshu.com/login",
        "weibo": "https://weibo.com/login.php",
        "zhihu": "https://www.zhihu.com/signin",
        "bilibili": "https://passport.bilibili.com/login",
        "douyin": "https://creator.douyin.com/",
    }

    # 各平台的验证 URL
    PLATFORM_VERIFY_URLS = {
        "xiaohongshu": "https://creator.xiaohongshu.com",
        "weibo": "https://weibo.com",
        "zhihu": "https://www.zhihu.com",
        "bilibili": "https://www.bilibili.com",
        "douyin": "https://creator.douyin.com",
    }

    def __init__(self, storage_dir: str | None = None):
        """
        初始化 Cookie 管理器

        Args:
            storage_dir: Cookie 存储目录，默认为 data/cookies
        """
        if storage_dir is None:
            storage_dir = "data/cookies"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 确保 .gitignore 存在
        gitignore = self.storage_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.json\n!.gitignore\n")

    def _get_cookie_file(self, platform: str, username: str) -> Path:
        """获取 Cookie 文件路径"""
        filename = f"{platform}_{username}.json"
        return self.storage_dir / filename

    async def save_cookies(
        self,
        platform: str,
        username: str,
        cookies: list[dict[str, Any]],
        expires_days: int = 30,
    ) -> Result[bool]:
        """
        保存 Cookie

        Args:
            platform: 平台名称（xiaohongshu/weibo/zhihu）
            username: 用户名
            cookies: Cookie 列表
            expires_days: 过期天数，默认 30 天

        Returns:
            Result[bool]: 是否保存成功
        """
        try:
            cookie_file = self._get_cookie_file(platform, username)

            cookie_data = {
                "platform": platform,
                "username": username,
                "cookies": cookies,
                "created_at": datetime.now().isoformat(),
                "expires_at": (
                    datetime.now() + timedelta(days=expires_days)
                ).isoformat(),
                "last_used": datetime.now().isoformat(),
            }

            async with aiofiles.open(cookie_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(cookie_data, ensure_ascii=False, indent=2))

            logger.info(f"Cookie 已保存: {platform}/{username}")
            return success(True)

        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")
            return error(f"保存 Cookie 失败: {e}", "COOKIE_SAVE_ERROR")

    async def load_cookies(
        self, platform: str, username: str
    ) -> Result[list[dict[str, Any]]]:
        """
        加载 Cookie

        Args:
            platform: 平台名称
            username: 用户名

        Returns:
            Result[list]: Cookie 列表，如果不存在或已过期则返回错误
        """
        try:
            cookie_file = self._get_cookie_file(platform, username)

            if not cookie_file.exists():
                logger.warning(f"Cookie 文件不存在: {platform}/{username}")
                return error("Cookie 文件不存在", "COOKIE_NOT_FOUND")

            async with aiofiles.open(cookie_file, "r", encoding="utf-8") as f:
                content = await f.read()
                cookie_data = json.loads(content)

            # 检查是否过期
            expires_at = datetime.fromisoformat(cookie_data["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"Cookie 已过期: {platform}/{username}")
                return error("Cookie 已过期", "COOKIE_EXPIRED")

            # 更新最后使用时间
            cookie_data["last_used"] = datetime.now().isoformat()
            async with aiofiles.open(cookie_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(cookie_data, ensure_ascii=False, indent=2))

            logger.info(f"Cookie 已加载: {platform}/{username}")
            return success(cookie_data["cookies"])

        except Exception as e:
            logger.error(f"加载 Cookie 失败: {e}")
            return error(f"加载 Cookie 失败: {e}", "COOKIE_LOAD_ERROR")

    async def delete_cookies(self, platform: str, username: str) -> Result[bool]:
        """
        删除 Cookie

        Args:
            platform: 平台名称
            username: 用户名

        Returns:
            Result[bool]: 是否删除成功
        """
        try:
            cookie_file = self._get_cookie_file(platform, username)

            if cookie_file.exists():
                cookie_file.unlink()
                logger.info(f"Cookie 已删除: {platform}/{username}")
                return success(True)
            else:
                logger.warning(f"Cookie 文件不存在: {platform}/{username}")
                return error("Cookie 文件不存在", "COOKIE_NOT_FOUND")

        except Exception as e:
            logger.error(f"删除 Cookie 失败: {e}")
            return error(f"删除 Cookie 失败: {e}", "COOKIE_DELETE_ERROR")

    async def list_cookies(
        self, platform: str | None = None
    ) -> Result[list[dict[str, Any]]]:
        """
        列出所有 Cookie

        Args:
            platform: 平台名称，如果为 None 则列出所有平台

        Returns:
            Result[list]: Cookie 信息列表
        """
        cookies = []

        try:
            pattern = f"{platform}_*.json" if platform else "*.json"

            for cookie_file in self.storage_dir.glob(pattern):
                try:
                    async with aiofiles.open(cookie_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        cookie_data = json.loads(content)

                    # 检查是否过期
                    expires_at = datetime.fromisoformat(cookie_data["expires_at"])
                    is_expired = datetime.now() > expires_at

                    cookies.append(
                        {
                            "platform": cookie_data["platform"],
                            "username": cookie_data["username"],
                            "created_at": cookie_data["created_at"],
                            "expires_at": cookie_data["expires_at"],
                            "last_used": cookie_data.get("last_used"),
                            "is_expired": is_expired,
                        }
                    )

                except Exception as e:
                    logger.error(f"读取 Cookie 文件失败 {cookie_file}: {e}")
                    continue

            return success(cookies)

        except Exception as e:
            logger.error(f"列出 Cookie 失败: {e}")
            return error(f"列出 Cookie 失败: {e}", "COOKIE_LIST_ERROR")

    async def cleanup_expired(self) -> Result[int]:
        """
        清理过期的 Cookie

        Returns:
            Result[int]: 清理的 Cookie 数量
        """
        count = 0

        try:
            for cookie_file in self.storage_dir.glob("*.json"):
                try:
                    async with aiofiles.open(cookie_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        cookie_data = json.loads(content)

                    expires_at = datetime.fromisoformat(cookie_data["expires_at"])
                    if datetime.now() > expires_at:
                        cookie_file.unlink()
                        count += 1
                        logger.info(
                            f"已清理过期 Cookie: {cookie_data['platform']}/{cookie_data['username']}"
                        )

                except Exception as e:
                    logger.error(f"清理 Cookie 失败 {cookie_file}: {e}")
                    continue

            logger.info(f"共清理 {count} 个过期 Cookie")
            return success(count)

        except Exception as e:
            logger.error(f"清理过期 Cookie 失败: {e}")
            return error(f"清理过期 Cookie 失败: {e}", "COOKIE_CLEANUP_ERROR")

    async def get_cookie_info(
        self, platform: str, username: str
    ) -> Result[dict[str, Any]]:
        """
        获取 Cookie 信息（不包含实际 Cookie 数据）

        Args:
            platform: 平台名称
            username: 用户名

        Returns:
            Result[dict]: Cookie 信息
        """
        try:
            cookie_file = self._get_cookie_file(platform, username)

            if not cookie_file.exists():
                return error("Cookie 文件不存在", "COOKIE_NOT_FOUND")

            async with aiofiles.open(cookie_file, "r", encoding="utf-8") as f:
                content = await f.read()
                cookie_data = json.loads(content)

            expires_at = datetime.fromisoformat(cookie_data["expires_at"])
            is_expired = datetime.now() > expires_at

            info = {
                "platform": cookie_data["platform"],
                "username": cookie_data["username"],
                "created_at": cookie_data["created_at"],
                "expires_at": cookie_data["expires_at"],
                "last_used": cookie_data.get("last_used"),
                "is_expired": is_expired,
                "cookie_count": len(cookie_data.get("cookies", [])),
            }

            return success(info)

        except Exception as e:
            logger.error(f"获取 Cookie 信息失败: {e}")
            return error(f"获取 Cookie 信息失败: {e}", "COOKIE_INFO_ERROR")

    def get_platform_login_url(self, platform: str) -> str | None:
        """获取平台登录 URL"""
        return self.PLATFORM_LOGIN_URLS.get(platform)

    def get_key_cookies(self, platform: str) -> list[str]:
        """获取平台关键 Cookie 名称"""
        return self.PLATFORM_KEY_COOKIES.get(platform, [])

    async def get_cookies_dict(
        self, platform: str, username: str
    ) -> Result[dict[str, str]]:
        """
        获取 Cookie 字典格式 (用于 HTTP 请求)

        Args:
            platform: 平台名称
            username: 用户名

        Returns:
            Result[dict]: Cookie 字典 {name: value}
        """
        result = await self.load_cookies(platform, username)
        if not result.success:
            return error(result.error or "加载 Cookie 失败", "COOKIE_LOAD_ERROR")

        cookies = result.data
        cookie_dict = {
            c["name"]: c["value"] for c in cookies if "name" in c and "value" in c
        }

        return success(cookie_dict)

    async def get_status_summary(self) -> Result[dict[str, Any]]:
        """
        获取所有平台登录状态摘要

        Returns:
            Result[dict]: 各平台登录状态
        """
        summary = {}

        try:
            for platform in self.PLATFORM_KEY_COOKIES.keys():
                # 查找该平台的 Cookie 文件
                pattern = f"{platform}_*.json"
                cookie_files = list(self.storage_dir.glob(pattern))

                if cookie_files:
                    # 取第一个（通常只有一个账号）
                    try:
                        async with aiofiles.open(
                            cookie_files[0], "r", encoding="utf-8"
                        ) as f:
                            content = await f.read()
                            data = json.loads(content)

                        expires_at = datetime.fromisoformat(data["expires_at"])
                        days_left = max(0, (expires_at - datetime.now()).days)

                        summary[platform] = {
                            "logged_in": True,
                            "username": data.get("username", "unknown"),
                            "saved_at": data.get("created_at"),
                            "expires_at": data["expires_at"],
                            "days_left": days_left,
                            "status": (
                                "valid"
                                if days_left > 3
                                else "expiring_soon" if days_left > 0 else "expired"
                            ),
                        }
                    except Exception:
                        summary[platform] = {"logged_in": False, "status": "error"}
                else:
                    summary[platform] = {"logged_in": False, "status": "not_logged_in"}

            return success(summary)

        except Exception as e:
            logger.error(f"获取状态摘要失败: {e}")
            return error(f"获取状态摘要失败: {e}", "STATUS_SUMMARY_ERROR")


# 全局单例
_cookie_manager: CookieManager | None = None


def get_cookie_manager() -> CookieManager:
    """获取 Cookie 管理器单例"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager
