"""
CrewAI Agents Module

自媒体内容生产团队的 Agent 定义。

架构：
- ContentOrchestrator：编排者，协调子 Agent
- Researcher：热点研究员
- Marketer：营销策划师
- Copywriter：文案创作者
- Designer：视觉设计师
- ContentReviewer：内容审核员
- DataAnalyst：数据分析师
- PlatformAdapter：平台适配师
- PlatformPublisher：平台发布员
"""

from .base_agent import BaseAgent

# 核心编排者
from .content_orchestrator import ContentOrchestrator

# 内容创作子 Agent
from .researcher import Researcher, ResearchReport
from .marketer import Marketer, ContentStrategy
from .copywriter import Copywriter, CopyDraft
from .designer import Designer, DesignOutput

# 审核和发布
from .content_reviewer import ContentReviewer
from .data_analyst import DataAnalyst
from .platform_adapter import PlatformAdapter
from .platform_publisher import PlatformPublisher

# 旧版本兼容（保留原有导入路径）
from .content_creator import ContentDraft

# 向后兼容的别名
ContentCreator = ContentOrchestrator
ContentWriter = ContentOrchestrator
TopicResearcher = Researcher

__all__ = [
    # 基类
    "BaseAgent",
    # 编排者
    "ContentOrchestrator",
    "ContentCreator",  # 别名
    "ContentWriter",  # 别名
    # 子 Agent
    "Researcher",
    "ResearchReport",
    "TopicResearcher",  # 别名
    "Marketer",
    "ContentStrategy",
    "Copywriter",
    "CopyDraft",
    "Designer",
    "DesignOutput",
    # 数据结构
    "ContentDraft",
    # 审核/发布
    "ContentReviewer",
    "DataAnalyst",
    "PlatformAdapter",
    "PlatformPublisher",
]
