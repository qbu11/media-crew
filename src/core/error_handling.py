"""
Error handling utilities for Crew Media Ops.

提供统一的错误处理、重试逻辑和 Result 类型。
"""

from collections.abc import Callable
import functools
import logging
import random
import time
from typing import Any, Generic, TypeVar, Union

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.exceptions import (
    BrowserCrashError,
    CrewException,
    DeadlockError,
    LLMTimeoutError,
    NetworkTimeoutError,
    PoolExhaustedError,
    RateLimitError,
    TimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Result Types (代替异常抛出，提供更清晰的错误处理)
# ============================================================================


class Success(Generic[T]):
    """成功结果。"""

    def __init__(self, data: T):
        self.data = data
        self.success = True
        self.error: str | None = None
        self.error_code: str | None = None

    def __repr__(self) -> str:
        return f"Success(data={self.data!r})"


class Error:
    """错误结果。"""

    def __init__(
        self,
        error: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ):
        self.data: Any = None
        self.success = False
        self.error = error
        self.error_code = error_code
        self.details = details or {}

    def __repr__(self) -> str:
        return f"Error(error={self.error!r}, error_code={self.error_code!r})"


Result = Union[Success[T], Error]  # noqa: UP007


def success(data: T) -> Success[T]:
    """创建成功结果。"""
    return Success(data)


def error(
    message: str,
    error_code: str,
    details: dict[str, Any] | None = None,
) -> Error:
    """创建错误结果。"""
    return Error(message, error_code, details)


def from_exception(exc: CrewException) -> Error:
    """从异常创建错误结果。"""
    return Error(
        error=exc.message,
        error_code=exc.error_code,
        details=exc.details,
    )


# ============================================================================
# Retry Decorators (统一的错误处理)
# ============================================================================


def retry_on_transient(
    max_attempts: int = 3,
    min_wait: float = 2,
    max_wait: float = 30,
):
    """
    对瞬态错误进行重试。

    适用于：网络超时、API 限流、连接池耗尽等。
    """
    return retry(
        retry=retry_if_exception_type((
            TimeoutError,
            NetworkTimeoutError,
            RateLimitError,
            PoolExhaustedError,
            DeadlockError,
            LLMTimeoutError,
            BrowserCrashError,
        )),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"重试 {retry_state.attempt_number}/{max_attempts}: {retry_state.outcome.exception()}"
        ),
    )


def retry_on_llm_error(max_attempts: int = 3):
    """
    对 LLM 错误进行重试。
    """
    return retry(
        retry=retry_if_exception_type((LLMTimeoutError,)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )


# ============================================================================
# Jitter for Rate Limiting
# ============================================================================


def jitter(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """添加随机延迟，避免请求同步。"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


# ============================================================================
# Safe Execute Wrapper
# ============================================================================


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: T | None = None,  # noqa: ARG001
    log_errors: bool = True,
    **kwargs: Any,
) -> Result[T]:
    """
    安全执行函数，捕获所有异常并返回 Result。

    Args:
        func: 要执行的函数
        *args: 位置参数
        default: 发生错误时的默认返回值
        log_errors: 是否记录错误日志
        **kwargs: 关键字参数

    Returns:
        Result[T]: 成功或错误结果
    """
    try:
        result = func(*args, **kwargs)
        return success(result)
    except CrewException as e:
        if log_errors:
            logger.error(f"业务异常: {e.message}", extra=e.details)
        return from_exception(e)
    except Exception as e:
        if log_errors:
            logger.exception(f"未预期的异常: {e}")
        return error(str(e), "UNEXPECTED_ERROR")


async def safe_execute_async(
    func: Callable[..., T],
    *args: Any,
    default: T | None = None,  # noqa: ARG001
    log_errors: bool = True,
    **kwargs: Any,
) -> Result[T]:
    """
    安全执行异步函数，捕获所有异常并返回 Result。
    """
    try:
        result = await func(*args, **kwargs)
        return success(result)
    except CrewException as e:
        if log_errors:
            logger.error(f"业务异常: {e.message}", extra=e.details)
        return from_exception(e)
    except Exception as e:
        if log_errors:
            logger.exception(f"未预期的异常: {e}")
        return error(str(e), "UNEXPECTED_ERROR")


# ============================================================================
# Error Context Manager
# ============================================================================


class ErrorContext:
    """
    错误上下文管理器，用于包装可能失败的操作。

    Usage:
        with ErrorContext("fetch_hotspots", platform="weibo") as ctx:
            data = fetch_data()
            ctx.result = data

        if ctx.success:
            print(ctx.result)
        else:
            print(ctx.error)
    """

    def __init__(self, operation: str, **context: Any):
        self.operation = operation
        self.context = context
        self.result: Any = None
        self.success = True
        self.error: str | None = None
        self.error_code: str | None = None

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            self.success = False
            if isinstance(exc_val, CrewException):
                self.error = exc_val.message
                self.error_code = exc_val.error_code
                logger.error(
                    f"[{self.operation}] 业务异常: {self.error}",
                    extra={**self.context, **exc_val.details},
                )
            else:
                self.error = str(exc_val)
                self.error_code = "UNEXPECTED_ERROR"
                logger.exception(
                    f"[{self.operation}] 未预期的异常: {self.error}",
                    extra=self.context,
                )
            return True  # 抑制异常
        return False


# ============================================================================
# Fallback Decorator
# ============================================================================


def fallback(fallback_func: Callable[..., T]):
    """
    装饰器：主函数失败时调用备用函数。

    Usage:
        @fallback(lambda: "default content")
        def generate_content():
            raise LLMTimeoutError("claude", 30)

        result = generate_content()  # 返回 "default content"
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"主函数 {func.__name__} 失败，调用备用函数: {e}"
                )
                return fallback_func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Circuit Breaker (熔断器)
# ============================================================================


class CircuitBreaker:
    """
    熔断器：防止级联故障。

    当连续失败次数达到阈值时，熔断器打开，后续请求直接失败。
    经过冷却时间后，熔断器进入半开状态，允许一个请求通过。
    如果成功，熔断器关闭；如果失败，熔断器重新打开。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.is_open = False

    def record_success(self) -> None:
        """记录成功。"""
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        """记录失败。"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True

    def can_execute(self) -> bool:
        """检查是否可以执行。"""
        if not self.is_open:
            return True

        # 检查是否过了恢复时间
        if self.last_failure_time is not None:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                # 进入半开状态
                return True

        return False

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器模式。"""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.can_execute():
                raise CrewException(
                    message="服务熔断中，请稍后重试",
                    error_code="CIRCUIT_BREAKER_OPEN",
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception:
                self.record_failure()
                raise

        return wrapper
