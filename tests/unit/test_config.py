"""Configuration tests."""

import os

import pytest

from src.core.config import Settings, get_settings


@pytest.mark.unit
def test_default_settings(monkeypatch) -> None:
    """Default settings load correctly."""
    # Clear environment variables that may override defaults
    for key in ["API_PORT", "CREW_MAX_ITER", "DEFAULT_LANGUAGE", "APP_ENV"]:
        monkeypatch.delenv(key, raising=False)

    s = Settings()
    assert s.APP_ENV == "development"
    assert s.API_PORT == 8000
    assert s.CREW_MAX_ITER == 15
    assert s.DEFAULT_LANGUAGE == "zh-CN"


@pytest.mark.unit
def test_get_settings_returns_instance() -> None:
    """get_settings returns a Settings instance."""
    s = get_settings()
    assert isinstance(s, Settings)
