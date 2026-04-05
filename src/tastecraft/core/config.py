"""TasteCraft application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default paths
DEFAULT_HOME = Path.home() / ".tastecraft"
DEFAULT_DB_NAME = "tastecraft.db"


class Settings(BaseSettings):
    """Global application settings loaded from env vars and config.yaml."""

    model_config = SettingsConfigDict(
        env_prefix="TASTECRAFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    home_dir: Path = Field(default_factory=lambda: DEFAULT_HOME)

    # LLM
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    max_turns: int = 20

    # Database
    database_url: str = ""

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    # Scheduler
    timezone: str = "Asia/Shanghai"

    # Browser / Playwright
    playwright_headless: bool = True
    playwright_timeout: int = 30000

    # Feishu notification
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_webhook_url: str = ""

    def model_post_init(self, __context: Any) -> None:
        """Set derived defaults after init."""
        if not self.database_url:
            db_path = self.home_dir / "data" / DEFAULT_DB_NAME
            self.database_url = f"sqlite+aiosqlite:///{db_path}"
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def projects_dir(self) -> Path:
        return self.home_dir / "projects"

    @property
    def logs_dir(self) -> Path:
        return self.home_dir / "logs"

    @property
    def data_dir(self) -> Path:
        return self.home_dir / "data"

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for d in [self.home_dir, self.projects_dir, self.logs_dir, self.data_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def load_global_config(self) -> dict[str, Any]:
        """Load ~/.tastecraft/config.yaml if it exists."""
        config_path = self.home_dir / "config.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_active_project(self) -> str | None:
        """Read the currently active project from marker file."""
        marker = self.home_dir / "current_project"
        if marker.exists():
            return marker.read_text(encoding="utf-8").strip()
        return None

    def set_active_project(self, project_id: str) -> None:
        """Set the currently active project."""
        self.ensure_dirs()
        marker = self.home_dir / "current_project"
        marker.write_text(project_id, encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings singleton."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
