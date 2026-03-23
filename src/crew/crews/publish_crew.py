"""
Publish Crew Module

发布线 Crew：平台适配 → 并行发布。
"""

from typing import Any

from crewai import Process, Task
from loguru import logger

from src.agents import PlatformAdapter, PlatformPublisher
from src.agents.platform_adapter import Platform
from src.agents.platform_publisher import PublishBatch

from .base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus


class PublishCrewInput(CrewInput):
    """
    PublishCrew 专用输入数据类。

    Args:
        content_id: 内容 ID
        content_draft: 内容草稿数据
        target_platforms: 目标平台列表
        schedule_time: 定时发布时间（可选）
        enable_retry: 是否启用失败重试
    """

    def __init__(
        self,
        content_id: str,
        content_draft: dict[str, Any],
        target_platforms: list[str],
        schedule_time: str | None = None,
        enable_retry: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.inputs.update({
            "content_id": content_id,
            "content_draft": content_draft,
            "target_platforms": target_platforms,
            "schedule_time": schedule_time,
            "enable_retry": enable_retry,
        })
        self.metadata.update({
            "content_id": content_id,
            "platforms": target_platforms,
            "scheduled": schedule_time is not None,
        })


class PublishCrewResult(CrewResult):
    """
    PublishCrew 专用结果数据类。

    扩展自 CrewResult，添加发布特定的字段。
    """

    def __init__(
        self,
        status: CrewStatus,
        adapted_contents: dict[str, dict[str, Any]] | None = None,
        publish_records: list[dict[str, Any]] | None = None,
        **kwargs,
    ):
        super().__init__(status=status, **kwargs)
        self.adapted_contents = adapted_contents or {}
        self.publish_records = publish_records or []

        # 更新 data 字段
        if self.data is None:
            self.data = {}
        self.data.update({
            "adapted_contents": adapted_contents,
            "publish_records": publish_records,
            "summary": self._generate_summary(),
        })

    def _generate_summary(self) -> dict[str, Any]:
        """生成发布摘要。"""
        total = len(self.publish_records)
        successful = sum(1 for r in self.publish_records if r.get("status") == "published")
        failed = sum(1 for r in self.publish_records if r.get("status") == "failed")
        pending = total - successful - failed

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "pending": pending,
            "success_rate": f"{(successful / total * 100):.1f}%" if total > 0 else "0%",
        }

    @property
    def all_success(self) -> bool:
        """检查是否所有平台都发布成功。"""
        return all(r.get("status") == "published" for r in self.publish_records)

    @property
    def successful_platforms(self) -> list[str]:
        """获取发布成功的平台列表。"""
        return [r.get("platform") for r in self.publish_records if r.get("status") == "published"]

    @property
    def failed_platforms(self) -> list[str]:
        """获取发布失败的平台列表。"""
        return [r.get("platform") for r in self.publish_records if r.get("status") == "failed"]


