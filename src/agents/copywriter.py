"""
Copywriter Agent - 文案创作者

职责：根据策略创作文案、生成多版本、适配平台。

作为独立的 SubAgent，可被 ContentCreator Orchestrator 调用。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.crew.callbacks import CallbackHandler


class Copywriter(BaseAgent):
    """
    文案创作者 Agent。

    职责：
    - 根据策略和研究创作文案
    - 生成多个版本供 A/B 测试
    - 适配不同平台的内容格式
    - 确保内容质量和传播力
    """

    _tools: list[Any] = []

    def get_role(self) -> str:
        return "文案创作者"

    def get_goal(self) -> str:
        return (
            "根据策略创作高质量文案，生成多版本供选择，"
            "确保内容符合平台调性、具有传播力且合规。"
        )

    def get_backstory(self) -> str:
        return """你是一位资深的自媒体文案创作者，精通各平台的内容风格和用户喜好。

## 核心职责

1. **文案创作** — 标题、正文、摘要、话题标签
2. **风格适配** — 根据平台调性调整文风，保持品牌一致性
3. **A/B 版本** — 生成 2-3 个标题变体，不同切入角度
4. **合规检查** — 广告法极限词、平台敏感词、诱导互动词

## 敏感词清单

### 广告法极限词（禁止）
最、第一、顶级、极品、极致、史无前例、100%、王者、冠军、唯一、首个

### 诱导互动词（风险）
点赞过X、评论区领取、转发抽奖、关注送XX

### 站外引流词（风险）
微信号、加微信、手机号、扫码、淘宝、天猫、京东

## 工作原则

