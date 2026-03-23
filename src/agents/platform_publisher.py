"""
Platform Publisher Agent

平台发布员：将内容发布到各平台，并管理发布状态。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from .base_agent import BaseAgent
from .platform_adapter import Platform


class PublishStatus(Enum):
    """发布状态枚举。"""

    PENDING = "pending"  # 待发布
    SCHEDULED = "scheduled"  # 已定时
    PUBLISHING = "publishing"  # 发布中
    PUBLISHED = "published"  # 已发布
    FAILED = "failed"  # 失败
    RETRYING = "retrying"  # 重试中


class PlatformPublisher(BaseAgent):
    """
    平台发布员 Agent。

    职责：
    - 将适配后的内容发布到各平台
    - 管理发布队列和定时发布
    - 处理发布失败和重试
    - 记录发布结果和链接
    - 提供发布状态查询
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def __init__(
        self,
        llm: str | None = None,
        tools: list[Any] | None = None,
        verbose: bool = True,
        allow_delegation: bool = False,
        human_input: bool = False,
    ):
        """
        初始化平台发布员。

        Args:
            llm: 使用的 LLM 模型名称
            tools: Agent 可用的工具列表
            verbose: 是否输出详细日志
            allow_delegation: 是否允许任务委托（发布员默认不允许）
            human_input: 是否需要人工输入
        """
        super().__init__(
            llm=llm,
            tools=tools,
            verbose=verbose,
            allow_delegation=allow_delegation,
            human_input=human_input,
        )

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "平台发布员"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "可靠、高效地将内容发布到各平台，管理发布队列， "
            "处理异常情况，确保每一条内容都能成功发布"
        )

    def get_backstory(self) -> str:
        """返回 Agent 的背景故事。"""
        return """你是一位经验丰富的平台发布专员，负责内容在各大平台的发布工作。
你对各平台的发布流程和 API 接口非常熟悉，能够快速定位和解决发布问题。
你做事细致认真，每一条发布前都会仔细检查格式和参数。
你擅长处理各种发布异常，懂得何时重试、何时人工介入。
你维护着清晰的发布记录，确保每条内容都有据可查。
在需要定时发布时，你能精确把握最佳发布时间窗口。
你的工作是内容生产流程的最后一环，确保所有努力最终成功触达用户。"""

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - platform_api_tool: 各平台 API 工具
        # - scheduler: 定时任务工具
        # - notification_tool: 通知工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class PublishRecord:
    """
    发布记录数据结构。

    用于规范化平台发布员的输出格式。
    """

    def __init__(
        self,
        content_id: str,
        platform: Platform,
        status: PublishStatus,
        published_url: str | None = None,
        published_at: datetime | None = None,
        scheduled_at: datetime | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        """
        初始化发布记录。

        Args:
            content_id: 内容 ID
            platform: 发布平台
            status: 发布状态
            published_url: 发布后的 URL
            published_at: 实际发布时间
            scheduled_at: 定时发布时间
            error_message: 错误信息
            retry_count: 重试次数
            metadata: 其他元数据
        """
        self.content_id = content_id
        self.platform = platform
        self.status = status
        self.published_url = published_url
        self.published_at = published_at
        self.scheduled_at = scheduled_at
        self.error_message = error_message
        self.retry_count = retry_count
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "content_id": self.content_id,
            "platform": self.platform.value,
            "status": self.status.value,
            "published_url": self.published_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    def is_success(self) -> bool:
        """检查发布是否成功。"""
        return self.status == PublishStatus.PUBLISHED

    def is_failed(self) -> bool:
        """检查发布是否失败。"""
        return self.status == PublishStatus.FAILED

    def is_pending(self) -> bool:
        """检查是否待发布。"""
        return self.status in (PublishStatus.PENDING, PublishStatus.SCHEDULED)


class PublishBatch:
    """
    批量发布管理类。

    用于管理一条内容在多个平台的发布。
    """

    def __init__(self, content_id: str, platforms: list[Platform]):
        """
        初始化批量发布。

        Args:
            content_id: 内容 ID
            platforms: 目标平台列表
        """
        self.content_id = content_id
        self.records: dict[Platform, PublishRecord] = {
            platform: PublishRecord(
                content_id=content_id,
                platform=platform,
                status=PublishStatus.PENDING,
            )
            for platform in platforms
        }

    def update_record(self, record: PublishRecord) -> None:
        """
        更新发布记录。

        Args:
            record: 发布记录
        """
        self.records[record.platform] = record

    def get_record(self, platform: Platform) -> PublishRecord | None:
        """
        获取指定平台的发布记录。

        Args:
            platform: 平台

        Returns:
            发布记录或 None
        """
        return self.records.get(platform)

    def get_successful_platforms(self) -> list[Platform]:
        """获取发布成功的平台列表。"""
        return [
            p for p, r in self.records.items() if r.status == PublishStatus.PUBLISHED
        ]

    def get_failed_platforms(self) -> list[Platform]:
        """获取发布失败的平台列表。"""
        return [
            p for p, r in self.records.items() if r.status == PublishStatus.FAILED
        ]

    def get_pending_platforms(self) -> list[Platform]:
        """获取待发布的平台列表。"""
        return [
            p
            for p, r in self.records.items()
            if r.status in (PublishStatus.PENDING, PublishStatus.SCHEDULED)
        ]

    def is_all_success(self) -> bool:
        """检查是否所有平台都发布成功。"""
        return all(r.is_success() for r in self.records.values())

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "content_id": self.content_id,
            "records": {p.value: r.to_dict() for p, r in self.records.items()},
            "summary": {
                "total": len(self.records),
                "successful": len(self.get_successful_platforms()),
                "failed": len(self.get_failed_platforms()),
                "pending": len(self.get_pending_platforms()),
            },
        }
