"""
Input Validation Module

提供统一的输入验证、清洗和转义。
"""

import html
import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Platform Enum
# ============================================================================


class Platform(str, Enum):
    """支持的平台。"""

    # 国内平台
    XIAOHONGSHU = "xiaohongshu"
    WECHAT = "wechat"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"

    # 海外平台
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    REDDIT = "reddit"


DOMESTIC_PLATFORMS = {
    Platform.XIAOHONGSHU,
    Platform.WECHAT,
    Platform.WEIBO,
    Platform.ZHIHU,
    Platform.DOUYIN,
    Platform.BILIBILI,
}

OVERSEAS_PLATFORMS = {
    Platform.TWITTER,
    Platform.INSTAGRAM,
    Platform.FACEBOOK,
    Platform.LINKEDIN,
    Platform.YOUTUBE,
    Platform.REDDIT,
}


class ContentTone(str, Enum):
    """内容风格。"""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    EDUCATIONAL = "educational"
    STORYTELLING = "storytelling"


class ContentStatus(str, Enum):
    """内容状态。"""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


# ============================================================================
# Utility Functions
# ============================================================================


def sanitize_string(value: str) -> str:
    """
    清洗字符串：移除 HTML 标签，不转义（保持可读性）。
    """
    if not value:
        return ""

    # 移除 HTML 标签
    clean = re.sub(r"<[^>]+>", "", value)

    # 移除控制字符
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean)

    return clean.strip()


def validate_no_sql_injection(value: str) -> bool:
    """
    检查字符串是否包含 SQL 注入模式。
    """
    if not value:
        return True

    # 常见 SQL 注入模式
    patterns = [
        r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b)",
        r"(?i)(\b(UNION|JOIN)\b.*\b(SELECT|FROM)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(?i)(\b(OR|AND)\b.*=)",
        r"(?i)(\bEXEC\b|\bEXECUTE\b)",
        r"(?i)(\bSCRIPT\b.*\bSRC\b)",
    ]

    for pattern in patterns:
        if re.search(pattern, value):
            return False

    return True


def validate_no_xss(value: str) -> bool:
    """
    检查字符串是否包含 XSS 模式。
    """
    if not value:
        return True

    # 常见 XSS 模式
    patterns = [
        r"(?i)<\s*script",
        r"(?i)javascript\s*:",
        r"(?i)on\w+\s*=",
        r"(?i)<\s*iframe",
        r"(?i)<\s*object",
        r"(?i)<\s*embed",
        r"(?i)<\s*link",
        r"(?i)<\s*meta",
        r"(?i)expression\s*\(",
        r"(?i)vbscript\s*:",
    ]

    for pattern in patterns:
        if re.search(pattern, value):
            return False

    return True


def validate_no_prompt_injection(value: str) -> bool:
    """
    检查字符串是否包含 LLM Prompt 注入模式。
    """
    if not value:
        return True

    # 常见 Prompt 注入模式
    patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|above)\s+(instructions?|prompts?|rules)",
        r"(?i)system\s*:\s*you\s+are",
        r"(?i)forget\s+(all\s+)?(previous|above)",
        r"(?i)disregard\s+(all\s+)?(previous|above)",
        r"(?i)<\|.*?\|>",  # 特殊 token
        r"(?i)\[SYSTEM\]",
        r"(?i)\[INST\]",
        r"(?i)###\s*INSTRUCTION",
    ]

    for pattern in patterns:
        if re.search(pattern, value):
            return False

    return True


# ============================================================================
# Request Models
# ============================================================================


