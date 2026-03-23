"""
Authentication and Authorization Module

提供 JWT 认证、用户管理和权限检查。
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import logging
import secrets
import time
from typing import Any

from cryptography.fernet import Fernet
import orjson
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# User Models
# ============================================================================


class UserRole(str, Enum):
    """用户角色。"""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


@dataclass
class User:
    """用户信息。"""

    id: str
    username: str
    role: UserRole = UserRole.USER
    created_at: float = field(default_factory=time.time)
    last_login: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_publish(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.USER)

    def can_delete(self) -> bool:
        return self.role == UserRole.ADMIN


# ============================================================================
# JWT Token Management
# ============================================================================


class TokenPayload(BaseModel):
    """JWT Token 载荷。"""

    sub: str  # user_id
    username: str
    role: UserRole
    iat: float = Field(default_factory=time.time)
    exp: float

    def is_expired(self) -> bool:
        return time.time() > self.exp


class JWTManager:
    """
    JWT Token 管理器。

    使用 HMAC-SHA256 签名（简化实现，生产环境建议使用 PyJWT）。
    """

    def __init__(self, secret_key: str, expires_in: int = 3600):
        """
        Args:
            secret_key: 签名密钥
            expires_in: Token 有效期（秒）
        """
        self.secret_key = secret_key
        self.expires_in = expires_in

    def create_token(self, user: User) -> str:
        """创建 JWT Token。"""
        payload = TokenPayload(
            sub=user.id,
            username=user.username,
            role=user.role,
            iat=time.time(),
            exp=time.time() + self.expires_in,
        )

        # 编码载荷
        payload_bytes = orjson.dumps(payload.model_dump())
        payload_b64 = self._base64_encode(payload_bytes)

        # 生成签名
        signature = self._sign(payload_b64)

        return f"{payload_b64}.{signature}"

    def verify_token(self, token: str) -> TokenPayload | None:
        """验证 JWT Token。"""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None

            payload_b64, signature = parts

            # 验证签名
            expected_signature = self._sign(payload_b64)
            if not secrets.compare_digest(signature, expected_signature):
                logger.warning("Token 签名验证失败")
                return None

            # 解码载荷
            payload_bytes = self._base64_decode(payload_b64)
            payload_dict = orjson.loads(payload_bytes)
            payload = TokenPayload(**payload_dict)

            # 检查过期
            if payload.is_expired():
                logger.warning("Token 已过期")
                return None

            return payload

        except Exception as e:
            logger.error(f"Token 验证失败: {e}")
            return None

    def _sign(self, data: str) -> str:
        """签名数据。"""
        signature = hashlib.sha256(
            f"{data}{self.secret_key}".encode()
        ).hexdigest()
        return signature[:32]  # 取前 32 字符

    @staticmethod
    def _base64_encode(data: bytes) -> str:
        """Base64 URL 安全编码。"""
        import base64

        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def _base64_decode(data: str) -> bytes:
        """Base64 URL 安全解码。"""
        import base64

        # 补齐 padding
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)


# ============================================================================
# Sensitive Data Encryption
# ============================================================================


class EncryptionManager:
    """
    敏感数据加密管理器。

    使用 Fernet (AES-128-CBC) 对称加密。
    """

    def __init__(self, encryption_key: str | None = None):
        """
        Args:
            encryption_key: 加密密钥（Base64 编码的 Fernet key）
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # 生成新密钥
            self.key = Fernet.generate_key()

        self.cipher = Fernet(self.key)

    def encrypt(self, plaintext: str) -> str:
        """加密字符串。"""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密字符串。"""
        if not ciphertext:
            return ""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ""

    def encrypt_dict(self, data: dict[str, Any]) -> str:
        """加密字典。"""
        json_str = orjson.dumps(data).decode()
        return self.encrypt(json_str)

    def decrypt_dict(self, ciphertext: str) -> dict[str, Any]:
        """解密字典。"""
        json_str = self.decrypt(ciphertext)
        if not json_str:
            return {}
        return orjson.loads(json_str)


# ============================================================================
# Cookie Manager (加密存储平台 Cookie)
# ============================================================================


@dataclass
class EncryptedCookie:
    """加密存储的 Cookie。"""

    platform: str
    encrypted_data: str
    created_at: float
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CookieManager:
    """
    平台 Cookie 管理器。

    安全存储和管理各平台的登录 Cookie。
    """

    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager
        self._cookies: dict[str, EncryptedCookie] = {}

    def store_cookie(
        self,
        platform: str,
        cookie_data: str,
        expires_in: int | None = None,
    ) -> None:
        """
        存储 Cookie。

        Args:
            platform: 平台名称
            cookie_data: Cookie 字符串
            expires_in: 有效期（秒）
        """
        encrypted_data = self.encryption.encrypt(cookie_data)

        expires_at = None
        if expires_in:
            expires_at = time.time() + expires_in

        self._cookies[platform] = EncryptedCookie(
            platform=platform,
            encrypted_data=encrypted_data,
            created_at=time.time(),
            expires_at=expires_at,
        )

        logger.info(f"存储 {platform} Cookie 成功")

    def get_cookie(self, platform: str) -> str | None:
        """
        获取 Cookie。

        Returns:
            Cookie 字符串，如果不存在或已过期则返回 None
        """
        cookie = self._cookies.get(platform)
        if cookie is None:
            logger.warning(f"{platform} Cookie 不存在")
            return None

        if cookie.is_expired():
            logger.warning(f"{platform} Cookie 已过期")
            del self._cookies[platform]
            return None

        return self.encryption.decrypt(cookie.encrypted_data)

    def remove_cookie(self, platform: str) -> bool:
        """删除 Cookie。"""
        if platform in self._cookies:
            del self._cookies[platform]
            logger.info(f"删除 {platform} Cookie")
            return True
        return False

    def list_platforms(self) -> list[str]:
        """列出所有有 Cookie 的平台。"""
        # 过滤过期的
        valid_platforms = []
        for platform, cookie in list(self._cookies.items()):
            if cookie.is_expired():
                del self._cookies[platform]
            else:
                valid_platforms.append(platform)
        return valid_platforms


# ============================================================================
# Authentication Middleware
# ============================================================================


class AuthContext:
    """认证上下文，存储当前用户信息。"""

    _current_user: User | None = None

    @classmethod
    def set_user(cls, user: User) -> None:
        cls._current_user = user

    @classmethod
    def get_user(cls) -> User | None:
        return cls._current_user

    @classmethod
    def clear(cls) -> None:
        cls._current_user = None


def require_auth(required_role: UserRole | None = None):
    """
    认证装饰器。

    Usage:
        @require_auth()
        def protected_endpoint():
            user = AuthContext.get_user()
            return {"user": user.username}

        @require_auth(required_role=UserRole.ADMIN)
        def admin_endpoint():
            return {"message": "Admin only"}
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = AuthContext.get_user()
            if user is None:
                from src.core.exceptions import AuthenticationError

                raise AuthenticationError("需要登录")

            if required_role and user.role != required_role:
                from src.core.exceptions import CrewException

                raise CrewException(
                    message="权限不足",
                    error_code="FORBIDDEN",
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# API Key Manager (用于内部服务调用)
# ============================================================================


class APIKeyManager:
    """
    API Key 管理器。

    用于验证内部服务调用的 API Key。
    """

    def __init__(self, valid_keys: set[str]):
        """
        Args:
            valid_keys: 有效的 API Key 集合
        """
        self.valid_keys = valid_keys

    def validate(self, api_key: str) -> bool:
        """
        验证 API Key。

        使用常量时间比较防止时序攻击。
        """
        return any(secrets.compare_digest(api_key, valid_key) for valid_key in self.valid_keys)

    def generate_key(self) -> str:
        """生成新的 API Key。"""
        return secrets.token_urlsafe(32)
