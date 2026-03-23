"""
CrewAI Tools for Media Publishing Platform

Provides tools for content publishing, analytics, and optimization
across multiple Chinese social media platforms.
"""

from .analytics_tools import analytics_report_tool, data_collect_tool
from .base_tool import BaseTool, ToolError, ToolResult
from .content_tools import hashtag_suggest_tool, image_search_tool, seo_optimize_tool
from .search_tools import competitor_analysis_tool, hot_search_tool, trend_analysis_tool

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
]

__version__ = "0.1.0"