class ContentGenerateRequest(BaseModel):
    """内容生成请求。"""

    topic: str = Field(..., min_length=1, max_length=200, description="选题主题")
    keywords: str = Field(default="", max_length=500, description="关键词")
    platforms: list[Platform] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="目标平台",
    )
    tone: ContentTone = Field(
        default=ContentTone.PROFESSIONAL,
        description="内容风格",
    )
    brand_voice: str = Field(default="", max_length=500, description="品牌调性")
    reference_urls: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="参考链接",
    )

    @field_validator("topic", "keywords", "brand_voice")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """清洗文本输入。"""
        return sanitize_string(v)

    @field_validator("topic", "keywords")
    @classmethod
    def validate_security(cls, v: str) -> str:
        """验证安全约束。"""
        if not validate_no_sql_injection(v):
            raise ValueError("输入包含不允许的字符")
        if not validate_no_xss(v):
            raise ValueError("输入包含不允许的 HTML")
        if not validate_no_prompt_injection(v):
            raise ValueError("输入包含不允许的模式")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[Platform]) -> list[Platform]:
        """验证平台列表。"""
        # 去重
        unique = list(set(v))
        if len(unique) != len(v):
            raise ValueError("平台列表包含重复项")
        return unique

    @field_validator("reference_urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        """验证 URL 格式。"""
        url_pattern = re.compile(
            r"^https?://"
            r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"
            r"(?:/[^\s]*)?$"
        )
        for url in v:
            if not url_pattern.match(url):
                raise ValueError(f"无效的 URL: {url}")
        return v


class PublishRequest(BaseModel):
    """发布请求。"""

    content_id: str = Field(..., min_length=1, max_length=100, description="内容 ID")
    platforms: list[Platform] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="目标平台",
    )
    scheduled_at: Optional[str] = Field(
        default=None,
        description="定时发布时间（ISO 8601）",
    )
    auto_confirm: bool = Field(default=False, description="自动确认发布")

    @field_validator("content_id")
    @classmethod
    def validate_content_id(cls, v: str) -> str:
        """验证内容 ID 格式。"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("内容 ID 格式无效")
        return v

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: Optional[str]) -> Optional[str]:
        """验证定时发布时间。"""
        if v is None:
            return v

        # 验证 ISO 8601 格式
        iso_pattern = re.compile(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        )
        if not iso_pattern.match(v):
            raise ValueError("时间格式无效，请使用 ISO 8601 格式")

        # 验证时间在未来
        from datetime import datetime

        try:
            scheduled = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if scheduled < datetime.now(scheduled.tzinfo):
                raise ValueError("定时发布时间必须在将来")
        except ValueError:
            raise ValueError("无法解析时间")  # noqa: B904

        return v


class HotspotSearchRequest(BaseModel):
    """热点搜索请求。"""

    keywords: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    platforms: list[Platform] = Field(
        default_factory=lambda: list(DOMESTIC_PLATFORMS),
        description="目标平台",
    )
    days: int = Field(default=7, ge=1, le=30, description="时间范围（天）")
    limit: int = Field(default=10, ge=1, le=50, description="结果数量限制")

    @field_validator("keywords")
    @classmethod
    def sanitize_and_validate(cls, v: str) -> str:
        """清洗和验证关键词。"""
        clean = sanitize_string(v)
        if not validate_no_sql_injection(clean):
            raise ValueError("输入包含不允许的字符")
        return clean


class AnalyticsRequest(BaseModel):
    """数据分析请求。"""

    content_id: Optional[str] = Field(default=None, max_length=100, description="内容 ID")
    platform: Optional[Platform] = Field(default=None, description="平台")
    period: str = Field(default="7d", description="统计周期")
    metrics: list[str] = Field(
        default_factory=lambda: ["views", "likes", "comments", "shares"],
        description="指标列表",
    )

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        """验证统计周期。"""
        valid_periods = ["1d", "3d", "7d", "14d", "30d", "90d"]
        if v not in valid_periods:
            raise ValueError(f"无效的统计周期，可选值: {valid_periods}")
        return v

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: list[str]) -> list[str]:
        """验证指标列表。"""
        valid_metrics = {"views", "likes", "comments", "shares", "saves", "engagement_rate"}
        for metric in v:
            if metric not in valid_metrics:
                raise ValueError(f"无效的指标: {metric}")
        return v


# ============================================================================
# Response Models
# ============================================================================


class APIResponse[T](BaseModel):
    """统一 API 响应格式。"""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    meta: Optional[dict[str, Any]] = None

    @classmethod
    def ok(cls, data: T, meta: Optional[dict[str, Any]] = None) -> "APIResponse[T]":
        """创建成功响应。"""
        return cls(success=True, data=data, meta=meta)

    @classmethod
    def fail(
        cls,
        error: str,
        error_code: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> "APIResponse[T]":
        """创建失败响应。"""
        return cls(success=False, error=error, error_code=error_code, meta=meta)


class PaginatedResponse[T](BaseModel):
    """分页响应。"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """创建分页响应。"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
