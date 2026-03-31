"""
Unit tests for base_tool module.

Tests cover:
- ToolResult: to_dict(), is_success(), is_failed()
- ToolError: __init__, to_result()
- BaseTool: validate_input(), check_rate_limit(), pre_execute(), post_execute(), run(), get_metadata()
- ConfigurableTool: _load_config() with env vars, missing keys, get_config_value()
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.tools.base_tool import BaseTool, ConfigurableTool, ToolError, ToolResult, ToolStatus


# ---------------------------------------------------------------------------
# Concrete subclass used throughout the tests
# ---------------------------------------------------------------------------
class DummyTool(BaseTool):
    """Concrete subclass of BaseTool for testing."""

    name = "dummy_tool"
    description = "A dummy tool for testing"
    platform = "test"
    version = "1.0.0"

    max_requests_per_minute = 3
    min_interval_seconds = 2.0

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "default")
        if action == "fail":
            return ToolResult(status=ToolStatus.FAILED, error="intentional failure", platform=self.platform)
        if action == "raise":
            raise ValueError("unexpected boom")
        if action == "tool_error":
            raise ToolError("tool-level error", platform=self.platform, details={"code": 42})
        return ToolResult(status=ToolStatus.SUCCESS, data={"action": action}, platform=self.platform)


class DummyConfigurableTool(ConfigurableTool):
    """Concrete subclass of ConfigurableTool for testing."""

    name = "dummy_configurable"
    platform = "testplatform"
    required_config_keys = ["api_key", "secret"]

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(status=ToolStatus.SUCCESS, data={"ok": True})


# ===========================================================================
# ToolResult tests
# ===========================================================================
class TestToolResult:
    """Tests for the ToolResult dataclass."""

    def test_to_dict_contains_all_keys(self):
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            data={"k": "v"},
            error=None,
            platform="weibo",
            content_id="c123",
            metadata={"extra": 1},
        )
        d = result.to_dict()
        assert d["status"] == "success"
        assert d["data"] == {"k": "v"}
        assert d["error"] is None
        assert d["platform"] == "weibo"
        assert d["content_id"] == "c123"
        assert d["metadata"] == {"extra": 1}
        # timestamp must be an ISO string
        assert isinstance(d["timestamp"], str)

    def test_to_dict_failed_status(self):
        result = ToolResult(status=ToolStatus.FAILED, error="oops")
        d = result.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "oops"

    def test_is_success_true(self):
        assert ToolResult(status=ToolStatus.SUCCESS).is_success() is True

    def test_is_success_false_for_failed(self):
        assert ToolResult(status=ToolStatus.FAILED).is_success() is False

    def test_is_success_false_for_partial(self):
        assert ToolResult(status=ToolStatus.PARTIAL).is_success() is False

    def test_is_failed_true(self):
        assert ToolResult(status=ToolStatus.FAILED).is_failed() is True

    def test_is_failed_false_for_success(self):
        assert ToolResult(status=ToolStatus.SUCCESS).is_failed() is False

    def test_is_failed_false_for_pending(self):
        assert ToolResult(status=ToolStatus.PENDING).is_failed() is False

    def test_default_values(self):
        result = ToolResult(status=ToolStatus.PENDING)
        assert result.data is None
        assert result.error is None
        assert result.platform is None
        assert result.content_id is None
        assert result.metadata == {}
        assert isinstance(result.timestamp, datetime)


# ===========================================================================
# ToolError tests
# ===========================================================================
class TestToolError:
    """Tests for the ToolError exception class."""

    def test_init_with_all_params(self):
        err = ToolError("msg", platform="xhs", details={"a": 1})
        assert err.message == "msg"
        assert err.platform == "xhs"
        assert err.details == {"a": 1}
        assert str(err) == "msg"

    def test_init_defaults(self):
        err = ToolError("simple")
        assert err.platform is None
        assert err.details == {}

    def test_to_result_returns_failed(self):
        err = ToolError("bad thing", platform="weibo", details={"code": 500})
        result = err.to_result()
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.FAILED
        assert result.error == "bad thing"
        assert result.platform == "weibo"
        assert result.metadata == {"code": 500}

    def test_is_exception(self):
        err = ToolError("test")
        assert isinstance(err, Exception)


# ===========================================================================
# BaseTool tests (via DummyTool)
# ===========================================================================
class TestBaseTool:
    """Tests for BaseTool abstract base class via DummyTool."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseTool()

    def test_init_with_config(self):
        tool = DummyTool(config={"key": "val"})
        assert tool.config == {"key": "val"}
        assert tool._last_execution is None
        assert tool._execution_count == 0

    def test_init_without_config(self):
        tool = DummyTool()
        assert tool.config == {}

    # -- validate_input --
    def test_validate_input_default_returns_true(self):
        tool = DummyTool()
        is_valid, err = tool.validate_input(anything="whatever")
        assert is_valid is True
        assert err is None

    # -- check_rate_limit --
    def test_check_rate_limit_allows_first_request(self):
        tool = DummyTool()
        allowed, err = tool.check_rate_limit()
        assert allowed is True
        assert err is None

    def test_check_rate_limit_denies_when_count_exceeded(self):
        tool = DummyTool()
        tool._execution_count = tool.max_requests_per_minute
        tool._execution_count_window = datetime.now()
        allowed, err = tool.check_rate_limit()
        assert allowed is False
        assert "Rate limit exceeded" in err

    def test_check_rate_limit_resets_after_window(self):
        tool = DummyTool()
        tool._execution_count = tool.max_requests_per_minute
        tool._execution_count_window = datetime.now() - timedelta(seconds=61)
        allowed, err = tool.check_rate_limit()
        assert allowed is True
        assert tool._execution_count == 0

    def test_check_rate_limit_denies_when_interval_not_met(self):
        tool = DummyTool()
        tool._last_execution = datetime.now()  # just executed
        allowed, err = tool.check_rate_limit()
        assert allowed is False
        assert "Minimum interval" in err

    def test_check_rate_limit_allows_after_interval(self):
        tool = DummyTool()
        tool._last_execution = datetime.now() - timedelta(seconds=10)
        allowed, err = tool.check_rate_limit()
        assert allowed is True

    # -- pre_execute --
    def test_pre_execute_returns_pending_when_ok(self):
        tool = DummyTool()
        result = tool.pre_execute()
        assert result.status == ToolStatus.PENDING

    def test_pre_execute_returns_failed_on_rate_limit(self):
        tool = DummyTool()
        tool._execution_count = tool.max_requests_per_minute
        tool._execution_count_window = datetime.now()
        result = tool.pre_execute()
        assert result.status == ToolStatus.FAILED
        assert "Rate limit" in result.error

    # -- post_execute --
    def test_post_execute_tracks_execution(self):
        tool = DummyTool()
        assert tool._execution_count == 0
        assert tool._last_execution is None

        result = ToolResult(status=ToolStatus.SUCCESS)
        tool.post_execute(result)

        assert tool._execution_count == 1
        assert tool._last_execution is not None

    def test_post_execute_returns_same_result(self):
        tool = DummyTool()
        original = ToolResult(status=ToolStatus.SUCCESS, data={"x": 1})
        returned = tool.post_execute(original)
        assert returned is original

    # -- run --
    def test_run_success(self):
        tool = DummyTool()
        result = tool.run(action="hello")
        assert result.is_success()
        assert result.data == {"action": "hello"}
        assert tool._execution_count == 1

    def test_run_handles_tool_error(self):
        tool = DummyTool()
        result = tool.run(action="tool_error")
        assert result.is_failed()
        assert "tool-level error" in result.error
        assert tool._execution_count == 1

    def test_run_handles_unexpected_exception(self):
        tool = DummyTool()
        result = tool.run(action="raise")
        assert result.is_failed()
        assert "Unexpected error" in result.error
        assert "unexpected boom" in result.error

    def test_run_blocked_by_rate_limit(self):
        tool = DummyTool()
        tool._execution_count = tool.max_requests_per_minute
        tool._execution_count_window = datetime.now()
        result = tool.run(action="hello")
        assert result.is_failed()
        assert "Rate limit" in result.error

    # -- get_metadata --
    def test_get_metadata_initial(self):
        tool = DummyTool()
        meta = tool.get_metadata()
        assert meta["name"] == "dummy_tool"
        assert meta["description"] == "A dummy tool for testing"
        assert meta["platform"] == "test"
        assert meta["version"] == "1.0.0"
        assert meta["rate_limit"]["max_requests_per_minute"] == 3
        assert meta["rate_limit"]["min_interval_seconds"] == 2.0
        assert meta["execution_count"] == 0
        assert meta["last_execution"] is None

    def test_get_metadata_after_execution(self):
        tool = DummyTool()
        tool.run()
        meta = tool.get_metadata()
        assert meta["execution_count"] == 1
        assert meta["last_execution"] is not None


