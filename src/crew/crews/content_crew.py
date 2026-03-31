"""
Content Crew Module

内容生产线 Crew：支持两种模式

模式 1 - 简化模式（2个 Agent）：
- ContentCreator：内容研究创作
- ContentReviewer：内容审核

模式 2 - 完整模式（Orchestrator + SubAgent）：
- Researcher：热点研究、爆款分析
- Marketer：策略制定、发布规划
- Copywriter：文案创作、平台适配
- Designer：图片生成、视觉设计
- ContentReviewer：内容审核

核心逻辑：什么火就发什么
"""

import logging
import os
from enum import Enum
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task

from src.agents import (
    ContentOrchestrator,
    ContentReviewer,
    Copywriter,
    Designer,
    Marketer,
    Researcher,
)
from src.agents.researcher import ResearchReport
from src.agents.marketer import ContentStrategy
from src.agents.copywriter import CopyDraft
from src.agents.designer import DesignOutput
from src.services.taste_engine import TasteEngine

from .base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus

logger = logging.getLogger(__name__)


class WorkflowMode(str, Enum):
    """工作流模式"""

    SIMPLE = "simple"  # 简化模式：2 个 Agent
    FULL = "full"  # 完整模式：Orchestrator + SubAgent


class ContentCrewInput(CrewInput):
    """
    ContentCrew 专用输入数据类。

    Args:
        topic: 内容主题
        target_platform: 目标平台
        content_type: 内容类型（article, video, image_post）
        research_depth: 研究深度（basic, standard, deep）
        enable_human_review: 是否启用人工审核
        viral_category: 爆款垂类（美妆/职场/穿搭/情感/干货等）
    """

    def __init__(
        self,
        topic: str,
        target_platform: str = "xiaohongshu",
        content_type: str = "article",
        research_depth: str = "standard",
        enable_human_review: bool = True,
        viral_category: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.inputs.update({
            "topic": topic,
            "target_platform": target_platform,
            "content_type": content_type,
            "research_depth": research_depth,
            "enable_human_review": enable_human_review,
            "viral_category": viral_category,
        })
        self.metadata.update({
            "content_type": content_type,
            "research_depth": research_depth,
            "viral_category": viral_category,
        })


class ContentCrewResult(CrewResult):
    """
    ContentCrew 专用结果数据类。

    扩展自 CrewResult，添加内容生产特定的字段。
    """

    def __init__(
        self,
        status: CrewStatus,
        research_findings: dict[str, Any] | None = None,
        content_draft: dict[str, Any] | None = None,
        review_report: dict[str, Any] | None = None,
        viral_reference_report: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(status=status, **kwargs)
        self.research_findings = research_findings
        self.content_draft = content_draft
        self.review_report = review_report
        self.viral_reference_report = viral_reference_report

        # 更新 data 字段
        if self.data is None:
            self.data = {}
        self.data.update({
            "research_findings": research_findings,
            "content_draft": content_draft,
            "review_report": review_report,
            "viral_reference_report": viral_reference_report,
        })

    @property
    def is_approved(self) -> bool:
        """检查内容是否通过审核。"""
        if self.review_report:
            return self.review_report.get("result") == "approved"
        return False

    @property
    def viral_check_passed(self) -> bool:
        """检查爆款对标验证是否通过。"""
        if self.review_report:
            return self.review_report.get("viral_check", False)
        if self.viral_reference_report:
            return self.viral_reference_report.get("passed", False)
        return False

    @property
    def viral_reference_count(self) -> int:
        """获取爆款对标数量。"""
        if self.review_report:
            return self.review_report.get("viral_count", 0)
        if self.content_draft:
            refs = self.content_draft.get("viral_references", [])
            return len(refs) if refs else 0
        return 0


class ContentCrew(BaseCrew):
    """
    内容生产线 Crew。

    新架构（2个 Agent）：
    1. ContentCreator（内容研究创作）：追踪热点 → 研究爆款 → 学习风格 → 创作内容
    2. ContentReviewer（内容审核）：独立审核内容质量和合规性

    核心逻辑：什么火就发什么
    """

    def __init__(
        self,
        verbose: bool = True,
        process: Process = Process.sequential,
        memory: bool = True,
        max_rpm: int | None = None,
        enable_human_review: bool = True,
        llm: str | None = None,
    ):
        """
        初始化 ContentCrew。

        Args:
            verbose: 是否输出详细日志
            process: 执行流程类型
            memory: 是否使用记忆
            max_rpm: 每分钟最大执行次数
            enable_human_review: 是否启用人工审核
            llm: LLM 模型名称
        """
        super().__init__(
            verbose=verbose,
            process=process,
            memory=memory,
            max_rpm=max_rpm,
        )
        self.enable_human_review = enable_human_review

        # 配置 LLM：优先使用 Anthropic Claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "sk-ant-xxx":
            self.llm = LLM(
                model="anthropic/claude-sonnet-4-20250514",
                api_key=api_key,
            )
        else:
            # 回退到默认
            self.llm = llm or "gpt-4o-mini"

    def get_crew_name(self) -> str:
        """返回 Crew 名称。"""
        return "ContentCrew"

    def get_agents(self, platform: str = "") -> list:
        """返回 Agent 列表。"""
        from crewai import Agent
        from src.agents.content_creator import ContentCreator as RealContentCreator
        from src.agents.content_reviewer import ContentReviewer

        # 返回 Agent 实例（不传入 tools，在 build_crew 中再设置）
        return [
            Agent(
                role=RealContentCreator().get_role(),
                goal=RealContentCreator().get_goal(),
                backstory=RealContentCreator().get_backstory(platform=platform),
                verbose=self.verbose,
                llm=self.llm,
            ),
            Agent(
                role=ContentReviewer().get_role(),
                goal=ContentReviewer().get_goal(),
                backstory=ContentReviewer().get_backstory(platform=platform),
                verbose=self.verbose,
                llm=self.llm,
                human_input=self.enable_human_review,
            ),
        ]

    def get_tasks(self, inputs: CrewInput) -> list:
        """返回任务列表。"""
        from crewai import Task

        topic = inputs.inputs.get("topic", "")
        target_platform = inputs.inputs.get("target_platform", "xiaohongshu")
        content_type = inputs.inputs.get("content_type", "article")
        research_depth = inputs.inputs.get("research_depth", "standard")
        viral_category = inputs.inputs.get("viral_category", "")

        # 使用 _create_tasks 创建任务
        agents = self.get_agents(platform=target_platform)
        return self._create_tasks(
            agents=agents,
            topic=topic,
            target_platform=target_platform,
            content_type=content_type,
            research_depth=research_depth,
            viral_category=viral_category,
            taste_context=inputs.inputs.get("taste_context", ""),
            revision_feedback=inputs.inputs.get("revision_feedback", ""),
        )

    def build_crew(self, inputs: CrewInput) -> Any:
        """
        构建 Crew 实例。

        Args:
            inputs: Crew 输入

        Returns:
            Crew 实例
        """
        from crewai import Agent, Crew
        from src.agents.content_creator import ContentCreator as RealContentCreator
        from src.agents.content_reviewer import ContentReviewer
        topic = inputs.inputs.get("topic", "")
        target_platform = inputs.inputs.get("target_platform", "xiaohongshu")
        content_type = inputs.inputs.get("content_type", "article")
        research_depth = inputs.inputs.get("research_depth", "standard")
        viral_category = inputs.inputs.get("viral_category", "")

        # 创建 Agent
        # Agent 1: 内容研究创作（合并了选题研究和内容创作）
        creator = Agent(
            role="内容研究创作者",
            goal=(
                "追踪热点、研究爆款、学习风格、创作内容。"
                "通过广泛阅读各平台爆款文章，深度学习其写作套路和风格特点，"
                "然后创作出符合平台调性、具有传播力的高质量内容"
            ),
            backstory=RealContentCreator().get_backstory(platform=target_platform),
            tools=[],  # 暂不使用工具
            verbose=self.verbose,
            llm=self.llm,
        )

        # Agent 2: 内容审核（独立）
        reviewer = Agent(
            role="内容审核员",
            goal=(
                "严格审核内容的质量、准确性和合规性，确保内容符合平台规则 "
                "和法律法规，同时提供具体的优化建议以提升内容价值"
            ),
            backstory=ContentReviewer().get_backstory(platform=target_platform),
            tools=[],  # 审核员不需要外部工具
            verbose=self.verbose,
            llm=self.llm,
            human_input=self.enable_human_review,
        )

        agents = [creator, reviewer]

        # 创建任务
        tasks = self._create_tasks(
            agents=agents,
            topic=topic,
            target_platform=target_platform,
            content_type=content_type,
            research_depth=research_depth,
            viral_category=viral_category,
            taste_context=inputs.inputs.get("taste_context", ""),
            revision_feedback=inputs.inputs.get("revision_feedback", ""),
        )

        # 构建 Crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=self.process,
            memory=self.memory,
            verbose=self.verbose,
        )

        return crew

    def _create_tasks(
        self,
        agents: list,
        topic: str,
        target_platform: str,
        content_type: str,
        research_depth: str,
        viral_category: str | None,
        taste_context: str = "",
        revision_feedback: str = "",
    ) -> list:
        """
        创建任务列表。

        新流程（2个任务）：
        1. 内容研究创作任务：研究爆款 + 学习风格 + 创作内容
        2. 内容审核任务：独立审核
        """

        category_hint = f"\n        **垂类方向**: {viral_category}" if viral_category else ""

        # 任务 1：内容研究创作
        create_description = f"""
        **主题**: {topic}
        **目标平台**: {target_platform}
        **内容类型**: {content_type}
        **研究深度**: {research_depth}{category_hint}

        ## 步骤 1：爆款对标研究

        在 {target_platform} 上搜索与「{topic}」相关的爆款内容。
        搜索来源至少覆盖 3 个：平台热榜、同垂类头部账号近 30 天高赞内容、相关话题下的爆款。
        按你的 backstory 中的规则完成 5 维度分析，提取可复制的模式。

        ## 步骤 2：拟定大纲

        基于爆款模式，先写出内容大纲：
        1. 标题（写 3 个备选，选最强的）
        2. 开头钩子（用什么方式在 3 秒内抓住注意力）
        3. 正文结构（分几段、每段核心信息是什么）
        4. 情绪节奏（哪里制造共鸣、哪里制造转折、哪里升华）
        5. 结尾互动（如何自然引导读者参与）

        ## 步骤 3：正文创作

        按大纲展开写作。创作时注意：
        - 每段必须有新信息或新视角，删掉所有废话
        - 用具体案例/数据/步骤替代空洞描述
        - 语言风格匹配 {target_platform} 平台调性
        - 加入你自己的独特视角，不要写搜索引擎第一页就能找到的内容

        ## 步骤 4：质量自检

        用 6 维度评分（1-10）自检，每项目标 ≥7：
        钩子力、信息密度、情绪节奏、可操作性、原创视角、互动设计。
        如果任何维度 <7，修改后再提交。

        ## 输出

        按 backstory 中定义的 JSON 格式输出，必须包含 quality_self_check 和 viral_references。
        """

        # 注入用户口味偏好
        if taste_context:
            create_description += f"""

        ## 用户口味偏好（必须遵循）

        {taste_context}

        **重要**：以上偏好来自用户的历史反馈和数据分析，创作时必须优先满足这些偏好。
        如果偏好与爆款模式冲突，优先遵循用户偏好。
        """

        # 注入修订反馈（第 2+ 轮）
        if revision_feedback:
            create_description += f"""

        ## 上一轮审核反馈（请根据反馈修改）

        {revision_feedback}

        **重要**：请针对以上问题逐一修改，保留原稿的优点。
        """

        create_task = Task(
            description=create_description,
            expected_output="JSON 格式的内容草稿，包含标题、正文、摘要、标签、风格说明等",
            agent=agents[0],  # ContentCreator
            async_execution=False,
        )

        # 任务 2：内容审核（独立）
        review_description = f"""
        审核上一步产出的内容草稿。

        **目标平台**: {target_platform}
        **内容类型**: {content_type}

        按你 backstory 中的审核流程依次执行：
        1. 爆款对标验证（一票否决）
        2. 6 维度质量评分（对照创作者的 quality_self_check）
        3. 合规检查（违禁词检测）
        4. 平台适配检查

        重点关注：
        - 创作者自评分数是否虚高（差距 >2 分需标注）
        - 信息密度：能否删掉 20%+ 不影响理解？
        - 原创视角：是搜索引擎第一页的内容还是有独特洞察？

        按 backstory 中定义的 JSON 格式输出审核报告。
        """

        if self.enable_human_review:
            review_description += "\n\n**重要**：此任务需要人工审核，请在完成初步审核后等待人工确认。"

        review_task = Task(
            description=review_description,
            expected_output="JSON 格式的审核报告，包含审核结果、评分、问题、建议、修正后内容等",
            agent=agents[1],  # ContentReviewer
            async_execution=False,
            context=[create_task],
        )

        return [create_task, review_task]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        """
        验证输入参数。

        Args:
            inputs: Crew 输入

        Returns:
            (是否有效, 错误信息) 元组
        """
        topic = inputs.inputs.get("topic")
        if not topic:
            return False, "topic 参数不能为空"

        valid_platforms = [
            "wechat",
            "xiaohongshu",
            "douyin",
            "bilibili",
            "zhihu",
            "weibo",
        ]
        target_platform = inputs.inputs.get("target_platform", "xiaohongshu")
        if target_platform not in valid_platforms:
            return False, f"target_platform 必须是: {', '.join(valid_platforms)}"

        return True, None

    MAX_REVISION_ITERATIONS = 3

    def execute(self, inputs: CrewInput) -> CrewResult:
        """
        执行内容生产线（带修订循环和 Taste 注入）。

        流程：
        1. 从 TasteEngine 获取 taste context
        2. 注入 taste context 到创作任务
        3. 执行 create → review
        4. 如果 reviewer 返回 needs_revision，注入反馈后重试（最多 3 轮）
        5. 记录反馈到 TasteEngine

        Args:
            inputs: Crew 输入

        Returns:
            ContentCrewResult 实例
        """
        # 验证输入
        is_valid, error_msg = self.validate_inputs(inputs)
        if not is_valid:
            return ContentCrewResult(
                status=CrewStatus.FAILED,
                errors=[error_msg],
            )

        # 获取 taste context
        taste_engine = TasteEngine()
        target_platform = inputs.inputs.get("target_platform", "xiaohongshu")
        taste_context = taste_engine.get_taste_prompt(platform=target_platform)

        # 修订循环
        iteration = 0
        last_review_feedback = ""
        final_result = None

        while iteration < self.MAX_REVISION_ITERATIONS:
            iteration += 1

            # 注入 taste context 和修订反馈到 inputs
            enriched_inputs = self._enrich_inputs(
                inputs, taste_context, last_review_feedback, iteration
            )

            # 调用父类的 execute 方法
            result = super().execute(enriched_inputs)

            # 转换为 ContentCrewResult
            content_result = self._to_content_result(result)
            final_result = content_result

            # 检查审核结果
            review_report = content_result.review_report
            if review_report:
                review_result = review_report.get("result", "")

                if review_result == "approved":
                    logger.info(f"Content approved on iteration {iteration}")
                    break

                if review_result == "needs_revision" and iteration < self.MAX_REVISION_ITERATIONS:
                    # 构建修订反馈
                    issues = review_report.get("issues", [])
                    suggestions = review_report.get("suggestions", [])
                    last_review_feedback = self._format_revision_feedback(
                        issues, suggestions, review_report
                    )
                    logger.info(
                        f"Iteration {iteration}: needs revision, "
                        f"{len(issues)} issues, retrying..."
                    )
                    continue

            # approved, rejected, 或无 review_report — 停止
            break

        if final_result:
            final_result.metadata = final_result.metadata or {}
            final_result.metadata["iterations"] = iteration
            final_result.metadata["taste_phase"] = taste_engine.profile.phase

        return final_result

    def _enrich_inputs(
        self,
        inputs: CrewInput,
        taste_context: str,
        revision_feedback: str,
        iteration: int,
    ) -> CrewInput:
        """注入 taste context 和修订反馈到 inputs."""
        enriched = CrewInput()
        enriched.inputs = {**inputs.inputs}
        enriched.metadata = {**inputs.metadata, "iteration": iteration}
        enriched.inputs["taste_context"] = taste_context
        enriched.inputs["revision_feedback"] = revision_feedback
        return enriched

    def _format_revision_feedback(
        self,
        issues: list,
        suggestions: list,
        review_report: dict,
    ) -> str:
        """格式化修订反馈."""
        lines = []
        if issues:
            lines.append("### 需要修改的问题：")
            for i, issue in enumerate(issues, 1):
                if isinstance(issue, dict):
                    lines.append(f"{i}. [{issue.get('type', '问题')}] {issue.get('description', str(issue))}")
                else:
                    lines.append(f"{i}. {issue}")
        if suggestions:
            lines.append("\n### 优化建议：")
            for s in suggestions:
                lines.append(f"- {s}")
        if score := review_report.get("overall_score"):
            lines.append(f"\n当前评分：{score}/100")
        return "\n".join(lines)

    def _to_content_result(self, result: CrewResult) -> ContentCrewResult:
        """将 CrewResult 转换为 ContentCrewResult."""
        content_draft = None
        review_report = None
        research_findings = None
        viral_reference_report = None

        if result.data:
            if "task_outputs" in result.data:
                outputs = result.data["task_outputs"]
                if len(outputs) >= 1:
                    research_findings = outputs[0]
                if len(outputs) >= 2:
                    content_draft = outputs[1]
                if len(outputs) >= 3:
                    review_report = outputs[2]
            else:
                content_draft = result.data.get("content_draft")
                review_report = result.data.get("review_report")
                research_findings = result.data.get("research_findings")
                viral_reference_report = result.data.get("viral_reference_report")

        if content_draft and "viral_references" in content_draft and not viral_reference_report:
            viral_reference_report = {
                "viral_references": content_draft.get("viral_references", []),
                "passed": len(content_draft.get("viral_references", [])) >= 5,
                "count": len(content_draft.get("viral_references", [])),
            }

        return ContentCrewResult(
            status=result.status,
            research_findings=research_findings,
            content_draft=content_draft,
            review_report=review_report,
            viral_reference_report=viral_reference_report,
            execution_time=result.execution_time,
            error=result.error,
            metadata=result.metadata,
            data=result.data,
        )
