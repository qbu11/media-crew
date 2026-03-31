"""
Content Orchestrator - 内容编排者

作为编排者（Orchestrator），协调多个子 Agent 完成内容创作：
- Researcher：热点研究、爆款分析
- Marketer：策略制定、发布规划
- Copywriter：文案创作、平台适配
- Designer：图片生成、视觉设计

工作流程：
1. Researcher 收集热点和爆款参考
2. Marketer 制定内容策略
3. Copywriter 根据策略创作文案
4. Designer 生成配图和封面
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base_agent import BaseAgent
from .researcher import Researcher, ResearchReport
from .marketer import Marketer, ContentStrategy
from .copywriter import Copywriter, CopyDraft
from .designer import Designer, DesignOutput

if TYPE_CHECKING:
    from src.crew.callbacks import CallbackHandler


class ContentOrchestrator(BaseAgent):
    """
    内容编排者 Agent。

    作为协调者，指挥多个子 Agent 完成内容创作的完整流程。
    """

    _tools: list[Any] = []
    _sub_agents: dict[str, BaseAgent] = {}

    def __init__(
        self,
        enable_researcher: bool = True,
        enable_marketer: bool = True,
        enable_copywriter: bool = True,
        enable_designer: bool = True,
    ):
        self.enable_researcher = enable_researcher
        self.enable_marketer = enable_marketer
        self.enable_copywriter = enable_copywriter
        self.enable_designer = enable_designer
        self._sub_agents = {}
        self._init_sub_agents()

    def _init_sub_agents(self) -> None:
        """初始化子 Agent。"""
        if self.enable_researcher:
            self._sub_agents["researcher"] = Researcher()
        if self.enable_marketer:
            self._sub_agents["marketer"] = Marketer()
        if self.enable_copywriter:
            self._sub_agents["copywriter"] = Copywriter()
        if self.enable_designer:
            self._sub_agents["designer"] = Designer()

    def get_role(self) -> str:
        return "内容编排者"

    def get_goal(self) -> str:
        return (
            "协调多个专业子 Agent，高效完成从研究到发布的完整内容创作流程。"
            "确保每个环节的质量，输出高质量的整合内容。"
        )

    def get_backstory(self) -> str:
        return """你是一位资深的内容编排者，擅长协调多个专业 Agent 完成复杂的内容创作任务。

## 可调度的子 Agent

- **Researcher**（热点研究员）→ 研究报告
- **Marketer**（营销策划师）→ 内容策略
- **Copywriter**（文案创作者）→ 文案草稿
- **Designer**（视觉设计师）→ 设计输出

## 编排原则

