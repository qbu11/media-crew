"""
Audit Logging Module

提供安全审计日志功能，记录关键操作。
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型。"""

    # 认证相关
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"

    # 内容相关
    CONTENT_CREATE = "content_create"
    CONTENT_UPDATE = "content_update"
    CONTENT_DELETE = "content_delete"
    CONTENT_PUBLISH = "content_publish"
    CONTENT_APPROVE = "content_approve"
    CONTENT_REJECT = "content_reject"

    # 平台相关
    PLATFORM_CONNECT = "platform_connect"
    PLATFORM_DISCONNECT = "platform_disconnect"
    PLATFORM_PUBLISH = "platform_publish"
    PLATFORM_PUBLISH_FAILED = "platform_publish_failed"

    # 系统相关
    API_KEY_GENERATED = "api_key_generated"
    SETTINGS_CHANGED = "settings_changed"
    BULK_OPERATION = "bulk_operation"

    # 异常相关
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ERROR_OCCURRED = "error_occurred"


class AuditSeverity(str, Enum):
    """审计严重程度。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件。"""

    event_type: AuditEventType
    severity: AuditSeverity
    user_id: str | None
    ip_address: str | None
    user_agent: str | None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    request_id: str | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "session_id": self.session_id,
        }

    def to_json(self) -> str:
        """转换为 JSON。"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    审计日志记录器。

    Usage:
        audit = AuditLogger()

        # 记录用户登录
        audit.log(
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            user_id="user-001",
            ip_address="192.168.1.1",
            details={"method": "password"},
        )
    """

    def __init__(
        self,
        enabled: bool = True,
        log_to_file: bool = True,
        log_file: str = "logs/audit.log",
    ):
        self.enabled = enabled
        self.log_to_file = log_to_file
        self.log_file = log_file

        if log_to_file:
            # 确保日志目录存在
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        记录审计事件。

        Args:
            event_type: 事件类型
            severity: 严重程度
            user_id: 用户 ID
            ip_address: IP 地址
            user_agent: 用户代理
            resource_type: 资源类型
            resource_id: 资源 ID
            action: 操作描述
            details: 详细信息
            request_id: 请求 ID
            session_id: 会话 ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            request_id=request_id,
            session_id=session_id,
        )

        # 记录到标准日志
        log_message = f"[AUDIT] {event.to_json()}"

        if severity == AuditSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == AuditSeverity.ERROR:
            logger.error(log_message)
        elif severity == AuditSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 记录到文件
        if self.log_to_file:
            self._write_to_file(event)

    def _write_to_file(self, event: AuditEvent) -> None:
        """写入文件。"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    # =========================================================================
    # 便捷方法
    # =========================================================================

    def log_login(
        self,
        user_id: str,
        ip_address: str | None = None,
        method: str = "password",
        success: bool = True,
    ) -> None:
        """记录登录事件。"""
        self.log(
            event_type=AuditEventType.USER_LOGIN if success else AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id if success else None,
            ip_address=ip_address,
            details={"method": method, "success": success},
        )

    def log_logout(self, user_id: str, ip_address: str | None = None) -> None:
        """记录登出事件。"""
        self.log(
            event_type=AuditEventType.USER_LOGOUT,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
        )

    def log_content_operation(
        self,
        operation: str,
        user_id: str,
        content_id: str,
        platform: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录内容操作。"""
        event_map = {
            "create": AuditEventType.CONTENT_CREATE,
            "update": AuditEventType.CONTENT_UPDATE,
            "delete": AuditEventType.CONTENT_DELETE,
            "publish": AuditEventType.CONTENT_PUBLISH,
            "approve": AuditEventType.CONTENT_APPROVE,
            "reject": AuditEventType.CONTENT_REJECT,
        }

        self.log(
            event_type=event_map.get(operation, AuditEventType.CONTENT_UPDATE),
            severity=AuditSeverity.INFO,
            user_id=user_id,
            resource_type="content",
            resource_id=content_id,
            action=operation,
            details={"platform": platform, **(details or {})},
        )

    def log_platform_operation(
        self,
        operation: str,
        user_id: str,
        platform: str,
        success: bool = True,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录平台操作。"""
        event_map = {
            "connect": AuditEventType.PLATFORM_CONNECT,
            "disconnect": AuditEventType.PLATFORM_DISCONNECT,
            "publish": AuditEventType.PLATFORM_PUBLISH if success else AuditEventType.PLATFORM_PUBLISH_FAILED,
        }

        self.log(
            event_type=event_map.get(operation, AuditEventType.PLATFORM_CONNECT),
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
            user_id=user_id,
            resource_type="platform",
            resource_id=platform,
            action=operation,
            details={
                "success": success,
                "error": error,
                **(details or {}),
            },
        )

    def log_suspicious_activity(
        self,
        user_id: str | None,
        ip_address: str | None,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录可疑活动。"""
        self.log(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            details={"reason": reason, **(details or {})},
        )

    def log_rate_limit_exceeded(
        self,
        ip_address: str | None,
        endpoint: str,
        limit: int,
        current: int,
    ) -> None:
        """记录速率限制超出。"""
        self.log(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.WARNING,
            ip_address=ip_address,
            details={
                "endpoint": endpoint,
                "limit": limit,
                "current": current,
            },
        )


# 全局审计日志实例
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志实例。"""
    global _audit_logger
    if _audit_logger is None:
        from src.core.config import settings
        _audit_logger = AuditLogger(
            enabled=settings.get("AUDIT_LOGGING_ENABLED", True),
            log_file=settings.get("LOG_FILE", "logs/audit.log"),
        )
    return _audit_logger


def audit_log(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.INFO,
    **kwargs,
) -> None:
    """便捷函数：记录审计日志。"""
    get_audit_logger().log(event_type, severity, **kwargs)
