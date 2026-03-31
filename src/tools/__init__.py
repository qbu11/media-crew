"""
CrewAI Tools for Media Publishing Platform

Provides tools for content publishing, analytics, and optimization
across multiple Chinese social media platforms.
"""

from .analytics_tools import analytics_report_tool, data_collect_tool
from .base_tool import BaseTool, ToolError, ToolResult
from .content_tools import hashtag_suggest_tool, image_search_tool, seo_optimize_tool
from .search_tools import competitor_analysis_tool, hot_search_tool, trend_analysis_tool
from .viral_reference import (
    DIMENSION_ANALYSIS_PROMPTS,
    MatchResult,
    PLATFORM_SEARCH_URLS,
    ViralReference,
    ViralReferenceReport,
    ViralReferenceValidator,
    get_match_validation_prompt,
    get_viral_search_prompt,
)

__all__ = [
    # Base classes
    "BaseTool",
    "ToolError",
    "ToolResult",
    "analytics_report_tool",
    "competitor_analysis_tool",
    # Analytics tools
    "data_collect_tool",
    "hashtag_suggest_tool",
    # Search tools
    "hot_search_tool",
    # Content tools
    "image_search_tool",
    "seo_optimize_tool",
    "trend_analysis_tool",
    # Viral reference system
    "ViralReference",
    "MatchResult",
    "ViralReferenceReport",
    "ViralReferenceValidator",
    "get_viral_search_prompt",
    "get_match_validation_prompt",
    "DIMENSION_ANALYSIS_PROMPTS",
    "PLATFORM_SEARCH_URLS",
]

__version__ = "0.1.0"
