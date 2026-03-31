"""
Base Crew Module

所有 Crew 的基类，提供通用逻辑和标准化接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from crewai import Crew, Process
from loguru import logger


class CrewStatus(Enum):
    """Crew 执行状态枚举。"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class CrewInput:
    """
    Crew 输入数据类。

    标准化所有 Crew 的输入格式。
    """

    inputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        return {
            "inputs": self.inputs,
            "metadata": self.metadata,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrewInput":
        """从字典创建实例。"""
        return cls(
            inputs=data.get("inputs", {}),
            metadata=data.get("metadata", {}),
            context=data.get("context"),
        )


@dataclass
class CrewResult:
    """
    Crew 执行结果数据类。

    标准化所有 Crew 的输出格式。
    """

    status: CrewStatus
    data: dict[str, Any] | None = None
    error: str | None = None
    raw_outputs: dict[str, Any] | None = None
    execution_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "raw_outputs": self.raw_outputs,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_success(self) -> bool:
        """检查执行是否成功。"""
        return self.status == CrewStatus.COMPLETED

    def is_failed(self) -> bool:
        """检查执行是否失败。"""
        return self.status == CrewStatus.FAILED


T = TypeVar("T", bound=CrewInput)


class BaseCrew(ABC):
    """
    Crew 基类。

    所有具体 Crew 应继承此类并实现 abstract 方法。
    """

    def __init__(
        self,
        verbose: bool = True,
        process: Process = Process.sequential,
        memory: bool = True,
        max_rpm: int | None = None,
        share_crew: bool = False,
    ):
        """
        初始化 Crew。

        Args:
            verbose: 是否输出详细日志
            process: 执行流程类型
            memory: 是否使用记忆
            max_rpm: 每分钟最大执行次数
            share_crew: 是否共享 Crew
        """
        self.verbose = verbose
        self.process = process
        self.memory = memory
        self.max_rpm = max_rpm
        self.share_crew = share_crew
        self._crew: Crew | None = None
        self._status: CrewStatus = CrewStatus.PENDING

    @abstractmethod
    def get_agents(self) -> list[Any]:
        """
        返回 Crew 的 Agent 列表。

        Returns:
            Agent 列表
        """

    @abstractmethod
    def get_tasks(self, inputs: CrewInput) -> list[Any]:
        """
        根据 Crew 输入返回任务列表。

        Args:
            inputs: Crew 输入

        Returns:
            Task 列表
        """

    @abstractmethod
    def get_crew_name(self) -> str:
        """
        返回 Crew 名称。

        Returns:
            Crew 名称
        """

    def get_process(self) -> Process:
        """
        返回执行流程类型。

        子类可覆盖此方法以指定不同的流程类型。

        Returns:
            Process 枚举值
        """
        return self.process

    def get_description(self) -> str:
        """
        返回 Crew 描述。

        子类可覆盖此方法以提供自定义描述。

        Returns:
            Crew 描述字符串
        """
        return f"{self.get_crew_name()} Crew"

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, str | None]:
        """
        验证输入参数。

        子类可覆盖此方法以添加自定义验证逻辑。

        Args:
            inputs: Crew 输入

        Returns:
            (是否有效, 错误信息) 元组
        """
        return True, None

    def pre_execute(self, inputs: CrewInput) -> None:
        """
        执行前钩子。

        子类可覆盖此方法以添加自定义预处理逻辑。

        Args:
            inputs: Crew 输入
        """
        logger.info(f"[{self.get_crew_name()}] Starting execution")

    def post_execute(self, result: CrewResult) -> CrewResult:
        """
        执行后钩子。

        子类可覆盖此方法以添加自定义后处理逻辑。

        Args:
            result: 执行结果

        Returns:
            可能被修改后的结果
        """
        logger.info(f"[{self.get_crew_name()}] Execution completed with status: {result.status.value}")
        return result

    def build_crew(self, inputs: CrewInput) -> Crew:
        """
        构建 CrewAI Crew 实例。

        Args:
            inputs: Crew 输入

        Returns:
            CrewAI Crew 对象
        """
        agents = self.get_agents()
        tasks = self.get_tasks(inputs)

        return Crew(
            agents=agents,
            tasks=tasks,
            process=self.get_process(),
            memory=self.memory,
            verbose=self.verbose,
            max_rpm=self.max_rpm,
            share_crew=self.share_crew,
        )

    def execute(self, inputs: CrewInput) -> CrewResult:
        """
        执行 Crew。

        Args:
            inputs: Crew 输入

        Returns:
            CrewResult 执行结果
        """
        import time

        start_time = time.time()

        # 验证输入
        is_valid, error_msg = self.validate_inputs(inputs)
        if not is_valid:
            return CrewResult(
                status=CrewStatus.FAILED,
                error=f"Invalid inputs: {error_msg}",
                execution_time=time.time() - start_time,
            )

        try:
            self._status = CrewStatus.RUNNING
            self.pre_execute(inputs)

            # 构建 Crew
            crew = self.build_crew(inputs)

            # 执行 — CrewAI 1.6.1 接受 inputs=dict
            outputs = crew.kickoff(inputs=inputs.inputs)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 解析输出
            result_data = self._parse_outputs(outputs)

            result = CrewResult(
                status=CrewStatus.COMPLETED,
                data=result_data,
                raw_outputs=self._extract_raw_outputs(outputs),
                execution_time=execution_time,
            )

            return self.post_execute(result)

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{self.get_crew_name()}] Execution failed: {e}")

            result = CrewResult(
                status=CrewStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
            )

            return self.post_execute(result)

        finally:
            self._status = CrewStatus.PENDING

    def kickoff(self, **inputs) -> CrewResult:
        """
        便捷方法：执行 Crew。

        Args:
            **inputs: Crew 输入参数

        Returns:
            CrewResult 执行结果
        """
        crew_input = CrewInput(inputs=inputs)
        return self.execute(crew_input)

    def _parse_outputs(self, outputs: Any) -> dict[str, Any]:
        """
        解析 Crew 输出。

        子类可覆盖此方法以自定义输出解析逻辑。

        Args:
            outputs: 原始输出

        Returns:
            解析后的数据字典
        """
        if hasattr(outputs, "to_dict"):
            return outputs.to_dict()
        elif isinstance(outputs, dict):
            return outputs
        elif isinstance(outputs, str):
            return {"output": outputs}
        else:
            return {"raw": str(outputs)}

    def _extract_raw_outputs(self, outputs: Any) -> dict[str, Any]:
        """
        提取原始输出用于调试。

        Args:
            outputs: 原始输出

        Returns:
            原始输出字典
        """
        return {
            "type": type(outputs).__name__,
            "raw": str(outputs),
        }

    @classmethod
    def create(cls, **kwargs) -> "BaseCrew":
        """
        便捷方法：创建 Crew 实例。

        Args:
            **kwargs: Crew 配置参数

        Returns:
            BaseCrew 实例
        """
        return cls(**kwargs)