- **灵活性**：支持跳过某些阶段
- **可追溯**：记录每个阶段的输出
- **质量优先**：不满意的输出要求重做
"""

    def get_tools(self) -> list[Any]:
        return self._tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        cls._tools = tools

    def get_sub_agent(self, name: str) -> BaseAgent | None:
        return self._sub_agents.get(name)

    def list_sub_agents(self) -> list[str]:
        return list(self._sub_agents.keys())

    async def orchestrate(
        self,
        topic: str,
        target_platform: str = "xiaohongshu",
        content_type: str = "article",
        taste_context: str = "",
        callback: CallbackHandler | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        执行编排流程（异步，带回调）。

        Args:
            topic: 内容主题
            target_platform: 目标平台
            content_type: 内容类型
            taste_context: 用户 taste 偏好描述
            callback: WS 事件回调
        """
        workflow_stages: dict[str, Any] = {}
        research_output: dict[str, Any] | None = None
        strategy_output: dict[str, Any] | None = None
        copy_output: dict[str, Any] | None = None
        design_output: dict[str, Any] | None = None

        # ── 阶段 1：研究 ──────────────────────────────────────
        if self.enable_researcher and "researcher" in self._sub_agents:
            if callback:
                await callback.emit_agent_started(
                    "researcher", "热点研究员",
                    {"topic": topic, "platform": target_platform},
                )

            try:
                researcher: Researcher = self._sub_agents["researcher"]  # type: ignore[assignment]
                research_output = await researcher.run(
                    topic=topic,
                    target_platform=target_platform,
                    callback=callback,
                )
                workflow_stages["research"] = {
                    "completed": True,
                    "output": research_output,
                }

                if callback:
                    await callback.emit_agent_completed(
                        "researcher", "热点研究员",
                        {
                            "trending_count": len(research_output.get("trending_topics", [])),
                            "viral_count": len(research_output.get("viral_references", [])),
                            "recommendations": research_output.get("recommendations", []),
                        },
                    )
            except Exception as e:
                workflow_stages["research"] = {"completed": False, "error": str(e)}
                if callback:
                    await callback.emit_agent_failed("researcher", "热点研究员", str(e))

        # ── 阶段 2：策略 ──────────────────────────────────────
        if self.enable_marketer and "marketer" in self._sub_agents:
            if callback:
                await callback.emit_agent_started(
                    "marketer", "营销策划师",
                    {"topic": topic, "has_research": research_output is not None},
                )

            try:
                marketer: Marketer = self._sub_agents["marketer"]  # type: ignore[assignment]
                strategy_output = await marketer.run(
                    topic=topic,
                    target_platform=target_platform,
                    research_data=research_output,
                    taste_context=taste_context,
                    callback=callback,
                )
                workflow_stages["strategy"] = {
                    "completed": True,
                    "output": strategy_output,
                }

                if callback:
                    cs = strategy_output.get("content_strategy", {})
                    await callback.emit_agent_completed(
                        "marketer", "营销策划师",
                        {
                            "main_theme": cs.get("main_theme"),
                            "tone": cs.get("tone"),
                            "differentiation": cs.get("differentiation"),
                        },
                    )
            except Exception as e:
                workflow_stages["strategy"] = {"completed": False, "error": str(e)}
                if callback:
                    await callback.emit_agent_failed("marketer", "营销策划师", str(e))

        # ── 阶段 3：创作 ──────────────────────────────────────
        if self.enable_copywriter and "copywriter" in self._sub_agents:
            if callback:
                await callback.emit_agent_started(
                    "copywriter", "文案创作者",
                    {"topic": topic, "has_strategy": strategy_output is not None},
                )

            try:
                copywriter: Copywriter = self._sub_agents["copywriter"]  # type: ignore[assignment]
                copy_output = await copywriter.run(
                    topic=topic,
                    target_platform=target_platform,
                    research_data=research_output,
                    strategy_data=strategy_output,
                    taste_context=taste_context,
                    callback=callback,
                )
                workflow_stages["copywriting"] = {
                    "completed": True,
                    "output": copy_output,
                }

                if callback:
                    await callback.emit_agent_completed(
                        "copywriter", "文案创作者",
                        {
                            "title": copy_output.get("title"),
                            "word_count": len(copy_output.get("content", "")),
                            "variants": len(copy_output.get("title_variants", [])),
                            "compliant": copy_output.get("compliance_check", {}).get("passed"),
                        },
                    )
            except Exception as e:
                workflow_stages["copywriting"] = {"completed": False, "error": str(e)}
                if callback:
                    await callback.emit_agent_failed("copywriter", "文案创作者", str(e))

        # ── 阶段 4：设计 ──────────────────────────────────────
        if self.enable_designer and "designer" in self._sub_agents:
            if callback:
                await callback.emit_agent_started(
                    "designer", "视觉设计师",
                    {"topic": topic, "has_content": copy_output is not None},
                )

            try:
                designer: Designer = self._sub_agents["designer"]  # type: ignore[assignment]
                design_output = await designer.run(
                    topic=topic,
                    content_data=copy_output,
                    target_platform=target_platform,
                    callback=callback,
                )
                workflow_stages["design"] = {
                    "completed": True,
                    "output": design_output,
                }

                if callback:
                    await callback.emit_agent_completed(
                        "designer", "视觉设计师",
                        {
                            "cover_prompt": design_output.get("cover_image", {}).get("prompt", "")[:80],
                            "image_count": len(design_output.get("content_images", [])),
                            "style": design_output.get("image_style", {}).get("style"),
                        },
                    )
            except Exception as e:
                workflow_stages["design"] = {"completed": False, "error": str(e)}
                if callback:
                    await callback.emit_agent_failed("designer", "视觉设计师", str(e))

        # ── 整合最终输出 ──────────────────────────────────────
        final_output = self._build_final_output(
            topic, target_platform, copy_output, design_output,
        )

        return {
            "topic": topic,
            "platform": target_platform,
            "workflow_stages": workflow_stages,
            "final_output": final_output,
            "metadata": {
                "sub_agents": self.list_sub_agents(),
                "workflow_config": {
                    "researcher": self.enable_researcher,
                    "marketer": self.enable_marketer,
                    "copywriter": self.enable_copywriter,
                    "designer": self.enable_designer,
                },
                "generated_at": datetime.now().isoformat(),
            },
        }

    def _build_final_output(
        self,
        topic: str,
        platform: str,
        copy_output: dict[str, Any] | None,
        design_output: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """整合最终输出。"""
        if not copy_output:
            return None

        result: dict[str, Any] = {
            "title": copy_output.get("title", ""),
            "content": copy_output.get("content", ""),
            "summary": copy_output.get("summary", ""),
            "tags": copy_output.get("tags", []),
            "hashtags": copy_output.get("hashtags", []),
            "platform": platform,
            "word_count": len(copy_output.get("content", "")),
            "title_variants": copy_output.get("title_variants", []),
            "compliance_check": copy_output.get("compliance_check"),
        }

        if design_output:
            result["cover_image"] = design_output.get("cover_image")
            result["content_images"] = design_output.get("content_images", [])
            result["image_style"] = design_output.get("image_style")

        return result

    # ── 同步兼容（保留旧接口） ────────────────────────────────
    def orchestrate_sync(
        self,
        topic: str,
        target_platform: str = "xiaohongshu",
        content_type: str = "article",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """同步版本（向后兼容）。"""
        import asyncio
        return asyncio.run(
            self.orchestrate(topic, target_platform, content_type, **kwargs)
        )


# 保持向后兼容
ContentCreator = ContentOrchestrator
