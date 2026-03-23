"""
Content Crew Module

内容生产线 Crew：选题研究 → 内容创作 → 内容审核。
"""

from typing import Any

from crewai import Process, Task

from src.agents import ContentReviewer, ContentWriter, TopicResearcher
from src.tools import competitor_analysis_tool, hot_search_tool, trend_analysis_tool

from .base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus


class ContentCrewInput(CrewInput):
    """
    ContentCrew 专用输入数据类。

    Args:
        industry: 行业领域
        keywords: 关键词列表
        target_platform: 目标平台
        content_type: 内容类型（article, video, image_post）
        research_depth: 研究深度（basic, standard, deep）
        enable_human_review: 是否启用人工审核
    """

    def __init__(
        self,
        industry: str,
        keywords: list[str],
        target_platform: str = "xiaohongshu",
        content_type: str = "article",
        research_depth: str = "standard",
        enable_human_review: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.inputs.update({
            "industry": industry,
            "keywords": keywords,
            "target_platform": target_platform,
            "content_type": content_type,
            "research_depth": research_depth,
            "enable_human_review": enable_human_review,
        })
        self.metadata.update({
            "industry": industry,
            "content_type": content_type,
            "research_depth": research_depth,
        })


class ContentCrewResult(CrewResult):
    """
    ContentCrew 专用结果数据类。

    扩展自 CrewResult，添加内容生产特定的字段。
    """

    def __init__(
        self,
        status: CrewStatus,
        topic_report: dict[str, Any] | None = None,
        content_draft: dict[str, Any] | None = None,
        review_report: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(status=status, **kwargs)
        self.topic_report = topic_report
        self.content_draft = content_draft
        self.review_report = review_report

        # 更新 data 字段
        if self.data is None:
            self.data = {}
        self.data.update({
            "topic_report": topic_report,
            "content_draft": content_draft,
            "review_report": review_report,
        })

    @property
    def is_approved(self) -> bool:
        """检查内容是否通过审核。"""
        if self.review_report:
            return self.review_report.get("result") == "approved"
        return False


class ContentCrew(BaseCrew):
    """
    内容生产线 Crew。

    流程：TopicResearcher → ContentWriter → ContentReviewer

    职责：
    - 研究热点和选题
    - 创作原创内容
    - 审核内容质量和合规性
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
        self.llm = llm

        # 初始化工具
        self._search_tools = [
            hot_search_tool,
            competitor_analysis_tool,
            trend_analysis_tool,
        ]

    def get_crew_name(self) -> str:
        """返回 Crew 名称。"""
        return "ContentProduction"

    def get_description(self) -> str:
        """返回 Crew 描述。"""
        return "内容生产线：选题研究 → 内容创作 → 内容审核"

    def get_agents(self) -> list[Any]:
        """
        返回 Crew 的 Agent 列表。

        Returns:
            Agent 列表 [TopicResearcher, ContentWriter, ContentReviewer]
        """
        # 创建选题研究员
        topic_researcher = TopicResearcher.create(
            tools=self._search_tools,
            verbose=self.verbose,
            llm=self.llm,
        )

        # 创建内容创作者
        content_writer = ContentWriter.create(
            verbose=self.verbose,
            llm=self.llm,
        )

        # 创建内容审核员
        content_reviewer = ContentReviewer.create(
            verbose=self.verbose,
            human_input=self.enable_human_review,
            allow_delegation=False,
            llm=self.llm,
        )

        return [topic_researcher, content_writer, content_reviewer]

    def get_tasks(self, inputs: CrewInput) -> list[Any]:
        """
        根据 Crew 输入返回任务列表。

        Args:
            inputs: Crew 输入

        Returns:
            Task 列表 [research_task, write_task, review_task]
        """
        agents = self.get_agents()

        industry = inputs.inputs.get("industry", "")
        keywords = inputs.inputs.get("keywords", [])
        target_platform = inputs.inputs.get("target_platform", "xiaohongshu")
        content_type = inputs.inputs.get("content_type", "article")
        research_depth = inputs.inputs.get("research_depth", "standard")

        # 任务 1：选题研究
        research_task = Task(
            description=f"""
            根据以下要求进行选题研究：

            **行业领域**: {industry}
            **关键词**: {', '.join(keywords)}
            **目标平台**: {target_platform}
            **研究深度**: {research_depth}

            请执行以下步骤：
            1. 使用 hot_search_tool 搜索相关热点话题
            2. 使用 competitor_analysis_tool 分析竞品内容
            3. 使用 trend_analysis_tool 分析关键词趋势
            4. 综合分析，生成 3-5 个高潜力选题建议

            输出格式：JSON 格式的选题报告，包含：
            - title: 选题标题
            - category: 内容分类
            - potential_score: 潜力评分 (0-100)
            - reasoning: 选择理由
            - target_audience: 目标受众
            - suggested_angle: 建议切入点
            - keywords: 相关关键词列表
            """,
            expected_output="JSON 格式的选题报告，包含 3-5 个选题建议及其详细分析",
            agent=agents[0],  # TopicResearcher
            async_execution=False,
        )

        # 任务 2：内容创作
        write_task = Task(
            description=f"""
            根据选题报告创作{content_type}类型内容：

            **目标平台**: {target_platform}
            **内容类型**: {content_type}

            请执行以下步骤：
            1. 从选题报告中选择潜力最高的选题
            2. 根据平台特性创作内容
            3. 生成吸引人的标题
            4. 撰写正文内容
            5. 生成合适的标签

            输出格式：JSON 格式的内容草稿，包含：
            - title: 内容标题
            - content: 正文内容（Markdown 格式）
            - summary: 内容摘要
            - tags: 标签列表
            - cover_image_prompt: 封面图提示词（可选）
            - platform: 目标平台
            """,
            expected_output="JSON 格式的内容草稿，包含标题、正文、摘要、标签等完整内容",
            agent=agents[1],  # ContentWriter
            async_execution=False,
            context=[research_task],
        )

        # 任务 3：内容审核
        review_description = f"""
        审核以下内容草稿的质量和合规性：

        **目标平台**: {target_platform}

        请执行以下检查：
        1. 质量检查：内容结构、逻辑性、专业性
        2. 合规检查：法律法规、平台规则、敏感内容
        3. 传播评估：标题吸引力、内容传播潜力
        4. 提供具体的优化建议

        输出格式：JSON 格式的审核报告，包含：
        - result: 审核结果 (approved/needs_revision/rejected)
        - overall_score: 综合评分 (0-100)
        - quality_score: 质量评分 (0-100)
        - compliance_score: 合规评分 (0-100)
        - spread_score: 传播评分 (0-100)
        - issues: 问题列表
        - suggestions: 优化建议列表
        - highlights: 内容亮点列表
        - reviewer_notes: 审核员备注
        """

        if self.enable_human_review:
            review_description += "\n\n**重要**：此任务需要人工审核，请在完成初步审核后等待人工确认。"

        review_task = Task(
            description=review_description,
            expected_output="JSON 格式的审核报告，包含审核结果、评分、问题、建议等",
            agent=agents[2],  # ContentReviewer
            async_execution=False,
            context=[write_task],
        )

        return [research_task, write_task, review_task]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        """
        验证输入参数。

        Args:
            inputs: Crew 输入

        Returns:
            (是否有效, 错误信息) 元组
        """
        industry = inputs.inputs.get("industry")
        if not industry:
            return False, "industry 参数不能为空"

        keywords = inputs.inputs.get("keywords", [])
        if not keywords:
            return False, "keywords 参数不能为空"

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
            return False, f"不支持的 target_platform: {target_platform}"

        valid_content_types = ["article", "video", "image_post"]
        content_type = inputs.inputs.get("content_type", "article")
        if content_type not in valid_content_types:
            return False, f"不支持的 content_type: {content_type}"

        return True, None

    def _parse_outputs(self, outputs: Any) -> dict[str, Any]:
        """
        解析 Crew 输出。

        Args:
            outputs: 原始输出

        Returns:
            解析后的数据字典
        """
        result = super()._parse_outputs(outputs)

        # 尝试提取各个阶段的输出
        if hasattr(outputs, "tasks_output"):
            tasks_output = outputs.tasks_output

            # 提取选题报告
            if len(tasks_output) > 0:
                result["topic_report"] = self._extract_task_output(tasks_output[0])

            # 提取内容草稿
            if len(tasks_output) > 1:
                result["content_draft"] = self._extract_task_output(tasks_output[1])

            # 提取审核报告
            if len(tasks_output) > 2:
                result["review_report"] = self._extract_task_output(tasks_output[2])

        return result

    def _extract_task_output(self, task_output: Any) -> dict[str, Any]:
        """
        提取任务输出。

        Args:
            task_output: 任务输出

        Returns:
            解析后的任务输出
        """
        if hasattr(task_output, "raw"):
            output_str = task_output.raw
        elif hasattr(task_output, "result"):
            output_str = task_output.result
        else:
            output_str = str(task_output)

        # 尝试解析 JSON
        import json

        try:
            return json.loads(output_str)
        except (json.JSONDecodeError, TypeError):
            return {"output": output_str}

    def execute(self, inputs: CrewInput) -> CrewResult:
        """
        执行 Crew 并返回 ContentCrewResult。

        Args:
            inputs: Crew 输入

        Returns:
            ContentCrewResult 执行结果
        """
        result = super().execute(inputs)

        # 转换为 ContentCrewResult
        parsed = self._parse_outputs(result.raw_outputs)

        return ContentCrewResult(
            status=result.status,
            data=result.data,
            error=result.error,
            raw_outputs=result.raw_outputs,
            execution_time=result.execution_time,
            metadata=result.metadata,
            timestamp=result.timestamp,
            topic_report=parsed.get("topic_report"),
            content_draft=parsed.get("content_draft"),
            review_report=parsed.get("review_report"),
        )

    @classmethod
    def create(
        cls,
        enable_human_review: bool = True,
        llm: str | None = None,
        **kwargs,
    ) -> "ContentCrew":
        """
        便捷方法：创建 ContentCrew 实例。

        Args:
            enable_human_review: 是否启用人工审核
            llm: LLM 模型名称
            **kwargs: 其他配置参数

        Returns:
            ContentCrew 实例
        """
        return cls(
            enable_human_review=enable_human_review,
            llm=llm,
            **kwargs,
        )
