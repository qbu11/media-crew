"""Content brief schema for topic research results."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TargetAudience(str, Enum):
    """Target audience types."""

    GENERAL = "general"
    PROFESSIONAL = "professional"
    STUDENT = "student"
    ENTREPRENEUR = "entrepreneur"
    TECHNICAL = "technical"


class ContentType(str, Enum):
    """Content format types."""

    ARTICLE = "article"
    VIDEO = "video"
    IMAGE = "image"
    THREAD = "thread"
    MIXED = "mixed"


class PlatformType(str, Enum):
    """Supported platforms."""

    XIAOHONGSHU = "xiaohongshu"
    WECHAT = "wechat"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"


class TrendingTopic(BaseModel):
    """A trending topic discovered during research."""

    keyword: str = Field(..., description="Topic keyword")
    search_volume: int = Field(default=0, ge=0, description="Estimated search volume")
    growth_rate: float = Field(default=0.0, ge=-100.0, le=1000.0, description="Growth rate percentage")
    competition_level: Literal["low", "medium", "high"] = Field(
        default="medium", description="Competition level"
    )
    related_keywords: list[str] = Field(default_factory=list, description="Related keywords")
    source_platform: PlatformType | None = Field(default=None, description="Source platform")


class AudienceInsight(BaseModel):
    """Audience analysis insights."""

    segment: TargetAudience = Field(..., description="Audience segment")
    size_estimate: str = Field(..., description="Estimated audience size description")
    interests: list[str] = Field(default_factory=list, description="Key interests")
    pain_points: list[str] = Field(default_factory=list, description="Common pain points")
    preferred_content_type: ContentType = Field(
        default=ContentType.ARTICLE, description="Preferred content format"
    )
    active_hours: list[str] = Field(
        default_factory=lambda: ["9:00-11:00", "18:00-21:00"],
        description="Peak active hours",
    )


class ContentBrief(BaseModel):
    """Content brief generated from topic research."""

    # Metadata
    id: str = Field(..., description="Unique brief identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    # Topic
    topic: str = Field(..., min_length=1, max_length=200, description="Main topic")
    sub_topics: list[str] = Field(default_factory=list, description="Sub topics to cover")
    keywords: list[str] = Field(
        ..., min_length=1, description="Keywords for SEO and discovery"
    )

    # Audience
    target_audience: list[AudienceInsight] = Field(
        default_factory=list, description="Target audience analysis"
    )

    # Trends
    trending_topics: list[TrendingTopic] = Field(
        default_factory=list, description="Related trending topics"
    )

    # Content Direction
    content_angle: str = Field(..., description="Unique angle/perspective for the content")
    tone: Literal["professional", "casual", "humorous", "inspiring", "educational"] = Field(
        default="professional", description="Content tone"
    )
    suggested_content_type: ContentType = Field(
        default=ContentType.ARTICLE, description="Suggested content format"
    )

    # Platform Strategy
    primary_platform: PlatformType = Field(
        default=PlatformType.XIAOHONGSHU, description="Primary platform"
    )
    secondary_platforms: list[PlatformType] = Field(
        default_factory=list, description="Secondary platforms"
    )

    # Guidance
    key_points: list[str] = Field(default_factory=list, description="Key points to cover")
    call_to_action: str = Field(default="", description="Suggested call to action")
    hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags")

    # Validation
    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        """Validate keywords list."""
        if not v:
            raise ValueError("At least one keyword is required")
        return [k.strip().lower() for k in v if k.strip()]

    @field_validator("sub_topics")
    @classmethod
    def validate_sub_topics(cls, v: list[str]) -> list[str]:
        """Validate sub topics list."""
        return [t.strip() for t in v if t.strip()][:5]  # Max 5 sub topics

    @field_validator("hashtags")
    @classmethod
    def validate_hashtags(cls, v: list[str]) -> list[str]:
        """Validate hashtags format."""
        tags = []
        for tag in v:
            tag = tag.strip()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            tags.append(tag)
        return tags[:10]  # Max 10 hashtags

    model_config = {"json_schema_extra": {"example": {}}}


ContentBrief.model_rebuild()


# Example for documentation
ContentBrief.model_config["json_schema_extra"]["example"] = {
    "id": "brief-20250320-001",
    "topic": "AI创业实战指南",
    "sub_topics": ["MVP开发", "融资策略", "团队搭建"],
    "keywords": ["AI创业", "人工智能", "创业指南", "科技创业"],
    "target_audience": [
        {
            "segment": "entrepreneur",
            "size_estimate": "10万+",
            "interests": ["AI技术", "创业融资", "产品管理"],
            "pain_points": ["技术选型困难", "资金短缺", "团队管理"],
            "preferred_content_type": "article",
        }
    ],
    "trending_topics": [
        {
            "keyword": "AI Agent",
            "search_volume": 50000,
            "growth_rate": 150.0,
            "competition_level": "medium",
            "related_keywords": ["智能体", "AI助手", "自动化"],
        }
    ],
    "content_angle": "从技术人角度分享AI创业踩坑经验",
    "tone": "professional",
    "suggested_content_type": "article",
    "primary_platform": "xiaohongshu",
    "secondary_platforms": ["wechat", "zhihu"],
    "key_points": [
        "技术栈选择建议",
        "第一笔融资经验",
        "核心团队组建",
        "产品迭代策略",
    ],
    "call_to_action": "关注我，获取更多AI创业干货",
    "hashtags": ["#AI创业", "#科技创业", "#创业指南"],
}