- **爆款对标**：每个文案至少参考 3 个爆款结构
- **平台适配**：严格遵守各平台规范
- **合规优先**：发现敏感词立即修改
- **多版本**：提供选择，不只有唯一答案
"""

    def get_tools(self) -> list[Any]:
        return self._tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        cls._tools = tools

    async def run(
        self,
        topic: str,
        target_platform: str = "xiaohongshu",
        research_data: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        taste_context: str = "",
        callback: CallbackHandler | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        执行文案创作流程。

        Args:
            topic: 内容主题
            target_platform: 目标平台
            research_data: Researcher 的研究报告
            strategy_data: Marketer 的策略
            taste_context: 用户 taste 偏好描述
            callback: WS 事件回调
        """
        # 工具 1：爆款结构分析
        if callback:
            await callback.emit_tool_start(
                "copywriter", "viral_structure_analysis",
                {"topic": topic, "reference_count": len((research_data or {}).get("viral_references", []))},
            )

        await asyncio.sleep(0.3)

        viral_patterns = self._analyze_viral_patterns(research_data)

        if callback:
            await callback.emit_tool_end(
                "copywriter", "viral_structure_analysis", "success",
                {"patterns_found": len(viral_patterns)},
            )

        # 工具 2：文案生成（LLM 调用）
        if callback:
            await callback.emit_tool_start(
                "copywriter", "content_generation",
                {"platform": target_platform, "tone": "亲和真诚+只讲重点"},
            )

        await asyncio.sleep(0.5)

        draft = self._generate_draft(topic, target_platform, strategy_data, taste_context, viral_patterns)

        if callback:
            await callback.emit_tool_end(
                "copywriter", "content_generation", "success",
                {"title": draft["title"], "word_count": len(draft["content"])},
            )

        # 工具 3：合规检查
        if callback:
            await callback.emit_tool_start(
                "copywriter", "compliance_check",
                {"content_length": len(draft["content"])},
            )

        await asyncio.sleep(0.2)

        compliance = self._check_compliance(draft["content"])

        if callback:
            await callback.emit_tool_end(
                "copywriter", "compliance_check", "success",
                {"passed": compliance["passed"], "issues": len(compliance["issues"])},
            )

        draft["compliance_check"] = compliance

        # 工具 4：标题变体生成
        if callback:
            await callback.emit_tool_start(
                "copywriter", "title_variant_generation",
                {"original_title": draft["title"]},
            )

        await asyncio.sleep(0.2)

        draft["title_variants"] = self._generate_title_variants(topic, target_platform)

        if callback:
            await callback.emit_tool_end(
                "copywriter", "title_variant_generation", "success",
                {"variant_count": len(draft["title_variants"])},
            )

        return draft

    def _analyze_viral_patterns(self, research_data: dict[str, Any] | None) -> list[str]:
        """从爆款中提取结构模式。"""
        if not research_data:
            return ["清单体", "故事体", "观点体"]
        refs = research_data.get("viral_references", [])
        patterns = []
        for ref in refs:
            analysis = ref.get("analysis", {})
            structure = analysis.get("structure", "")
            if structure and structure not in patterns:
                patterns.append(structure)
        return patterns or ["清单体", "故事体", "观点体"]

    def _generate_draft(
        self,
        topic: str,
        platform: str,
        strategy: dict[str, Any] | None,
        taste_context: str,
        patterns: list[str],
    ) -> dict[str, Any]:
        """生成文案草稿（实际会调用 LLM）。"""
        # 这里是结构化输出，实际会由 LLM 生成
        tone = "亲和真诚+只讲重点"
        if strategy:
            cs = strategy.get("content_strategy", {})
            tone = cs.get("tone", tone)

        return {
            "title": f"试了20多款AI工具，最后只留了这3个",
            "content": self._build_content(topic, platform, tone),
            "summary": f"一篇关于{topic}的实用分享",
            "tags": [topic, "效率提升", "职场干货", "工具推荐"],
            "hashtags": [f"#{topic}", "#效率提升", "#职场干货"],
            "platform": platform,
            "style_notes": f"调性: {tone}，结构参考: {', '.join(patterns[:3])}",
        }

    def _build_content(self, topic: str, platform: str, tone: str) -> str:
        """构建正文内容。"""
        # 实际由 LLM 生成，这里是结构化模板
        return (
            f"之前跟你们一样，看到推荐就下载，手机和电脑装了一堆AI工具，"
            f"结果真正用起来的没几个。\n\n"
            f"上个月我做了个断舍离，把所有AI工具过了一遍，"
            f"留下标准就一个：每周至少用3次以上的才留。\n\n"
            f"最后活下来的就3个：\n\n"
            f"1️⃣ Kimi — 处理长文档\n"
            f"开会录音丢进去，5分钟出会议纪要。\n\n"
            f"2️⃣ ChatGPT — 想方案\n"
            f"不是让它直接写，是让它帮我想。\n\n"
            f"3️⃣ 秘塔搜索 — 查资料\n"
            f"以前百度搜一个问题要翻好几页，现在直接给答案+来源。\n\n"
            f"工具不在多。找到适合自己节奏的2-3个，用熟了，效率自然就上来了。\n\n"
            f"你现在在用哪个？评论区聊聊 👇"
        )

    def _check_compliance(self, content: str) -> dict[str, Any]:
        """合规检查。"""
        forbidden_words = [
            "最", "第一", "顶级", "极品", "极致", "史无前例",
            "100%", "王者", "冠军", "唯一", "首个",
        ]
        risky_words = [
            "点赞过", "评论区领取", "转发抽奖", "关注送",
            "微信号", "加微信", "手机号", "扫码",
        ]

        issues = []
        warnings = []

        for word in forbidden_words:
            if word in content:
                issues.append(f"包含广告法极限词: {word}")

        for word in risky_words:
            if word in content:
                warnings.append(f"包含风险词: {word}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _generate_title_variants(self, topic: str, platform: str) -> list[str]:
        """生成标题变体。"""
        return [
            f"试了20多款AI工具，最后只留了这3个",
            f"每天花2小时做的事，用AI只要20分钟",
            f"别再囤AI工具了，你的问题不是工具不够多",
        ]


class CopyDraft:
    """文案草稿数据结构。"""

    def __init__(
        self,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        title_variants: list[str] | None = None,
        hashtags: list[str] | None = None,
        cover_image_prompt: str | None = None,
        variants: list[dict[str, Any]] | None = None,
        compliance_check: dict[str, Any] | None = None,
        style_notes: str = "",
        platform: str = "general",
    ):
        self.title = title
        self.content = content
        self.summary = summary
        self.tags = tags
        self.title_variants = title_variants or []
        self.hashtags = hashtags or []
        self.cover_image_prompt = cover_image_prompt
        self.variants = variants or []
        self.compliance_check = compliance_check or {"passed": True, "issues": [], "warnings": []}
        self.style_notes = style_notes
        self.platform = platform

    @property
    def word_count(self) -> int:
        return len(self.content)

    @property
    def is_compliant(self) -> bool:
        return self.compliance_check.get("passed", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "title_variants": self.title_variants,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "hashtags": self.hashtags,
            "cover_image_prompt": self.cover_image_prompt,
            "variants": self.variants,
            "compliance_check": self.compliance_check,
            "style_notes": self.style_notes,
            "platform": self.platform,
            "word_count": self.word_count,
        }

    def to_markdown(self) -> str:
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
