"""
Hotspot Detection Crew Module

热点探测 Crew：监控多平台热点话题，生成热点报告。
"""

import json
from typing import Any

from crewai import Process, Task

from src.agents import TopicResearcher
from src.tools import hot_search_tool, trend_analysis_tool

from .base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus


class HotspotDetectionInput(CrewInput):
    """
    HotspotDetectionCrew 专用输入数据类。

    Args:
        keywords: 关键词列表
        platforms: 目标平台列表
        limit: 每个平台返回的热点数量上限
    """

    def __init__(
        self,
        keywords: list[str],
        platforms: list[str] | None = None,
        limit: int = 20,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.inputs.update({
            "keywords": keywords,
            "platforms": platforms or ["weibo", "xiaohongshu", "douyin", "bilibili", "zhihu"],
            "limit": limit,
        })
        self.metadata.update({
            "keywords": keywords,
            "platform_count": len(platforms) if platforms else 5,
        })


class HotspotDetectionResult(CrewResult):
    """
    HotspotDetectionCrew 专用结果数据类。

    扩展自 CrewResult，添加热点探测特定的字段。
    """

    def __init__(
        self,
        status: CrewStatus,
        hot_topics: list[dict[str, Any]] | None = None,
        trend_report: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(status=status, **kwargs)
        self.hot_topics = hot_topics or []
        self.trend_report = trend_report

        if self.data is None:
            self.data = {}
        self.data.update({
            "hot_topics": self.hot_topics,
            "trend_report": self.trend_report,
        })

    @property
    def topic_count(self) -> int:
        """返回发现的热点话题数量。"""
        return len(self.hot_topics)


class HotspotDetectionCrew(BaseCrew):
    """
    热点探测 Crew。

    流程：TopicResearcher 执行多平台热点搜索和趋势分析

    职责：
    - 监控多平台热点话题
    - 分析关键词趋势
    - 生成热点报告
    """

    def __init__(
        self,
        verbose: bool = True,
        process: Process = Process.sequential,
        memory: bool = True,
        max_rpm: int | None = None,
        llm: str | None = None,
    ):
        super().__init__(
            verbose=verbose,
            process=process,
            memory=memory,
            max_rpm=max_rpm,
        )
        self.llm = llm
        self._search_tools = [hot_search_tool, trend_analysis_tool]

    def get_crew_name(self) -> str:
        return "HotspotDetection"

    def get_description(self) -> str:
        return "热点探测：多平台热点监控 + 趋势分析"

    def get_agents(self) -> list[Any]:
        researcher = TopicResearcher.create(
            tools=self._search_tools,
            verbose=self.verbose,
            llm=self.llm,
        )
        return [researcher]

    def get_tasks(self, inputs: CrewInput) -> list[Any]:
        agents = self.get_agents()

        keywords = inputs.inputs.get("keywords", [])
        platforms = inputs.inputs.get("platforms", [])
        limit = inputs.inputs.get("limit", 20)

        # Task 1: 多平台热点搜索
        search_task = Task(
            description=f"""
            在以下平台搜索热点话题：

            **目标平台**: {', '.join(platforms)}
            **关键词**: {', '.join(keywords)}
            **每平台上限**: {limit}

            执行步骤：
            1. 对每个平台调用 hot_search 工具获取热门话题
            2. 使用 trend_analysis 工具分析关键词趋势
            3. 按热度排序，筛选与关键词相关的热点
            4. 合并去重，生成综合热点列表

            输出格式：JSON，包含：
            - hot_topics: 热点话题列表，每项包含：
              - title: 话题标题
              - platform: 来源平台
              - heat: 热度值
              - category: 分类
              - url: 原始链接
              - relevance_score: 与关键词的相关度 (0-100)
            - trend_report: 趋势分析，包含：
              - rising_keywords: 上升趋势关键词
              - declining_keywords: 下降趋势关键词
              - predictions: 趋势预测
            """,
            expected_output="JSON 格式的热点报告，包含 hot_topics 列表和 trend_report",
            agent=agents[0],
            async_execution=False,
        )

        return [search_task]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        keywords = inputs.inputs.get("keywords", [])
        if not keywords:
            return False, "keywords 参数不能为空"

        valid_platforms = ["weibo", "xiaohongshu", "douyin", "bilibili", "zhihu"]
        platforms = inputs.inputs.get("platforms", [])
        for p in platforms:
            if p not in valid_platforms:
                return False, f"不支持的平台: {p}"

        return True, None

    def _parse_outputs(self, outputs: Any) -> dict[str, Any]:
        result = super()._parse_outputs(outputs)

        if hasattr(outputs, "tasks_output") and outputs.tasks_output:
            task_output = outputs.tasks_output[0]
            parsed = self._extract_task_output(task_output)
            result["hot_topics"] = parsed.get("hot_topics", [])
            result["trend_report"] = parsed.get("trend_report")

        return result

    def _extract_task_output(self, task_output: Any) -> dict[str, Any]:
        if hasattr(task_output, "raw"):
            output_str = task_output.raw
        elif hasattr(task_output, "result"):
            output_str = task_output.result
        else:
            output_str = str(task_output)

        try:
            return json.loads(output_str)
        except (json.JSONDecodeError, TypeError):
            return {"output": output_str}

    def execute(self, inputs: CrewInput) -> HotspotDetectionResult:
        result = super().execute(inputs)

        parsed = self._parse_outputs(result.raw_outputs) if result.raw_outputs else {}

        return HotspotDetectionResult(
            status=result.status,
            data=result.data,
            error=result.error,
            raw_outputs=result.raw_outputs,
            execution_time=result.execution_time,
            metadata=result.metadata,
            timestamp=result.timestamp,
            hot_topics=parsed.get("hot_topics", []),
            trend_report=parsed.get("trend_report"),
        )

    @classmethod
    def create(cls, llm: str | None = None, **kwargs) -> "HotspotDetectionCrew":
        return cls(llm=llm, **kwargs)
