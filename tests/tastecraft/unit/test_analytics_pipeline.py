"""Tests for Analytics Pipeline — output parsing instead of result.data."""

from __future__ import annotations

from tastecraft.pipelines.analytics import _parse_metrics


class TestParseMetrics:
    """Verify _parse_metrics extracts metrics from various output formats."""

    def test_parse_json_block(self):
        """Parse metrics from ```json ... ``` block."""
        output = (
            "Here are the metrics:\n"
            "```json\n"
            '{"views": 1500, "likes": 120, "comments": 30, "shares": 15, '
            '"saves": 45, "new_followers": 5, "engagement_rate": 0.08}\n'
            "```\n"
            "The content performed well."
        )
        metrics = _parse_metrics(output)
        assert metrics["views"] == 1500
        assert metrics["likes"] == 120
        assert metrics["engagement_rate"] == 0.08

    def test_parse_raw_json(self):
        """Parse metrics from raw JSON output."""
        output = '{"views": 500, "likes": 40, "comments": 10}'
        metrics = _parse_metrics(output)
        assert metrics["views"] == 500
        assert metrics["likes"] == 40

    def test_parse_embedded_json(self):
        """Parse metrics from JSON embedded in text."""
        output = (
            'The metrics are: {"views": 200, "likes": 15, "comments": 3} '
            "and the content is doing okay."
        )
        metrics = _parse_metrics(output)
        assert metrics["views"] == 200

    def test_parse_failure_returns_empty(self):
        """Return empty dict when no JSON found."""
        output = "No metrics available at this time."
        metrics = _parse_metrics(output)
        assert metrics == {}

    def test_parse_empty_string(self):
        """Return empty dict for empty string."""
        metrics = _parse_metrics("")
        assert metrics == {}

    def test_no_attribute_error_on_agent_result(self):
        """AgentResult has no .data attribute — verify we don't use it."""
        from tastecraft.core.agent_loop import AgentResult

        result = AgentResult(success=True, output='{"views": 100}')
        assert not hasattr(result, "data")
        # Our code should use result.output, not result.data
        metrics = _parse_metrics(result.output)
        assert metrics["views"] == 100
