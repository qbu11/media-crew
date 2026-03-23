"""
Custom exceptions for Crew Media Ops.

所有自定义异常都应继承自 CrewException。
"""

from typing import Any


class CrewException(Exception):
    """Base exception for all Crew Media Ops errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ============================================================================
# HotspotAgent Exceptions
# ============================================================================


class HotspotException(CrewException):
    """Base exception for hotspot-related errors."""


class RateLimitError(HotspotException):
    """API rate limit exceeded."""

    def __init__(self, platform: str, retry_after: int = 60):
        super().__init__(
            message=f"{platform} API 限流，请稍后重试",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"platform": platform, "retry_after": retry_after},
        )


class ForbiddenError(HotspotException):
    """API access forbidden (403)."""

    def __init__(self, platform: str):
        super().__init__(
            message=f"{platform} API 访问被拒绝",
            error_code="FORBIDDEN",
            details={"platform": platform},
        )


class TimeoutError(CrewException):
    """Request timeout."""

    def __init__(self, operation: str, timeout: int):
        super().__init__(
            message=f"{operation} 超时（{timeout}秒）",
            error_code="TIMEOUT",
            details={"operation": operation, "timeout": timeout},
        )


class JSONDecodeError(CrewException):
    """JSON parsing failed."""

    def __init__(self, raw_response: str):
        super().__init__(
            message="JSON 解析失败",
            error_code="JSON_DECODE_ERROR",
            details={"raw_response": raw_response[:500]},  # 只保存前 500 字符
        )


# ============================================================================
# ContentAgent Exceptions
# ============================================================================


class ContentException(CrewException):
    """Base exception for content-related errors."""


class LLMTimeoutError(ContentException):
    """LLM API timeout."""

    def __init__(self, model: str, timeout: int):
        super().__init__(
            message=f"LLM API 超时（模型: {model}, 超时: {timeout}秒）",
            error_code="LLM_TIMEOUT",
            details={"model": model, "timeout": timeout},
        )


class LLMFormatError(ContentException):
    """LLM response format error."""

    def __init__(self, expected_format: str, actual_response: str):
        super().__init__(
            message="LLM 返回格式错误",
            error_code="LLM_FORMAT_ERROR",
            details={
                "expected_format": expected_format,
                "actual_response": actual_response[:500],
            },
        )


class EmptyContentError(ContentException):
    """LLM returned empty content."""

    def __init__(self):
        super().__init__(
            message="LLM 返回空内容",
            error_code="EMPTY_CONTENT",
            details={},
        )


class ComplianceError(ContentException):
    """Content contains sensitive words."""

    def __init__(self, sensitive_words: list[str]):
        super().__init__(
            message="内容包含敏感词",
            error_code="COMPLIANCE_ERROR",
            details={"sensitive_words": sensitive_words},
        )


class TokenLimitError(ContentException):
    """Token limit exceeded."""

    def __init__(self, token_count: int, limit: int):
        super().__init__(
            message=f"Token 超限（{token_count}/{limit}）",
            error_code="TOKEN_LIMIT_EXCEEDED",
            details={"token_count": token_count, "limit": limit},
        )


class AuthenticationError(CrewException):
    """API authentication failed."""

    def __init__(self, service: str):
        super().__init__(
            message=f"{service} 认证失败，请检查 API Key",
            error_code="AUTHENTICATION_ERROR",
            details={"service": service},
        )


class DiskFullError(CrewException):
    """Disk space full."""

    def __init__(self, path: str, required_mb: int):
        super().__init__(
            message=f"磁盘空间不足（路径: {path}, 需要: {required_mb}MB）",
            error_code="DISK_FULL",
            details={"path": path, "required_mb": required_mb},
        )


class ImageGenTimeoutError(ContentException):
    """Image generation timeout."""

    def __init__(self, timeout: int):
        super().__init__(
            message=f"图片生成超时（{timeout}秒）",
            error_code="IMAGE_GEN_TIMEOUT",
            details={"timeout": timeout},
        )


class ImageComplianceError(ContentException):
    """Generated image violates compliance."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"图片不合规: {reason}",
            error_code="IMAGE_COMPLIANCE_ERROR",
            details={"reason": reason},
        )