class PublishCrew(BaseCrew):
    """
    发布线 Crew。

    流程：PlatformAdapter → [各平台 Publisher 并行]

    职责：
    - 将内容适配到各平台格式
    - 并行发布到多个平台
    - 管理发布状态和重试
    """

    def __init__(
        self,
        verbose: bool = True,
        process: Process = Process.sequential,
        memory: bool = False,
        max_rpm: int | None = 10,
        enable_retry: bool = True,
        max_retries: int = 3,
        llm: str | None = None,
    ):
        """
        初始化 PublishCrew。

        Args:
            verbose: 是否输出详细日志
            process: 执行流程类型
            memory: 是否使用记忆
            max_rpm: 每分钟最大执行次数（限制发布速率）
            enable_retry: 是否启用失败重试
            max_retries: 最大重试次数
            llm: LLM 模型名称
        """
        super().__init__(
            verbose=verbose,
            process=process,
            memory=memory,
            max_rpm=max_rpm,
        )
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.llm = llm
        self._adapter_agent: Any | None = None
        self._publisher_agents: dict[str, Any] = {}

    def get_crew_name(self) -> str:
        """返回 Crew 名称。"""
        return "ContentPublishing"

    def get_description(self) -> str:
        """返回 Crew 描述。"""
        return "发布线：平台适配 → 并行发布"

    def get_agents(self) -> list[Any]:
        """
        返回 Crew 的 Agent 列表。

        动态创建平台适配师和各平台发布员。

        Returns:
            Agent 列表 [PlatformAdapter, PlatformPublisher...]
        """
        agents = []

        # 创建平台适配师
        if self._adapter_agent is None:
            self._adapter_agent = PlatformAdapter.create(
                verbose=self.verbose,
                llm=self.llm,
            )
        agents.append(self._adapter_agent)

        # 创建各平台发布员（按需创建）
        for platform in Platform:
            if platform.value not in self._publisher_agents:
                publisher = PlatformPublisher.create(
                    verbose=self.verbose,
                    allow_delegation=False,
                    human_input=False,
                    llm=self.llm,
                )
                self._publisher_agents[platform.value] = publisher
            agents.append(self._publisher_agents[platform.value])

        return agents

    def get_tasks(self, inputs: CrewInput) -> list[Any]:
        """
        根据 Crew 输入返回任务列表。

        Args:
            inputs: Crew 输入

        Returns:
            Task 列表 [adapt_task, publish_tasks...]
        """
        agents = self.get_agents()
        target_platforms = inputs.inputs.get("target_platforms", ["xiaohongshu"])
        content_draft = inputs.inputs.get("content_draft", {})
        schedule_time = inputs.inputs.get("schedule_time")

        # 构建平台枚举列表
        platform_enum_list = []
        for platform_str in target_platforms:
            try:
                platform_enum = Platform(platform_str)
                platform_enum_list.append(platform_enum)
            except ValueError:
                logger.warning(f"Unknown platform: {platform_str}")

        if not platform_enum_list:
            platform_enum_list = [Platform.XIAOHONGSHU]

        # 任务 1：平台适配
        adapt_task = Task(
            description=f"""
            将内容适配到以下平台的格式和风格要求：

            **目标平台**: {', '.join([p.value for p in platform_enum_list])}

            **原始内容**:
            - 标题: {content_draft.get('title', '')}
            - 摘要: {content_draft.get('summary', '')}
            - 正文: {content_draft.get('content', '')[:200]}...
            - 标签: {content_draft.get('tags', [])}

            请为每个目标平台生成适配后的内容，包括：
            1. 符合平台长度要求的标题
            2. 适配后的正文内容
            3. 平台特定的标签
            4. 封面图建议

            输出格式：JSON 格式，键为平台名称，值为适配后的内容：
            {{
                "xiaohongshu": {{
                    "title": "...",
                    "content": "...",
                    "summary": "...",
                    "tags": [...],
                    "cover_image": "..."
                }},
                "weibo": {{ ... }}
            }}
            """,
            expected_output=f"JSON 格式的适配内容，包含 {len(platform_enum_list)} 个平台的版本",
            agent=agents[0],  # PlatformAdapter
            async_execution=False,
        )

        # 任务 2-N：并行发布到各平台
        publish_tasks = []
        agent_idx = 1  # 适配师之后是发布员

        for platform_enum in platform_enum_list:
            platform_str = platform_enum.value

            publish_task = Task(
                description=f"""
                将适配后的内容发布到 {platform_str} 平台。

                **平台**: {platform_str}
                **定时发布**: {schedule_time if schedule_time else '立即发布'}

                请执行以下步骤：
                1. 获取 {platform_str} 平台的适配内容
                2. 调用平台 API 进行发布
                3. 记录发布结果和 URL
                4. 处理发布异常

                输出格式：JSON 格式的发布记录：
                {{
                    "content_id": "...",
                    "platform": "{platform_str}",
                    "status": "published",
                    "published_url": "...",
                    "published_at": "...",
                    "error_message": null
                }}
                """,
                expected_output="JSON 格式的发布记录，包含发布状态、URL 等信息",
                agent=agents[agent_idx],
                async_execution=True,  # 并行执行
                context=[adapt_task],
            )

            publish_tasks.append(publish_task)
            agent_idx += 1

        return [adapt_task, *publish_tasks]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        """
        验证输入参数。

        Args:
            inputs: Crew 输入

        Returns:
            (是否有效, 错误信息) 元组
        """
        content_id = inputs.inputs.get("content_id")
        if not content_id:
            return False, "content_id 参数不能为空"

        content_draft = inputs.inputs.get("content_draft")
        if not content_draft:
            return False, "content_draft 参数不能为空"

        if not content_draft.get("title"):
            return False, "content_draft 必须包含 title 字段"

        if not content_draft.get("content"):
            return False, "content_draft 必须包含 content 字段"

        target_platforms = inputs.inputs.get("target_platforms", [])
        if not target_platforms:
            return False, "target_platforms 参数不能为空"

        valid_platforms = [p.value for p in Platform]
        for platform in target_platforms:
            if platform not in valid_platforms:
                return False, f"不支持的平台: {platform}"

        return True, None

    def pre_execute(self, inputs: CrewInput) -> None:
        """
        执行前钩子。

        Args:
            inputs: Crew 输入
        """
        super().pre_execute(inputs)
        content_id = inputs.inputs.get("content_id", "unknown")
        platforms = inputs.inputs.get("target_platforms", [])
        logger.info(f"[{self.get_crew_name()}] Publishing content {content_id} to {len(platforms)} platforms")

    def post_execute(self, result: CrewResult) -> CrewResult:
        """
        执行后钩子。

        Args:
            result: 执行结果

        Returns:
            可能被修改后的结果
        """
        super().post_execute(result)

        if result.is_success():
            # 记录成功的平台
            if result.data and "publish_records" in result.data:
                successful = [
                    r["platform"]
                    for r in result.data["publish_records"]
                    if r.get("status") == "published"
                ]
                logger.info(f"[{self.get_crew_name()}] Successfully published to: {', '.join(successful)}")

        return result

    def _parse_outputs(self, outputs: Any) -> dict[str, Any]:
        """
        解析 Crew 输出。

        Args:
            outputs: 原始输出

        Returns:
            解析后的数据字典
        """
        result = super()._parse_outputs(outputs)

        adapted_contents = {}
        publish_records = []

        if hasattr(outputs, "tasks_output"):
            tasks_output = outputs.tasks_output

            # 第一个任务是适配任务
            if len(tasks_output) > 0:
                adapted = self._extract_task_output(tasks_output[0])
                if isinstance(adapted, dict):
                    adapted_contents = adapted

            # 后续任务是发布任务
            for _i, task_output in enumerate(tasks_output[1:], start=1):
                record = self._extract_task_output(task_output)
                if isinstance(record, dict):
                    publish_records.append(record)

        result["adapted_contents"] = adapted_contents
        result["publish_records"] = publish_records

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
        执行 Crew 并返回 PublishCrewResult。

        Args:
            inputs: Crew 输入

        Returns:
            PublishCrewResult 执行结果
        """
        result = super().execute(inputs)

        # 转换为 PublishCrewResult
        parsed = self._parse_outputs(result.raw_outputs)

        return PublishCrewResult(
            status=result.status,
            data=result.data,
            error=result.error,
            raw_outputs=result.raw_outputs,
            execution_time=result.execution_time,
            metadata=result.metadata,
            timestamp=result.timestamp,
            adapted_contents=parsed.get("adapted_contents", {}),
            publish_records=parsed.get("publish_records", []),
        )

    @classmethod
    def create(
        cls,
        enable_retry: bool = True,
        max_retries: int = 3,
        llm: str | None = None,
        **kwargs,
    ) -> "PublishCrew":
        """
        便捷方法：创建 PublishCrew 实例。

        Args:
            enable_retry: 是否启用失败重试
            max_retries: 最大重试次数
            llm: LLM 模型名称
            **kwargs: 其他配置参数

        Returns:
            PublishCrew 实例
        """
        return cls(
            enable_retry=enable_retry,
            max_retries=max_retries,
            llm=llm,
            **kwargs,
        )

    def create_publish_batch(
        self,
        content_id: str,
        platforms: list[str],
    ) -> PublishBatch:
        """
        创建发布批次。

        Args:
            content_id: 内容 ID
            platforms: 平台列表

        Returns:
            PublishBatch 实例
        """
        platform_enums = []
        for platform_str in platforms:
            try:
                platform_enums.append(Platform(platform_str))
            except ValueError:
                logger.warning(f"Unknown platform: {platform_str}")

        return PublishBatch(content_id=content_id, platforms=platform_enums)
