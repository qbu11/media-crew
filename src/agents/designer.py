"""
Designer Agent - 视觉设计师

职责：生成图片、设计封面、优化视觉呈现。

作为独立的 SubAgent，可被 ContentCreator Orchestrator 调用。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.crew.callbacks import CallbackHandler


class Designer(BaseAgent):
    """
    视觉设计师 Agent。

    职责：
    - 生成配图和封面
    - 设计图片布局和风格
    - 优化视觉呈现效果
    - 确保图文协调统一
    """

    _tools: list[Any] = []

    def get_role(self) -> str:
        return "视觉设计师"

    def get_goal(self) -> str:
        return (
            "生成高质量配图、设计吸引眼球的封面、优化视觉呈现，"
            "确保图文协调统一，提升内容传播力。"
        )

    def get_backstory(self) -> str:
        return """你是一位资深的自媒体视觉设计师，精通图片设计和视觉营销。

## 核心职责

1. **图片生成** — 使用 DALL-E 生成原创配图
2. **封面设计** — 吸引眼球的视觉元素、品牌调性一致性
3. **图片处理** — 裁剪适配各平台、滤镜和色彩调整
4. **图文排版** — 信息图设计、长图拼接、九宫格布局

## 平台图片规范

### 小红书
- 封面：3:4（1242x1660px）
- 正文图：3:4 或 1:1
- 数量：1-9 张
- 注意：不能有文字（文字在正文中）

### 微信公众号
- 封面：2.35:1（900x383px）或 1:1
- 正文图：宽度 900px

### 微博
- 图片：1-9 张
- 尺寸：690x690px（1:1）或 690x920px（3:4）

## 工作原则

- **原创性**：不直接使用他人图片
- **相关性**：图片与内容高度相关
- **品牌一致**：保持视觉风格统一
- **平台适配**：一次生成，多平台复用
"""

    def get_tools(self) -> list[Any]:
        return self._tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        cls._tools = tools

    async def run(
        self,
        topic: str,
        content_data: dict[str, Any] | None = None,
        target_platform: str = "xiaohongshu",
        callback: CallbackHandler | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        执行视觉设计流程。

        Args:
            topic: 内容主题
            content_data: Copywriter 的文案数据
            target_platform: 目标平台
            callback: WS 事件回调
        """
        # 工具 1：封面图生成
        if callback:
            await callback.emit_tool_start(
                "designer", "cover_image_generation",
                {"topic": topic, "platform": target_platform},
            )

        await asyncio.sleep(0.3)

        cover_image = self._generate_cover_image(topic, target_platform, content_data)

        if callback:
            await callback.emit_tool_end(
                "designer", "cover_image_generation", "success",
                {"prompt_length": len(cover_image["prompt"])},
            )

        # 工具 2：配图方案生成
        if callback:
            await callback.emit_tool_start(
                "designer", "content_images_planning",
                {"platform": target_platform},
            )

        await asyncio.sleep(0.2)

        content_images = self._plan_content_images(topic, target_platform, content_data)

        if callback:
            await callback.emit_tool_end(
                "designer", "content_images_planning", "success",
                {"image_count": len(content_images)},
            )

        # 工具 3：视觉风格定义
        if callback:
            await callback.emit_tool_start(
                "designer", "visual_style_definition",
                {"tone": "亲和真诚+简洁"},
            )

        await asyncio.sleep(0.1)

        image_style = {
            "color_palette": ["#4A90E2", "#50E3C2", "#F5A623"],
            "style": "minimalist",
            "mood": "friendly",
        }

        if callback:
            await callback.emit_tool_end(
                "designer", "visual_style_definition", "success",
                image_style,
            )

        return {
            "cover_image": cover_image,
            "content_images": content_images,
            "image_style": image_style,
            "platform_adaptations": self._build_platform_adaptations(
                target_platform, cover_image, content_images,
            ),
            "generation_notes": f"为 {target_platform} 平台生成的视觉方案",
        }

    def _generate_cover_image(
        self, topic: str, platform: str, content_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """生成封面图方案。"""
        title = content_data.get("title", topic) if content_data else topic

        prompt = (
            f"A clean, minimalist cover image for social media about '{topic}'. "
            f"Title: '{title}'. Style: modern, friendly, with soft colors. "
            f"No text on image. 3:4 aspect ratio."
        )

        size_map = {
            "xiaohongshu": {"width": 1242, "height": 1660},
            "wechat": {"width": 900, "height": 383},
            "weibo": {"width": 690, "height": 920},
            "zhihu": {"width": 690, "height": 400},
            "douyin": {"width": 1080, "height": 1920},
            "bilibili": {"width": 1920, "height": 1080},
        }

        return {
            "prompt": prompt,
            "url": "",  # 实际调用 DALL-E 后填充
            "alt_text": f"{title} - 封面图",
            "dimensions": size_map.get(platform, {"width": 1242, "height": 1660}),
        }

    def _plan_content_images(
        self, topic: str, platform: str, content_data: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """规划内容配图。"""
        content = content_data.get("content", "") if content_data else ""
        # 简单分析内容，决定需要几张配图
        image_count = min(3, content.count("\n\n") + 1) if content else 3

        return [
            {
                "prompt": f"Illustration for section {i + 1} about {topic}. Minimalist style.",
                "url": "",
                "alt_text": f"{topic} 配图{i + 1}",
                "position": f"after_paragraph_{i + 1}",
            }
            for i in range(image_count)
        ]

    def _build_platform_adaptations(
        self, platform: str, cover: dict, images: list
    ) -> dict[str, Any]:
        """构建各平台适配方案。"""
        return {
            platform: {
                "cover": cover["prompt"],
                "images": [img["prompt"] for img in images],
            }
        }


class DesignOutput:
    """设计输出数据结构。"""

    def __init__(
        self,
        cover_image: dict[str, Any],
        content_images: list[dict[str, Any]] | None = None,
        image_style: dict[str, Any] | None = None,
        platform_adaptations: dict[str, Any] | None = None,
        generation_notes: str = "",
    ):
        self.cover_image = cover_image
        self.content_images = content_images or []
        self.image_style = image_style or {}
        self.platform_adaptations = platform_adaptations or {}
        self.generation_notes = generation_notes

    def to_dict(self) -> dict[str, Any]:
        return {
            "cover_image": self.cover_image,
            "content_images": self.content_images,
            "image_style": self.image_style,
            "platform_adaptations": self.platform_adaptations,
            "generation_notes": self.generation_notes,
        }

    @property
    def image_count(self) -> int:
        return 1 + len(self.content_images)

    def get_images_for_platform(self, platform: str) -> dict[str, Any]:
        if platform in self.platform_adaptations:
            return self.platform_adaptations[platform]
        return {
            "cover": self.cover_image.get("url"),
            "images": [img.get("url") for img in self.content_images],
        }
