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
            topic="AI创业指南",
            target_platform="xiaohongshu",
            content_type="article",
            research_depth="standard",
            enable_human_review=True,
        )

        assert crew_input.inputs["topic"] == "AI创业指南"
        assert crew_input.inputs["target_platform"] == "xiaohongshu"
        assert crew_input.inputs["content_type"] == "article"
        assert crew_input.inputs["research_depth"] == "standard"

    def test_content_crew_input_to_dict(self) -> None:
        """
        Test ContentCrewInput.to_dict serialization.

        Arrange: Create ContentCrewInput
        Act: Call to_dict()
        Assert: Returns dictionary with all fields
        """
        crew_input = ContentCrewInput(
            topic="科技前沿",
            target_platform="wechat",
        )

        result = crew_input.to_dict()

        assert isinstance(result, dict)
        assert "inputs" in result
        assert "metadata" in result
        assert result["inputs"]["topic"] == "科技前沿"

    def test_content_crew_input_from_dict(self) -> None:
        """
        Test ContentCrewInput.from_dict deserialization.

        Arrange: Prepare dictionary with input data
        Act: Call from_dict()
        Assert: Returns ContentCrewInput with correct values
        """
        data = {
            "inputs": {
                "topic": "电商直播",
                "target_platform": "douyin",
            },
            "metadata": {"test": True},
        }

        crew_input = CrewInput.from_dict(data)

        assert crew_input.inputs["topic"] == "电商直播"
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
            research_findings={
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
        assert result.research_findings["title"] == "AI创业指南"
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

        assert crew.get_crew_name() == "ContentCrew"
        assert crew.enable_human_review is True

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)
    def test_content_crew_custom_parameters(self) -> None:
        """
        Test ContentCrew with custom parameters.

        Arrange: Prepare custom parameters (no Anthropic key so llm stays as string)
        Act: Create ContentCrew with custom settings
        Assert: Custom parameters are set correctly
        """
        crew = ContentCrew(
            verbose=False,
            memory=False,
            enable_human_review=False,
            llm="gpt-4o-mini",
        )

        assert crew.verbose is False
        assert crew.memory is False
        assert crew.enable_human_review is False
        assert crew.llm == "gpt-4o-mini"

    def test_content_crew_validate_inputs_valid(self) -> None:
        """
        Test ContentCrew.validate_inputs with valid data.

        Arrange: Create ContentCrew and valid input
        Act: Call validate_inputs()
        Assert: Returns (True, None)
        """
        crew = ContentCrew()
        crew_input = ContentCrewInput(
            topic="AI创业",
            target_platform="xiaohongshu",
            content_type="article",
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is True
        assert error is None

    def test_content_crew_validate_inputs_missing_topic(self) -> None:
        """
        Test ContentCrew.validate_inputs without topic.

        Arrange: Create input without topic
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = ContentCrew()
        crew_input = CrewInput(
            inputs={
                "target_platform": "xiaohongshu",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "topic" in error

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
                "topic": "AI创业",
                "target_platform": "invalid_platform",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "target_platform" in error

    @patch("src.agents.ContentCreator")
    @patch("src.agents.ContentReviewer")
    def test_content_crew_get_agents(
        self,
        mock_reviewer_cls: Mock,
        mock_creator_cls: Mock,
    ) -> None:
        """
        Test ContentCrew.get_agents creates correct agents.

        Arrange: Mock agent classes
        Act: Call get_agents()
        Assert: Returns list with 2 agents (creator + reviewer)
        """
        mock_creator_cls.return_value = MagicMock(
            get_role=MagicMock(return_value="创作者"),
            get_goal=MagicMock(return_value="创作"),
            get_backstory=MagicMock(return_value="背景"),
        )
        mock_reviewer_cls.return_value = MagicMock(
            get_role=MagicMock(return_value="审核员"),
            get_goal=MagicMock(return_value="审核"),
            get_backstory=MagicMock(return_value="背景"),
        )

        crew = ContentCrew()
        agents = crew.get_agents()

        assert len(agents) == 2

    @patch("src.crew.crews.content_crew.Task")
    @patch("src.agents.ContentCreator")
    @patch("src.agents.ContentReviewer")
    def test_content_crew_get_tasks(
        self,
        mock_reviewer_cls: Mock,
        mock_creator_cls: Mock,
        mock_task: Mock,
    ) -> None:
        """
        Test ContentCrew.get_tasks creates correct tasks.

        Arrange: Mock agent and task creation
        Act: Call get_tasks() with valid input
        Assert: Returns list with 2 tasks (create + review)
        """
        mock_creator_cls.return_value = MagicMock(
            get_role=MagicMock(return_value="创作者"),
            get_goal=MagicMock(return_value="创作"),
            get_backstory=MagicMock(return_value="背景"),
        )
        mock_reviewer_cls.return_value = MagicMock(
            get_role=MagicMock(return_value="审核员"),
            get_goal=MagicMock(return_value="审核"),
            get_backstory=MagicMock(return_value="背景"),
        )
        mock_task.return_value = MagicMock()

        crew = ContentCrew()
        crew_input = ContentCrewInput(
            topic="AI创业",
            target_platform="xiaohongshu",
        )

        tasks = crew.get_tasks(crew_input)

        assert len(tasks) == 2
        assert mock_task.call_count == 2

    def test_content_crew_extract_raw_outputs_json(self) -> None:
        """
        Test ContentCrew._extract_raw_outputs with mock output.

        Arrange: Create mock output with raw attribute
        Act: Call _extract_raw_outputs()
        Assert: Returns dictionary with raw data
        """
        crew = ContentCrew()
        mock_output = MagicMock()
        mock_output.raw = '{"title": "测试标题", "score": 85}'

        result = crew._extract_raw_outputs(mock_output)

        assert isinstance(result, dict)

    def test_content_crew_extract_raw_outputs_plain_text(self) -> None:
        """
        Test ContentCrew._extract_raw_outputs with plain text output.

        Arrange: Create mock output with plain text
        Act: Call _extract_raw_outputs()
        Assert: Returns dict
        """
        crew = ContentCrew()
        mock_output = MagicMock()
        mock_output.raw = "This is not JSON"

        result = crew._extract_raw_outputs(mock_output)

        assert isinstance(result, dict)

    def test_content_crew_create_classmethod(self) -> None:
        """
        Test ContentCrew.create class method.

        Arrange: None
        Act: Call ContentCrew.create()
        Assert: Returns ContentCrew instance
        """
        crew = ContentCrew.create(enable_human_review=False)

        assert isinstance(crew, ContentCrew)
        assert crew.enable_human_review is False


class TestContentCrewIntegration:
    """Integration tests for ContentCrew end-to-end workflow."""

    @patch.object(ContentCrew, "execute")
    def test_content_crew_full_workflow_mock(
        self,
        mock_execute: Mock,
    ) -> None:
        """
        Test ContentCrew full workflow with mocked execution.

        Arrange: Mock execute method
        Act: Call kickoff() with input
        Assert: Returns expected ContentCrewResult
        """
        # Mock execute to return a ContentCrewResult
        mock_execute.return_value = ContentCrewResult(
            status=CrewStatus.COMPLETED,
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
            topic="AI创业",
            target_platform="xiaohongshu",
        )

        assert result.status == CrewStatus.COMPLETED
        assert result.content_draft is not None
        assert result.review_report is not None
        assert result.is_approved is True

    def test_content_crew_parse_outputs_with_tasks(self) -> None:
        """
        Test ContentCrew._parse_outputs with dict-like output.

        Arrange: Create mock outputs with to_dict
        Act: Call _parse_outputs()
        Assert: Returns parsed dictionary
        """
        crew = ContentCrew()

        mock_outputs = MagicMock()
        mock_outputs.to_dict.return_value = {
            "content_draft": {"title": "内容草稿", "content": "内容..."},
            "review_report": {"result": "approved", "overall_score": 85},
        }

        result = crew._parse_outputs(mock_outputs)

        assert isinstance(result, dict)
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
