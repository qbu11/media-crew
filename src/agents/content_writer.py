"""
Content Writer Agent

内容创作者：根据选题和平台特性创作高质量、高传播力的内容。
"""

from typing import Any

from .base_agent import BaseAgent


class ContentWriter(BaseAgent):
    """
    内容创作者 Agent。

    职责：
    - 根据选题报告创作原创内容
    - 适配不同平台的内容风格和格式
    - 确保内容质量和传播力
    - 生成标题、正文、标签等完整内容
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "内容创作者"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "根据选题报告和目标平台的特性，创作高质量、高传播力、 "
            "符合平台调性的原创内容，包括标题、正文、摘要、标签等"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位才华横溢的内容创作者，精通各大平台的内容创作规范。
你的文字既有深度又有趣味性，总能抓住读者的注意力。
你擅长将复杂的概念用通俗易懂的方式表达出来，
同时保持内容的准确性和专业性。
你创作的内容总能在各平台获得良好的传播效果，
你对标题党、情绪调动、排版节奏等传播技巧驾轻就熟。
无论是深度长文、短视频脚本，还是图文内容，你都能游刃有余。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.OPUS_MODEL  # claude-opus-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - search_tool: 搜索工具（查找参考资料）
        # - file_writer: 文件写入工具
        # - markdown_formatter: Markdown 格式化工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class ContentDraft:
    """
    内容草稿数据结构。

    用于规范化内容创作者的输出格式。
    """

    def __init__(
        self,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        cover_image_prompt: str | None = None,
        platform: str = "general",
        metadata: dict[str, Any] | None = None,
    ):
        """
        初始化内容草稿。

        Args:
            title: 内容标题
            content: 正文内容（Markdown 格式）
            summary: 内容摘要
            tags: 标签列表
            cover_image_prompt: 封面图提示词（可选）
            platform: 目标平台
            metadata: 其他元数据
        """
        self.title = title
        self.content = content
        self.summary = summary
        self.tags = tags
        self.cover_image_prompt = cover_image_prompt
        self.platform = platform
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "cover_image_prompt": self.cover_image_prompt,
            "platform": self.platform,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """转换为完整的 Markdown 文档。"""
        lines = [
            f"# {self.title}",
            "",
            f"**摘要**: {self.summary}",
            "",
            f"**标签**: {', '.join(self.tags)}",
            "",
            "---",
            "",
            self.content,
        ]
        return "\n".join(lines)