# ===========================================================================
# ConfigurableTool tests
# ===========================================================================
class TestConfigurableTool:
    """Tests for ConfigurableTool._load_config and get_config_value."""

    def test_init_with_all_keys_provided(self):
        tool = DummyConfigurableTool(config={"api_key": "k", "secret": "s"})
        assert tool.config["api_key"] == "k"
        assert tool.config["secret"] == "s"

    def test_init_loads_missing_keys_from_env(self):
        with patch.dict("os.environ", {"TESTPLATFORM_API_KEY": "env_k", "TESTPLATFORM_SECRET": "env_s"}):
            tool = DummyConfigurableTool(config={})
        assert tool.config["api_key"] == "env_k"
        assert tool.config["secret"] == "env_s"

    def test_init_partial_env(self):
        """One key in config, other from env."""
        with patch.dict("os.environ", {"TESTPLATFORM_SECRET": "env_s"}):
            tool = DummyConfigurableTool(config={"api_key": "direct"})
        assert tool.config["api_key"] == "direct"
        assert tool.config["secret"] == "env_s"

    def test_init_raises_on_missing_keys(self):
        with patch.dict("os.environ", {}, clear=False):
            # Ensure the env vars are not present
            import os
            os.environ.pop("TESTPLATFORM_API_KEY", None)
            os.environ.pop("TESTPLATFORM_SECRET", None)
            with pytest.raises(ToolError) as exc_info:
                DummyConfigurableTool(config={})
            assert "api_key" in str(exc_info.value)

    def test_get_config_value_existing(self):
        tool = DummyConfigurableTool(config={"api_key": "k", "secret": "s", "extra": "e"})
        assert tool.get_config_value("extra") == "e"

    def test_get_config_value_missing_with_default(self):
        tool = DummyConfigurableTool(config={"api_key": "k", "secret": "s"})
        assert tool.get_config_value("nonexistent", "fallback") == "fallback"

    def test_get_config_value_missing_no_default(self):
        tool = DummyConfigurableTool(config={"api_key": "k", "secret": "s"})
        assert tool.get_config_value("nonexistent") is None