# ============================================================================
# PublishAgent Exceptions
# ============================================================================


class PublishException(CrewException):
    """Base exception for publish-related errors."""


class CookieExpiredError(PublishException):
    """Platform cookie expired."""

    def __init__(self, platform: str):
        super().__init__(
            message=f"{platform} 登录已过期，请重新登录",
            error_code="COOKIE_EXPIRED",
            details={"platform": platform},
        )


class CaptchaRequiredError(PublishException):
    """Platform requires captcha."""

    def __init__(self, platform: str):
        super().__init__(
            message=f"{platform} 需要验证码，请手动登录",
            error_code="CAPTCHA_REQUIRED",
            details={"platform": platform},
        )


class PublishRateLimitError(PublishException):
    """Publish rate limit exceeded."""

    def __init__(self, platform: str, min_interval: int):
        super().__init__(
            message=f"{platform} 发布频率过快，最小间隔 {min_interval} 秒",
            error_code="PUBLISH_RATE_LIMIT",
            details={"platform": platform, "min_interval": min_interval},
        )


class ContentRejectedError(PublishException):
    """Content rejected by platform."""

    def __init__(self, platform: str, reason: str):
        super().__init__(
            message=f"{platform} 拒绝发布: {reason}",
            error_code="CONTENT_REJECTED",
            details={"platform": platform, "reason": reason},
        )


class BrowserCrashError(PublishException):
    """Browser process crashed."""

    def __init__(self):
        super().__init__(
            message="浏览器进程崩溃",
            error_code="BROWSER_CRASH",
            details={},
        )


class ElementNotFoundError(PublishException):
    """Page element not found (platform UI may have changed)."""

    def __init__(self, selector: str, platform: str, screenshot_path: str):
        super().__init__(
            message=f"{platform} 页面元素未找到（可能平台 UI 改版）",
            error_code="ELEMENT_NOT_FOUND",
            details={
                "selector": selector,
                "platform": platform,
                "screenshot_path": screenshot_path,
            },
        )


class NetworkTimeoutError(CrewException):
    """Network request timeout."""

    def __init__(self, url: str, timeout: int):
        super().__init__(
            message=f"网络请求超时（URL: {url}, 超时: {timeout}秒）",
            error_code="NETWORK_TIMEOUT",
            details={"url": url, "timeout": timeout},
        )


# ============================================================================
# AnalyticsAgent Exceptions
# ============================================================================


class AnalyticsException(CrewException):
    """Base exception for analytics-related errors."""


class ContentNotFoundError(AnalyticsException):
    """Content not found (may be deleted)."""

    def __init__(self, content_id: str, platform: str):
        super().__init__(
            message=f"内容已被删除（ID: {content_id}, 平台: {platform}）",
            error_code="CONTENT_NOT_FOUND",
            details={"content_id": content_id, "platform": platform},
        )


class DataFormatError(AnalyticsException):
    """Data format changed (platform API may have changed)."""

    def __init__(self, platform: str, raw_data: str):
        super().__init__(
            message=f"{platform} 数据格式变更（可能 API 改版）",
            error_code="DATA_FORMAT_ERROR",
            details={"platform": platform, "raw_data": raw_data[:500]},
        )


# ============================================================================
# Database Exceptions
# ============================================================================


class DatabaseException(CrewException):
    """Base exception for database-related errors."""


class IntegrityError(DatabaseException):
    """Database integrity constraint violated."""

    def __init__(self, constraint: str):
        super().__init__(
            message=f"数据库约束冲突: {constraint}",
            error_code="INTEGRITY_ERROR",
            details={"constraint": constraint},
        )


class PoolExhaustedError(DatabaseException):
    """Database connection pool exhausted."""

    def __init__(self, pool_size: int):
        super().__init__(
            message=f"数据库连接池耗尽（池大小: {pool_size}）",
            error_code="POOL_EXHAUSTED",
            details={"pool_size": pool_size},
        )


class DeadlockError(DatabaseException):
    """Database deadlock detected."""

    def __init__(self):
        super().__init__(
            message="数据库死锁",
            error_code="DEADLOCK",
            details={},
        )
