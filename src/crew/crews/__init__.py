"""
CrewAI Crews Module

自媒体内容生产团队的 4 个核心 Crew。
"""

from .analytics_crew import AnalyticsCrew
from .base_crew import BaseCrew, CrewInput, CrewResult
from .content_crew import ContentCrew
from .hotspot_crew import HotspotDetectionCrew
from .publish_crew import PublishCrew

__all__ = [
    "AnalyticsCrew",
    # Base classes
    "BaseCrew",
    # Crew implementations
    "ContentCrew",
    "CrewInput",
    "CrewResult",
    "HotspotDetectionCrew",
    "PublishCrew",
]
