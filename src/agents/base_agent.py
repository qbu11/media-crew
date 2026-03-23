"""
Base Agent Module

所有 Agent 的基类，提供通用逻辑和默认配置。
"""

from abc import ABC, abstractmethod
from typing import Any

from crewai import Agent
from langchain_anthropic import ChatAnthropic


class BaseAgent(ABC):
    """
    Agent 基类。

    所有具体 Agent 应继承此类并实现 abstract 方法。
    """

    # 默认 LLM 模型
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    OPUS_MODEL = "claude-opus-4-20250514"

    def __init__(
        self,
        llm: str | None = None,
        tools: list[Any] | None = None,
        verbose: bool = True,
        allow_delegation: bool = True,
        human_input: bool = False,
    ):
        """
        初始化 Agent。

        Args:
            llm: 使用的 LLM 模型名称，默认使用子类指定的模型
            tools: Agent 可用的工具列表
            verbose: 是否输出详细日志
            allow_delegation: 是否允许任务委托
            human_input: 是否需要人工输入
        """
        self.llm = llm or self.get_default_model()
        self.tools = tools or []
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.human_input = human_input

    @abstractmethod
    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""

    @abstractmethod
    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""

    @abstractmethod
    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""

    def get_default_model(self) -> str:
        """
        返回默认的 LLM 模型。

        子类可覆盖此方法以指定不同的默认模型。
        """
        return self.DEFAULT_MODEL

    def get_tools(self) -> list[Any]:
        """
        返回 Agent 可用的工具列表。

        子类可覆盖此方法以添加特定工具。
        """
        return self.tools

    def create_llm(self) -> ChatAnthropic:
        """创建 LLM 实例。"""
        return ChatAnthropic(
            model=self.llm,
            temperature=0.7,
        )

    def build(self) -> Agent:
        """
        构建 CrewAI Agent 实例。

        Returns:
            Agent: CrewAI Agent 对象
        """
        return Agent(
            role=self.get_role(),
            goal=self.get_goal(),
            backstory=self.get_backstory(),
            tools=self.get_tools(),
            llm=self.create_llm(),
            verbose=self.verbose,
            allow_delegation=self.allow_delegation,
            human_input=self.human_input,
        )

    @classmethod
    def create(
        cls,
        llm: str | None = None,
        tools: list[Any] | None = None,
        **kwargs,
    ) -> Agent:
        """
        便捷方法：创建并返回 Agent 实例。

        Args:
            llm: LLM 模型名称
            tools: 工具列表
            **kwargs: 其他 Agent 参数

        Returns:
            Agent: CrewAI Agent 对象
        """
        instance = cls(llm=llm, tools=tools, **kwargs)
        return instance.build()
