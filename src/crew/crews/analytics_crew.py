"""
Analytics Crew Module

分析线 Crew：数据采集 → 数据分析 → 优化建议。
"""

from datetime import datetime
from typing import Any

from crewai import Process, Task
from loguru import logger

from src.agents import DataAnalyst
from src.agents.platform_adapter import Platform
from src.tools import analytics_report_tool, data_collect_tool

from .base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus


class AnalyticsCrewInput(CrewInput):
    """
    AnalyticsCrew 专用输入数据类。

    Args:
        content_ids: 已发布内容 ID 列表
        time_range: 时间范围（24h, 7d, 30d）
        platforms: 平台列表（可选）
        metrics: 指标列表（可选）
        report_format: 报告格式（json, markdown）
    """

    def __init__(
        self,
        content_ids: list[str],
        time_range: str = "7d",
        platforms: list[str] | None = None,
        metrics: list[str] | None = None,
        report_format: str = "json",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.inputs.update({
            "content_ids": content_ids,
            "time_range": time_range,
            "platforms": platforms or ["xiaohongshu"],
            "metrics": metrics or ["views", "likes", "comments", "shares", "engagement_rate"],
            "report_format": report_format,
        })
        self.metadata.update({
            "time_range": time_range,
            "content_count": len(content_ids),
            "report_format": report_format,
        })


class AnalyticsCrewResult(CrewResult):
    """
    AnalyticsCrew 专用结果数据类。

    扩展自 CrewResult，添加分析特定的字段。
    """

    def __init__(
        self,
        status: CrewStatus,
        collected_data: list[dict[str, Any]] | None = None,
        analysis_report: dict[str, Any] | None = None,
        recommendations: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(status=status, **kwargs)
        self.collected_data = collected_data or []
        self.analysis_report = analysis_report or {}
        self.recommendations = recommendations or []

        # 更新 data 字段
        if self.data is None:
            self.data = {}
        self.data.update({
            "collected_data": collected_data,
            "analysis_report": analysis_report,
            "recommendations": recommendations,
        })

    @property
    def top_performers(self) -> list[dict[str, Any]]:
        """获取表现最佳的内容列表。"""
        return self.analysis_report.get("top_performers", [])

    @property
    def underperformers(self) -> list[dict[str, Any]]:
        """获取表现不佳的内容列表。"""
        return self.analysis_report.get("underperformers", [])

    @property
    def key_findings(self) -> list[str]:
        """获取关键发现列表。"""
        return self.analysis_report.get("key_findings", [])

    def to_markdown_report(self) -> str:
        """生成 Markdown 格式的报告。"""
        lines = [
            "# Analytics Report",
            "",
            f"**Generated at**: {datetime.now().isoformat()}",
            "",
            "## Summary",
            self.analysis_report.get("summary", "No summary available."),
            "",
            "## Key Findings",
        ]

        for i, finding in enumerate(self.key_findings, 1):
            lines.append(f"{i}. {finding}")

        lines.extend([
            "",
            "## Top Performers",
        ])

        for item in self.top_performers[:5]:
            title = item.get("title", "N/A")
            views = item.get("views", 0)
            platform = item.get("platform", "unknown")
            lines.append(f"- **{title}** ({platform}): {views:,} views")

        lines.extend([
            "",
            "## Recommendations",
        ])

        for i, rec in enumerate(self.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)


class AnalyticsCrew(BaseCrew):
    """
    分析线 Crew。

    流程：DataAnalyst（采集）→ DataAnalyst（分析）→ DataAnalyst（建议）

    职责：
    - 采集各平台内容表现数据
    - 分析数据趋势和模式
    - 生成优化建议和策略调整
    """

    def __init__(
        self,
        verbose: bool = True,
        process: Process = Process.sequential,
        memory: bool = True,
        max_rpm: int | None = 30,
        llm: str | None = None,
    ):
        """
        初始化 AnalyticsCrew。

        Args:
            verbose: 是否输出详细日志
            process: 执行流程类型
            memory: 是否使用记忆
            max_rpm: 每分钟最大执行次数
            llm: LLM 模型名称
        """
        super().__init__(
            verbose=verbose,
            process=process,
            memory=memory,
            max_rpm=max_rpm,
        )
        self.llm = llm

        # 初始化工具
        self._analytics_tools = [
            data_collect_tool,
            analytics_report_tool,
        ]

        # 缓存采集的数据
        self._collected_data: list[dict[str, Any]] = []

    def get_crew_name(self) -> str:
        """返回 Crew 名称。"""
        return "ContentAnalytics"

    def get_description(self) -> str:
        """返回 Crew 描述。"""
        return "分析线：数据采集 → 数据分析 → 优化建议"

    def get_agents(self) -> list[Any]:
        """
        返回 Crew 的 Agent 列表。

        创建三个不同职责的数据分析师。

        Returns:
            Agent 列表 [DataCollector, DataAnalyzer, StrategyAdvisor]
        """
        # Agent 1：数据采集员
        data_collector = DataAnalyst.create(
            tools=self._analytics_tools,
            verbose=self.verbose,
            llm=self.llm,
        )
        # 设置采集员角色
        data_collector.role = "数据采集员"
        data_collector.goal = "准确、完整地采集各平台内容表现数据"

        # Agent 2：数据分析员
        data_analyzer = DataAnalyst.create(
            tools=self._analytics_tools,
            verbose=self.verbose,
            llm=self.llm,
        )
        data_analyzer.role = "数据分析员"
        data_analyzer.goal = "深入分析数据，发现规律和洞察"

        # Agent 3：策略顾问
        strategy_advisor = DataAnalyst.create(
            tools=self._analytics_tools,
            verbose=self.verbose,
            llm=self.llm,
        )
        strategy_advisor.role = "策略顾问"
        strategy_advisor.goal = "基于数据洞察，提供可操作的优化建议"

        return [data_collector, data_analyzer, strategy_advisor]

    def get_tasks(self, inputs: CrewInput) -> list[Any]:
        """
        根据 Crew 输入返回任务列表。

        Args:
            inputs: Crew 输入

        Returns:
            Task 列表 [collect_task, analyze_task, advise_task]
        """
        agents = self.get_agents()

        content_ids = inputs.inputs.get("content_ids", [])
        time_range = inputs.inputs.get("time_range", "7d")
        platforms = inputs.inputs.get("platforms", ["xiaohongshu"])
        metrics = inputs.inputs.get("metrics", [])
        report_format = inputs.inputs.get("report_format", "json")

        # 任务 1：数据采集
        collect_task = Task(
            description=f"""
            采集以下内容的性能数据：

            **内容 ID 列表**: {content_ids}
            **平台**: {', '.join(platforms)}
            **时间范围**: {time_range}
            **指标**: {', '.join(metrics)}

            请执行以下步骤：
            1. 使用 data_collect_tool 采集每条内容的数据
            2. 确保数据完整性
            3. 处理缺失数据和异常值

            输出格式：JSON 格式的数据列表，每项包含：
            {{
                "content_id": "...",
                "platform": "...",
                "metrics": {{
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "favorites": 0,
                    "engagement_rate": 0.0
                }},
                "collected_at": "..."
            }}
            """,
            expected_output=f"JSON 格式的数据列表，包含 {len(content_ids)} 条内容的数据",
            agent=agents[0],  # DataCollector
            async_execution=False,
        )

        # 任务 2：数据分析
        analyze_task = Task(
            description=f"""
            分析采集到的内容表现数据：

            **时间范围**: {time_range}
            **分析维度**: 趋势、对比、异常检测

            请执行以下分析：
            1. 计算各指标的平均值、中位数、标准差
            2. 识别表现最佳和最差的内容
            3. 分析不同平台的表现差异
            4. 检测数据异常和趋势变化
            5. 找出影响表现的关键因素

            输出格式：JSON 格式的分析报告，包含：
            {{
                "summary": "分析摘要",
                "metrics_summary": {{
                    "total_views": 0,
                    "avg_engagement_rate": 0.0,
                    "total_content": {len(content_ids)}
                }},
                "top_performers": [...],
                "underperformers": [...],
                "key_findings": [...],
                "trend_analysis": [...]
            }}
            """,
            expected_output="JSON 格式的分析报告，包含指标汇总、关键发现、趋势分析",
            agent=agents[1],  # DataAnalyzer
            async_execution=False,
            context=[collect_task],
        )

        # 任务 3：优化建议
        advise_task = Task(
            description=f"""
            基于数据分析结果，提供优化建议：

            **报告格式**: {report_format}

            请执行以下步骤：
            1. 回顾数据分析结果
            2. 识别改进机会
            3. 制定具体的优化策略
            4. 提供可操作的行动建议
            5. 预估改进效果

            建议应覆盖以下方面：
            - 内容创作优化
            - 发布时间优化
            - 平台策略调整
            - 标签和关键词优化
            - 互动策略改进

            输出格式：JSON 格式的建议报告，包含：
            {{
                "recommendations": [
                    {{
                        "category": "content|timing|platform|tag|engagement",
                        "priority": "high|medium|low",
                        "action": "具体行动",
                        "expected_impact": "预期影响",
                        "implementation_steps": ["步骤1", "步骤2"]
                    }}
                ],
                "quick_wins": ["快速见效的建议"],
                "long_term_strategy": ["长期策略建议"],
                "next_actions": ["下一步行动"]
            }}
            """,
            expected_output="JSON 格式的建议报告，包含分类建议、快速见效点、长期策略",
            agent=agents[2],  # StrategyAdvisor
            async_execution=False,
            context=[analyze_task],
        )

        return [collect_task, analyze_task, advise_task]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        """
        验证输入参数。

        Args:
            inputs: Crew 输入

        Returns:
            (是否有效, 错误信息) 元组
        """
        content_ids = inputs.inputs.get("content_ids", [])
        if not content_ids:
            return False, "content_ids 参数不能为空"

        time_range = inputs.inputs.get("time_range", "7d")
        valid_ranges = ["24h", "7d", "30d", "90d"]
        if time_range not in valid_ranges:
            return False, f"无效的 time_range: {time_range}，有效值: {', '.join(valid_ranges)}"

        platforms = inputs.inputs.get("platforms", [])
        valid_platforms = [p.value for p in Platform]
        for platform in platforms:
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
        content_ids = inputs.inputs.get("content_ids", [])
        time_range = inputs.inputs.get("time_range", "7d")
        logger.info(f"[{self.get_crew_name()}] Analyzing {len(content_ids)} content items over {time_range}")

    def post_execute(self, result: CrewResult) -> CrewResult:
        """
        执行后钩子。

        Args:
            result: 执行结果

        Returns:
            可能被修改后的结果
        """
        super().post_execute(result)

        if result.is_success() and result.data and "recommendations" in result.data:
                rec_count = len(result.data.get("recommendations", []))
                logger.info(f"[{self.get_crew_name()}] Generated {rec_count} recommendations")

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

        collected_data = []
        analysis_report = {}
        recommendations = []

        if hasattr(outputs, "tasks_output"):
            tasks_output = outputs.tasks_output

            # 任务 1：数据采集
            if len(tasks_output) > 0:
                collected = self._extract_task_output(tasks_output[0])
                if isinstance(collected, list):
                    collected_data = collected
                elif isinstance(collected, dict) and "results" in collected:
                    collected_data = collected["results"]

            # 任务 2：数据分析
            if len(tasks_output) > 1:
                analysis_report = self._extract_task_output(tasks_output[1])

            # 任务 3：优化建议
            if len(tasks_output) > 2:
                advise = self._extract_task_output(tasks_output[2])
                if isinstance(advise, dict):
                    recommendations = advise.get("recommendations", [])
                    # 也保存完整的建议报告
                    result["advise_report"] = advise

        result["collected_data"] = collected_data
        result["analysis_report"] = analysis_report
        result["recommendations"] = recommendations

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
        执行 Crew 并返回 AnalyticsCrewResult。

        Args:
            inputs: Crew 输入

        Returns:
            AnalyticsCrewResult 执行结果
        """
        result = super().execute(inputs)

        # 转换为 AnalyticsCrewResult
        parsed = self._parse_outputs(result.raw_outputs)

        return AnalyticsCrewResult(
            status=result.status,
            data=result.data,
            error=result.error,
            raw_outputs=result.raw_outputs,
            execution_time=result.execution_time,
            metadata=result.metadata,
            timestamp=result.timestamp,
            collected_data=parsed.get("collected_data", []),
            analysis_report=parsed.get("analysis_report", {}),
            recommendations=parsed.get("recommendations", []),
        )

    @classmethod
    def create(
        cls,
        llm: str | None = None,
        **kwargs,
    ) -> "AnalyticsCrew":
        """
        便捷方法：创建 AnalyticsCrew 实例。

        Args:
            llm: LLM 模型名称
            **kwargs: 其他配置参数

        Returns:
            AnalyticsCrew 实例
        """
        return cls(llm=llm, **kwargs)

    def get_quick_stats(self, content_ids: list[str]) -> dict[str, Any]:
        """
        快速获取内容统计。

        Args:
            content_ids: 内容 ID 列表

        Returns:
            快速统计数据
        """
        # 使用 data_collect_tool 快速采集
        import json

        results = []
        for content_id in content_ids:
            data_str = data_collect_tool(content_id=content_id, platform="xiaohongshu")
            try:
                data = json.loads(data_str)
                if data.get("status") == "success":
                    results.append(data.get("data", {}))
            except (json.JSONDecodeError, TypeError):
                continue

        # 计算统计
        if not results:
            return {"error": "No data collected"}

        total_views = sum(
            r.get("metrics", {}).get("views", 0)
            for r in results
        )
        total_likes = sum(
            r.get("metrics", {}).get("likes", 0)
            for r in results
        )

        return {
            "content_count": len(results),
            "total_views": total_views,
            "total_likes": total_likes,
            "avg_views": total_views / len(results) if results else 0,
            "avg_likes": total_likes / len(results) if results else 0,
        }
