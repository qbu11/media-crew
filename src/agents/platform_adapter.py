"""
Platform Adapter Agent

平台适配师：将内容适配到不同平台的格式和风格要求。
"""

from enum import Enum
from typing import Any

from .base_agent import BaseAgent


class Platform(Enum):
    """支持的平台枚举。"""

    WECHAT = "wechat"  # 微信公众号
    XIAOHONGSHU = "xiaohongshu"  # 小红书
    DOUYIN = "douyin"  # 抖音
    BILIBILI = "bilibili"  # B站
    ZHIHU = "zhihu"  # 知乎
    WEIBO = "weibo"  # 微博


class PlatformAdapter(BaseAgent):
    """
    平台适配师 Agent。

    职责：
    - 将通用内容转换为各平台专属格式
    - 调整内容风格以匹配平台调性
    - 生成平台特定的元素（标题、标签、封面等）
    - 确保内容符合平台规范
    """

    # 平台规格配置
    PLATFORM_SPECS: dict[Platform, dict[str, Any]] = {
        Platform.WECHAT: {
            "title_max_length": 64,
            "summary_max_length": 200,
            "max_tags": 5,
            "supports_markdown": True,
            "supports_html": True,
            "typical_length": "1500-3000",
        },
        Platform.XIAOHONGSHU: {
            "title_max_length": 20,
            "summary_max_length": 100,
            "max_tags": 10,
            "supports_markdown": False,
            "supports_html": False,
            "typical_length": "500-1500",
            "emoji_required": True,
        },
        Platform.DOUYIN: {
            "title_max_length": 50,
            "summary_max_length": 150,
            "max_tags": 5,
            "supports_markdown": False,
            "supports_html": False,
            "typical_length": "200-500",
            "video_focused": True,
        },
        Platform.BILIBILI: {
            "title_max_length": 80,
            "summary_max_length": 500,
            "max_tags": 12,
            "supports_markdown": False,
            "supports_html": False,
            "typical_length": "800-2000",
        },
        Platform.ZHIHU: {
            "title_max_length": 50,
            "summary_max_length": 300,
            "max_tags": 5,
            "supports_markdown": True,
            "supports_html": True,
            "typical_length": "2000-5000",
        },
        Platform.WEIBO: {
            "title_max_length": 30,
            "summary_max_length": 140,
            "max_tags": 5,
            "supports_markdown": False,
            "supports_html": False,
            "typical_length": "100-300",
        },
    }

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "平台适配师"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "将通用内容精准适配到各平台的格式和风格要求， "
            "确保内容在每个平台都能获得最佳表现"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位全能的平台适配专家，对各大内容平台的特性如数家珍。
你深谙微信公众号的深度阅读氛围、小红书的种草文化、抖音的快节奏叙事、
B站的弹幕文化、知乎的专业讨论氛围、微博的广场效应。
你能够将同一内容在不同平台上转化为完全不同的呈现形式，
同时保持核心信息的一致性。
你了解每个平台的推荐算法偏好，能够针对性地优化内容以获得更好的流量。
你的适配工作让内容在每个平台都能如鱼得水。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - platform_api_tool: 平台 API 工具（获取规范）
        # - image_generator: 图片生成工具
        # - hashtag_suggester: 标签建议工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools

    @classmethod
    def get_platform_specs(cls, platform: Platform) -> dict[str, Any]:
        """
        获取平台规格配置。

        Args:
            platform: 平台枚举

        Returns:
            平台规格字典
        """
        return cls.PLATFORM_SPECS.get(platform, {})


class AdaptedContent:
    """
    适配后内容的数据结构。

    用于规范化平台适配师的输出格式。
    """

    def __init__(
        self,
        platform: Platform,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        cover_image: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        初始化适配后内容。

        Args:
            platform: 目标平台
            title: 平台适配后的标题
            content: 平台适配后的正文
            summary: 平台适配后的摘要
            tags: 平台适配后的标签
            cover_image: 封面图 URL 或提示词
            metadata: 其他元数据
        """
        self.platform = platform
        self.title = title
        self.content = content
        self.summary = summary
        self.tags = tags
        self.cover_image = cover_image
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "platform": self.platform.value,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "cover_image": self.cover_image,
            "metadata": self.metadata,
        }
