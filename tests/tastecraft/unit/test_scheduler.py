"""Tests for Scheduler — pipeline field mapping from schedule.yaml."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path / "test-project"


@pytest.fixture
def mock_settings(project_dir):
    settings = MagicMock()
    settings.project_dir.return_value = project_dir
    settings.projects_dir = project_dir.parent
    settings.logs_dir = project_dir / "logs"
    settings.timezone = "UTC"
    return settings


def _write_schedule(project_dir: Path, schedules: dict) -> None:
    """Helper to write a schedule.yaml file."""
    project_dir.mkdir(parents=True, exist_ok=True)
    with (project_dir / "schedule.yaml").open("w") as f:
        yaml.dump({"schedules": schedules}, f)


class TestLoadScheduleRules:
    """Verify load_schedule_rules reads pipeline field correctly."""

    @patch("tastecraft.services.scheduler.get_settings")
    def test_default_schedule_when_no_file(self, mock_get_settings, mock_settings, project_dir):
        """Returns default schedule when no schedule.yaml exists."""
        mock_get_settings.return_value = mock_settings

        from tastecraft.services.scheduler import load_schedule_rules

        rules = load_schedule_rules("test-project")
        pipelines = [r["pipeline"] for r in rules]
        assert "content" in pipelines
        assert "publish" in pipelines
        assert "analytics" in pipelines
        assert "evolution" in pipelines
        assert "trending" in pipelines

    @patch("tastecraft.services.scheduler.get_settings")
    def test_pipeline_field_overrides_name(self, mock_get_settings, mock_settings, project_dir):
        """Entry name 'content-pipeline' with pipeline='content' maps correctly."""
        mock_get_settings.return_value = mock_settings
        _write_schedule(project_dir, {
            "content-pipeline": {
                "cron": "0 9 * * *",
                "pipeline": "content",
                "enabled": True,
            },
        })

        from tastecraft.services.scheduler import load_schedule_rules

        rules = load_schedule_rules("test-project")
        assert len(rules) == 1
        assert rules[0]["name"] == "content-pipeline"
        assert rules[0]["pipeline"] == "content"
        assert rules[0]["cron"] == "0 9 * * *"

    @patch("tastecraft.services.scheduler.get_settings")
    def test_multiple_entries_same_pipeline(self, mock_get_settings, mock_settings, project_dir):
        """Multiple publish-batch entries all map to 'publish' pipeline."""
        mock_get_settings.return_value = mock_settings
        _write_schedule(project_dir, {
            "publish-batch-1": {
                "cron": "0 12 * * *",
                "pipeline": "publish",
                "enabled": True,
            },
            "publish-batch-2": {
                "cron": "0 18 * * *",
                "pipeline": "publish",
                "enabled": True,
            },
            "publish-batch-3": {
                "cron": "0 21 * * *",
                "pipeline": "publish",
                "enabled": True,
            },
        })

        from tastecraft.services.scheduler import load_schedule_rules

        rules = load_schedule_rules("test-project")
        assert len(rules) == 3
        assert all(r["pipeline"] == "publish" for r in rules)
        crons = [r["cron"] for r in rules]
        assert "0 12 * * *" in crons
        assert "0 18 * * *" in crons
        assert "0 21 * * *" in crons

    @patch("tastecraft.services.scheduler.get_settings")
    def test_disabled_entries_excluded(self, mock_get_settings, mock_settings, project_dir):
        """Disabled entries are not included in rules."""
        mock_get_settings.return_value = mock_settings
        _write_schedule(project_dir, {
            "content": {
                "cron": "0 9 * * *",
                "pipeline": "content",
                "enabled": True,
            },
            "evolution": {
                "cron": "0 22 * * 0",
                "pipeline": "evolution",
                "enabled": False,
            },
        })

        from tastecraft.services.scheduler import load_schedule_rules

        rules = load_schedule_rules("test-project")
        assert len(rules) == 1
        assert rules[0]["pipeline"] == "content"

    @patch("tastecraft.services.scheduler.get_settings")
    def test_fallback_to_name_when_no_pipeline_field(self, mock_get_settings, mock_settings, project_dir):
        """When no 'pipeline' field, entry name is used as pipeline."""
        mock_get_settings.return_value = mock_settings
        _write_schedule(project_dir, {
            "analytics": {
                "cron": "0 23 * * *",
                "enabled": True,
            },
        })

        from tastecraft.services.scheduler import load_schedule_rules

        rules = load_schedule_rules("test-project")
        assert len(rules) == 1
        assert rules[0]["pipeline"] == "analytics"


class TestExportCron:
    """Verify export_cron uses pipeline field for CLI commands."""

    @patch("tastecraft.services.scheduler.get_settings")
    def test_export_uses_pipeline_command(self, mock_get_settings, mock_settings, project_dir):
        """Cron entries use the pipeline name, not the entry name, for CLI commands."""
        mock_get_settings.return_value = mock_settings
        _write_schedule(project_dir, {
            "content-pipeline": {
                "cron": "0 9 * * *",
                "pipeline": "content",
                "enabled": True,
            },
        })

        from tastecraft.services.scheduler import export_cron

        output = export_cron("test-project")
        assert "tastecraft run content" in output
        # The CLI command uses "content" (pipeline), not "content-pipeline" (entry name)
        import re
        cmd_lines = [ln for ln in output.split("\n") if "tastecraft run" in ln]
        assert len(cmd_lines) == 1
        assert re.search(r"tastecraft run content\b", cmd_lines[0])
