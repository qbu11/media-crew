"""
Content Tools for Media Publishing

Provides tools for:
- Image search and recommendation
- Hashtag/topic tag suggestions
- SEO optimization
"""

from enum import Enum
import json
import re
from typing import Any

from .base_tool import BaseTool, ToolResult, ToolStatus


class ContentType(Enum):
    """Content types for optimization"""
    ARTICLE = "article"
    VIDEO = "video"
    IMAGE_POST = "image_post"


class ImageSearchTool(BaseTool):
    """
    Tool for searching and recommending images for content.

    Uses image search APIs to find relevant images.
    """

    name = "image_search"
    description = "Searches for images relevant to content topics"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 10
    min_interval_seconds = 3.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key = self.config.get("api_key")

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        query = kwargs.get("query")
        if not query:
            return False, "Query is required"

        limit = kwargs.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return False, "Limit must be between 1 and 50"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Search for images.

        Args:
            query: Search query
            limit: Maximum number of results (default: 10)
            orientation: Image orientation (landscape, portrait, square)
            style: Image style (photo, illustration, vector)

        Returns:
            ToolResult with image URLs and metadata
        """
        query = kwargs.get("query")
        limit = kwargs.get("limit", 10)
        orientation = kwargs.get("orientation", "landscape")
        style = kwargs.get("style", "photo")

        try:
            # In actual implementation:
            # 1. Call image search API (Unsplash, Pexels, etc.)
            # 2. Filter by orientation and style
            # 3. Return image URLs and metadata

            images = [
                {
                    "url": f"https://images.unsplash.com/photo-{i + 1}",
                    "thumbnail": f"https://images.unsplash.com/photo-{i + 1}?w=200",
                    "width": 1920,
                    "height": 1080 if orientation == "landscape" else 1080,
                    "source": "unsplash",
                    "attribution": f"Photographer {i + 1}",
                    "license": "free"
                }
                for i in range(limit)
            ]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "query": query,
                    "images": images,
                    "total": len(images),
                    "filters": {
                        "orientation": orientation,
                        "style": style
                    }
                },
                platform="multi"
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Image search failed: {e!s}",
                platform="multi"
            )


class HashtagSuggestTool(BaseTool):
    """
    Tool for suggesting hashtags/topic tags for content.

    Analyzes content and suggests relevant, high-performing hashtags.
    """

    name = "hashtag_suggest"
    description = "Suggests hashtags and topic tags for content"
    platform = "multi"
    version = "0.1.0"

    # Platform-specific hashtag limits
    PLATFORM_LIMITS = {
        "xiaohongshu": 10,
        "weibo": 2,
        "douyin": 5,
        "bilibili": 12,
        "zhihu": 5
    }

    max_requests_per_minute = 10
    min_interval_seconds = 2.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        content = kwargs.get("content")
        if not content:
            return False, "Content is required"

        platform = kwargs.get("platform", "xiaohongshu")
        if platform not in self.PLATFORM_LIMITS:
            return False, f"Unsupported platform: {platform}"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Suggest hashtags for content.

        Args:
            content: Content text to analyze
            platform: Target platform
            max_tags: Maximum number of tags to suggest

        Returns:
            ToolResult with hashtag suggestions
        """
        content = kwargs.get("content", "")
        platform = kwargs.get("platform", "xiaohongshu")
        max_tags = kwargs.get("max_tags", self.PLATFORM_LIMITS.get(platform, 10))

        try:
            # Extract keywords from content
            keywords = self._extract_keywords(content)

            # Generate hashtags
            hashtags = self._generate_hashtags(keywords, platform, max_tags)

            # Add trending tags
            trending = self._get_trending_tags(platform)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "platform": platform,
                    "suggested_tags": hashtags[:max_tags],
                    "trending_tags": trending[:3],
                    "keywords_extracted": keywords[:10],
                    "max_tags_allowed": self.PLATFORM_LIMITS.get(platform, 10)
                },
                platform=platform
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"Hashtag suggestion failed: {e!s}",
                platform=platform
            )

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from content"""
        # Simple keyword extraction
        # In actual implementation, use NLP library
        words = re.findall(r"\w+", content.lower())
        # Filter short words and duplicates
        keywords = [w for w in words if len(w) > 2]
        return list(dict.fromkeys(keywords))

    def _generate_hashtags(
        self,
        keywords: list[str],
        platform: str,
        max_tags: int
    ) -> list[dict]:
        """Generate hashtag suggestions"""
        hashtags = []

        for keyword in keywords[:max_tags]:
            # Generate variations
            tag = keyword.replace(" ", "")
            hashtags.append({
                "tag": tag,
                "display": f"#{tag}",
                "relevance": 0.8,
                "popularity": "medium",
                "category": "content"
            })

        return hashtags

    def _get_trending_tags(self, platform: str) -> list[str]:
        """Get trending tags for platform"""
        # In actual implementation, fetch from platform API
        return ["热门", "推荐", "每日精选"]


class SEOOptimizeTool(BaseTool):
    """
    Tool for optimizing content for SEO.

    Analyzes content and provides SEO recommendations.
    """

    name = "seo_optimize"
    description = "Optimizes content for search engine visibility"
    platform = "multi"
    version = "0.1.0"

    max_requests_per_minute = 10
    min_interval_seconds = 2.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

    def validate_input(self, **kwargs) -> tuple[bool, str | None]:
        """Validate input parameters"""
        content = kwargs.get("content")
        if not content:
            return False, "Content is required"

        return True, None

    def execute(self, **kwargs) -> ToolResult:
        """
        Optimize content for SEO.

        Args:
            content: Content text to optimize
            title: Content title (optional)
            target_keywords: Keywords to target (optional)
            content_type: Type of content (article, video, image_post)

        Returns:
            ToolResult with SEO recommendations
        """
        content = kwargs.get("content", "")
        title = kwargs.get("title", "")
        target_keywords = kwargs.get("target_keywords", [])
        content_type = kwargs.get("content_type", "article")

        try:
            # Analyze content
            analysis = self._analyze_content(content, title, target_keywords)

            # Generate recommendations
            recommendations = self._generate_recommendations(analysis, content_type)

            # Calculate SEO score
            score = self._calculate_seo_score(analysis)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "seo_score": score,
                    "analysis": analysis,
                    "recommendations": recommendations,
                    "optimized_title": self._optimize_title(title, target_keywords),
                    "suggested_keywords": self._suggest_keywords(content)
                },
                platform="multi"
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                error=f"SEO optimization failed: {e!s}",
                platform="multi"
            )

    def _analyze_content(
        self,
        content: str,
        title: str,
        target_keywords: list[str]
    ) -> dict[str, Any]:
        """Analyze content for SEO factors"""
        word_count = len(content)
        title_length = len(title)

        # Check keyword density
        keyword_density = {}
        for keyword in target_keywords:
            count = content.lower().count(keyword.lower())
            density = (count * len(keyword)) / word_count if word_count > 0 else 0
            keyword_density[keyword] = {
                "count": count,
                "density": f"{density:.2%}"
            }

        return {
            "word_count": word_count,
            "title_length": title_length,
            "keyword_density": keyword_density,
            "has_subheadings": "##" in content or "<h2" in content,
            "has_images": "![" in content or "<img" in content,
            "has_links": "[" in content or "<a" in content,
            "readability_score": self._calculate_readability(content)
        }

    def _generate_recommendations(
        self,
        analysis: dict[str, Any],
        content_type: str
    ) -> list[dict]:
        """Generate SEO recommendations"""
        recommendations = []

        # Title length
        if analysis["title_length"] < 30:
            recommendations.append({
                "type": "title",
                "priority": "high",
                "message": "Title is too short. Aim for 30-60 characters.",
                "current": analysis["title_length"],
                "target": "30-60"
            })
        elif analysis["title_length"] > 60:
            recommendations.append({
                "type": "title",
                "priority": "medium",
                "message": "Title is too long. Keep it under 60 characters.",
                "current": analysis["title_length"],
                "target": "30-60"
            })

        # Word count
        if content_type == "article" and analysis["word_count"] < 300:
            recommendations.append({
                "type": "content",
                "priority": "high",
                "message": "Content is too short for SEO. Aim for 300+ words.",
                "current": analysis["word_count"],
                "target": "300+"
            })

        # Subheadings
        if not analysis["has_subheadings"] and analysis["word_count"] > 500:
            recommendations.append({
                "type": "structure",
                "priority": "medium",
                "message": "Add subheadings to improve content structure."
            })

        # Images
        if not analysis["has_images"]:
            recommendations.append({
                "type": "media",
                "priority": "medium",
                "message": "Add images to improve engagement."
            })

        return recommendations

    def _calculate_seo_score(self, analysis: dict[str, Any]) -> int:
        """Calculate overall SEO score (0-100)"""
        score = 50  # Base score

        # Title length bonus
        if 30 <= analysis["title_length"] <= 60:
            score += 15

        # Word count bonus
        if analysis["word_count"] >= 300:
            score += 10
        if analysis["word_count"] >= 1000:
            score += 5

        # Structure bonuses
        if analysis["has_subheadings"]:
            score += 10
        if analysis["has_images"]:
            score += 10
        if analysis["has_links"]:
            score += 5

        # Readability bonus
        if analysis["readability_score"] >= 60:
            score += 5

        return min(score, 100)

    def _calculate_readability(self, content: str) -> int:
        """Calculate readability score (simplified)"""
        # Simple implementation
        # In actual use, use a proper readability library
        sentences = content.count(".") + content.count("!") + content.count("?")
        words = len(content.split())

        if sentences == 0:
            return 50

        avg_sentence_length = words / sentences

        # Score based on average sentence length
        if avg_sentence_length < 15:
            return 80
        elif avg_sentence_length < 20:
            return 70
        elif avg_sentence_length < 25:
            return 60
        else:
            return 50

    def _optimize_title(self, title: str, keywords: list[str]) -> str:
        """Generate optimized title suggestion"""
        if not title:
            return ""

        # In actual implementation:
        # - Add primary keyword near the beginning
        # - Ensure length is optimal
        # - Add power words

        return title

    def _suggest_keywords(self, content: str) -> list[str]:
        """Suggest keywords based on content"""
        # Simple implementation
        words = re.findall(r"\w+", content.lower())
        word_freq = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]


# CrewAI tool wrappers

def image_search(query: str, limit: int = 10) -> str:
    """
    Search for images.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        JSON string with image results
    """
    tool = ImageSearchTool()
    result = tool.execute(query=query, limit=limit)
    return json.dumps(result.to_dict(), ensure_ascii=False)


def hashtag_suggest(content: str, platform: str = "xiaohongshu") -> str:
    """
    Suggest hashtags for content.

    Args:
        content: Content text to analyze
        platform: Target platform

    Returns:
        JSON string with hashtag suggestions
    """
    tool = HashtagSuggestTool()
    result = tool.execute(content=content, platform=platform)
    return json.dumps(result.to_dict(), ensure_ascii=False)


def seo_optimize(content: str, title: str = "") -> str:
    """
    Optimize content for SEO.

    Args:
        content: Content text to optimize
        title: Content title

    Returns:
        JSON string with SEO recommendations
    """
    tool = SEOOptimizeTool()
    result = tool.execute(content=content, title=title)
    return json.dumps(result.to_dict(), ensure_ascii=False)


# Export for CrewAI
image_search_tool = image_search
hashtag_suggest_tool = hashtag_suggest
seo_optimize_tool = seo_optimize
