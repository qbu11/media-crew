"""
CrewAI Crews Module

自媒体内容生产团队的 4 个核心 Crew。
"""

from .base_crew import BaseCrew, CrewResult, CrewInput
from .content_crew import ContentCrew
from .publish_crew import PublishCrew
from .analytics_crew import AnalyticsCrew
from .hotspot_crew import HotspotDetectionCrew

__all__ = [
    # Base classes
    "BaseCrew",
    "CrewResult",
    "CrewInput",

    # Crew implementations
    "ContentCrew",
    "PublishCrew",
    "AnalyticsCrew",
    "HotspotDetectionCrew",
]
