"""
Integration tests for ContentCrew.

Tests cover:
- Crew creation and configuration
- Input validation
- Task generation
- End-to-end workflow with mocks
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.crew.crews.base_crew import CrewInput, CrewResult, CrewStatus
from src.crew.crews.content_crew import (
    ContentCrew,
    ContentCrewInput,
    ContentCrewResult,
)


class TestContentCrewInput:
    """Test cases for ContentCrewInput."""

    def test_content_crew_input_creation(self) -> None:
        """
        Test ContentCrewInput can be created with valid parameters.

        Arrange: Prepare valid input parameters
        Act: Create ContentCrewInput instance
        Assert: All parameters are stored correctly
        """
        crew_input = ContentCrewInput(
            industry="AI",
            keywords=["AI创业", "人工智能"],
            target_platform="xiaohongshu",
            content_type="article",
            research_depth="standard",
            enable_human_review=True,
        )

        assert crew_input.inputs["industry"] == "AI"
        assert crew_input.inputs["keywords"] == ["AI创业", "人工智能"]
        assert crew_input.inputs["target_platform"] == "xiaohongshu"
        assert crew_input.inputs["content_type"] == "article"
        assert crew_input.metadata["industry"] == "AI"

    def test_content_crew_input_to_dict(self) -> None:
        """
        Test ContentCrewInput.to_dict serialization.

        Arrange: Create ContentCrewInput
        Act: Call to_dict()
        Assert: Returns dictionary with all fields
        """
        crew_input = ContentCrewInput(
            industry="科技",
            keywords=["AI", "科技"],
            target_platform="wechat",
        )

        result = crew_input.to_dict()

        assert isinstance(result, dict)
        assert "inputs" in result
        assert "metadata" in result
        assert result["inputs"]["industry"] == "科技"

    def test_content_crew_input_from_dict(self) -> None:
        """
        Test ContentCrewInput.from_dict deserialization.

        Arrange: Prepare dictionary with input data
        Act: Call from_dict()
        Assert: Returns ContentCrewInput with correct values
        """
        data = {
            "inputs": {
                "industry": "电商",
                "keywords": ["直播", "带货"],
                "target_platform": "douyin",
            },
            "metadata": {"test": True},
        }

        crew_input = CrewInput.from_dict(data)

        assert crew_input.inputs["industry"] == "电商"
        assert crew_input.metadata.get("test") is True


class TestContentCrewResult:
    """Test cases for ContentCrewResult."""

    def test_content_crew_result_creation(self) -> None:
        """
        Test ContentCrewResult can be created with all fields.

        Arrange: Prepare result data
        Act: Create ContentCrewResult instance
        Assert: All fields are stored correctly
        """
        result = ContentCrewResult(
            status=CrewStatus.COMPLETED,
            topic_report={
                "title": "AI创业指南",
                "potential_score": 85.0,
            },
            content_draft={
                "title": "AI创业3年，我踩过的5个坑",
                "content": "详细内容...",
            },
            review_report={
                "result": "approved",
                "overall_score": 85.0,
            },
            execution_time=10.5,
        )

        assert result.status == CrewStatus.COMPLETED
        assert result.topic_report["title"] == "AI创业指南"
        assert result.content_draft["title"] == "AI创业3年，我踩过的5个坑"
        assert result.review_report["result"] == "approved"

    def test_content_crew_result_is_approved(self) -> None:
        """
        Test ContentCrewResult.is_approved property.

        Arrange: Create results with different review statuses
        Act: Check is_approved property
        Assert: Returns correct boolean values
        """
        approved_result = ContentCrewResult(
            status=CrewStatus.COMPLETED,
            review_report={"result": "approved"},
        )

        rejected_result = ContentCrewResult(
            status=CrewStatus.COMPLETED,
            review_report={"result": "rejected"},
        )

        no_review_result = ContentCrewResult(status=CrewStatus.COMPLETED)

        assert approved_result.is_approved is True
        assert rejected_result.is_approved is False
        assert no_review_result.is_approved is False


class TestContentCrew:
    """Test cases for ContentCrew."""

    def test_content_crew_creation(self) -> None:
        """
        Test ContentCrew can be created with default parameters.

        Arrange: None
        Act: Create ContentCrew instance
        Assert: Default parameters are set correctly
        """
        crew = ContentCrew()

        assert crew.get_crew_name() == "ContentProduction"
        assert "选题研究" in crew.get_description()
        assert crew.enable_human_review is True

    def test_content_crew_custom_parameters(self) -> None:
        """
        Test ContentCrew with custom parameters.

        Arrange: Prepare custom parameters
        Act: Create ContentCrew with custom settings
        Assert: Custom parameters are set correctly
        """
        crew = ContentCrew(
            verbose=False,
            memory=False,
            enable_human_review=False,
            llm="claude-opus-4-20250514",
        )

        assert crew.verbose is False
        assert crew.memory is False
        assert crew.enable_human_review is False
        assert crew.llm == "claude-opus-4-20250514"

    def test_content_crew_validate_inputs_valid(self) -> None:
        """
        Test ContentCrew.validate_inputs with valid data.

        Arrange: Create ContentCrew and valid input
        Act: Call validate_inputs()
        Assert: Returns (True, None)
        """
        crew = ContentCrew()
        crew_input = ContentCrewInput(
            industry="AI",
            keywords=["AI创业"],
            target_platform="xiaohongshu",
            content_type="article",
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is True
        assert error is None

    def test_content_crew_validate_inputs_missing_industry(self) -> None:
        """
        Test ContentCrew.validate_inputs without industry.

        Arrange: Create input without industry
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = ContentCrew()
        crew_input = CrewInput(
            inputs={
                "keywords": ["AI"],
                "target_platform": "xiaohongshu",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "industry" in error

    def test_content_crew_validate_inputs_missing_keywords(self) -> None:
        """
        Test ContentCrew.validate_inputs without keywords.

        Arrange: Create input without keywords
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = ContentCrew()
        crew_input = CrewInput(
            inputs={
                "industry": "AI",
                "target_platform": "xiaohongshu",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "keywords" in error

    def test_content_crew_validate_inputs_invalid_platform(self) -> None:
        """
        Test ContentCrew.validate_inputs with invalid platform.

        Arrange: Create input with invalid platform
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = ContentCrew()
        crew_input = CrewInput(
            inputs={
                "industry": "AI",
                "keywords": ["AI"],
                "target_platform": "invalid_platform",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "target_platform" in error

    def test_content_crew_validate_inputs_invalid_content_type(self) -> None:
        """
        Test ContentCrew.validate_inputs with invalid content_type.

        Arrange: Create input with invalid content_type
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = ContentCrew()
        crew_input = CrewInput(
            inputs={
                "industry": "AI",
                "keywords": ["AI"],
                "target_platform": "xiaohongshu",
                "content_type": "invalid_type",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content_type" in error

    @patch("src.crew.crews.content_crew.TopicResearcher.create")
    @patch("src.crew.crews.content_crew.ContentWriter.create")
    @patch("src.crew.crews.content_crew.ContentReviewer.create")
    def test_content_crew_get_agents(
        self,
        mock_reviewer: Mock,
        mock_writer: Mock,
        mock_researcher: Mock,
    ) -> None:
        """
        Test ContentCrew.get_agents creates correct agents.

        Arrange: Mock agent creation methods
        Act: Call get_agents()
        Assert: Returns list with 3 agents
        """
        mock_researcher.return_value = MagicMock()
        mock_writer.return_value = MagicMock()
        mock_reviewer.return_value = MagicMock()

        crew = ContentCrew()
        agents = crew.get_agents()

        assert len(agents) == 3
        mock_researcher.assert_called_once()
        mock_writer.assert_called_once()
        mock_reviewer.assert_called_once()

    @patch("src.crew.crews.content_crew.Task")
    @patch("src.crew.crews.content_crew.TopicResearcher.create")
    @patch("src.crew.crews.content_crew.ContentWriter.create")
    @patch("src.crew.crews.content_crew.ContentReviewer.create")
    def test_content_crew_get_tasks(
        self,
        mock_reviewer: Mock,
        mock_writer: Mock,
        mock_researcher: Mock,
        mock_task: Mock,
    ) -> None:
        """
        Test ContentCrew.get_tasks creates correct tasks.

        Arrange: Mock agent and task creation
        Act: Call get_tasks() with valid input
        Assert: Returns list with 3 tasks
        """
        mock_researcher.return_value = MagicMock()
        mock_writer.return_value = MagicMock()
        mock_reviewer.return_value = MagicMock()
        mock_task.return_value = MagicMock()

        crew = ContentCrew()
        crew_input = ContentCrewInput(
            industry="AI",
            keywords=["AI创业"],
            target_platform="xiaohongshu",
        )

        tasks = crew.get_tasks(crew_input)

        assert len(tasks) == 3
        # Task was called 3 times for research, write, review
        assert mock_task.call_count == 3

    def test_content_crew_extract_task_output_json(self) -> None:
        """
        Test ContentCrew._extract_task_output with JSON output.

        Arrange: Create mock task output with JSON string
        Act: Call _extract_task_output()
        Assert: Returns parsed JSON dictionary
        """
        crew = ContentCrew()
        mock_output = MagicMock()
        mock_output.raw = '{"title": "测试标题", "score": 85}'

        result = crew._extract_task_output(mock_output)

        assert isinstance(result, dict)
        assert result["title"] == "测试标题"
        assert result["score"] == 85

    def test_content_crew_extract_task_output_invalid_json(self) -> None:
        """
        Test ContentCrew._extract_task_output with invalid JSON.

        Arrange: Create mock task output with plain text
        Act: Call _extract_task_output()
        Assert: Returns dict with 'output' key
        """
        crew = ContentCrew()
        mock_output = MagicMock()
        mock_output.raw = "This is not JSON"

        result = crew._extract_task_output(mock_output)

        assert isinstance(result, dict)
        assert result["output"] == "This is not JSON"

    @patch("src.crew.crews.content_crew.TopicResearcher.create")
    @patch("src.crew.crews.content_crew.ContentWriter.create")
    @patch("src.crew.crews.content_crew.ContentReviewer.create")
    def test_content_crew_create_classmethod(
        self,
        mock_reviewer: Mock,
        mock_writer: Mock,
        mock_researcher: Mock,
    ) -> None:
        """
        Test ContentCrew.create class method.

        Arrange: Mock agent creation
        Act: Call ContentCrew.create()
        Assert: Returns ContentCrew instance
        """
        mock_researcher.return_value = MagicMock()
        mock_writer.return_value = MagicMock()
        mock_reviewer.return_value = MagicMock()

        crew = ContentCrew.create(enable_human_review=False)

        assert isinstance(crew, ContentCrew)
        assert crew.enable_human_review is False


class TestContentCrewIntegration:
    """Integration tests for ContentCrew end-to-end workflow."""

    @patch("src.crew.crews.content_crew.TopicResearcher.create")
    @patch("src.crew.crews.content_crew.ContentWriter.create")
    @patch("src.crew.crews.content_crew.ContentReviewer.create")
    @patch.object(ContentCrew, "execute")
    def test_content_crew_full_workflow_mock(
        self,
        mock_execute: Mock,
        mock_reviewer: Mock,
        mock_writer: Mock,
        mock_researcher: Mock,
    ) -> None:
        """
        Test ContentCrew full workflow with mocked execution.

        Arrange: Mock agents and execute method
        Act: Call kickoff() with input
        Assert: Returns expected ContentCrewResult
        """
        # Setup mocks
        mock_researcher.return_value = MagicMock()
        mock_writer.return_value = MagicMock()
        mock_reviewer.return_value = MagicMock()

        # Mock execute to return a ContentCrewResult
        mock_execute.return_value = ContentCrewResult(
            status=CrewStatus.COMPLETED,
            topic_report={
                "title": "AI创业实战指南",
                "potential_score": 85.0,
                "reasoning": "热点话题",
            },
            content_draft={
                "title": "AI创业3年，我踩过的5个坑",
                "content": "详细内容...",
                "tags": ["AI", "创业"],
            },
            review_report={
                "result": "approved",
                "overall_score": 85.0,
            },
            execution_time=15.0,
        )

        crew = ContentCrew()
        result = crew.kickoff(
            industry="AI",
            keywords=["AI创业", "人工智能"],
            target_platform="xiaohongshu",
        )

        assert result.status == CrewStatus.COMPLETED
        assert result.topic_report is not None
        assert result.content_draft is not None
        assert result.review_report is not None
        assert result.is_approved is True

    def test_content_crew_parse_outputs_with_tasks(self) -> None:
        """
        Test ContentCrew._parse_outputs with tasks_output.

        Arrange: Create mock outputs with tasks_output
        Act: Call _parse_outputs()
        Assert: Extracts task outputs correctly
        """
        crew = ContentCrew()

        # Mock outputs with tasks_output
        mock_outputs = MagicMock()
        mock_outputs.tasks_output = [
            MagicMock(raw='{"title": "选题报告", "potential_score": 85}'),
            MagicMock(raw='{"title": "内容草稿", "content": "内容..."}'),
            MagicMock(raw='{"result": "approved", "overall_score": 85}'),
        ]
        mock_outputs.to_dict.return_value = {"test": "value"}

        result = crew._parse_outputs(mock_outputs)

        assert "topic_report" in result
        assert "content_draft" in result
        assert "review_report" in result

    def test_content_crew_parse_outputs_without_tasks(self) -> None:
        """
        Test ContentCrew._parse_outputs without tasks_output.

        Arrange: Create mock outputs without tasks_output
        Act: Call _parse_outputs()
        Assert: Returns basic parsed output
        """
        crew = ContentCrew()

        mock_outputs = MagicMock(spec=["to_dict"])  # No tasks_output attribute, but has to_dict
        mock_outputs.to_dict.return_value = {"output": "basic"}

        result = crew._parse_outputs(mock_outputs)

        assert isinstance(result, dict)
        assert "output" in result
