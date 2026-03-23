"""
Unit tests for Agent classes.

Tests cover:
- Agent creation and configuration
- Default values and behaviors
- Tool management
- Data structure methods
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.agents.base_agent import BaseAgent
from src.agents.content_reviewer import (
    ContentReviewer,
    ReviewReport,
    ReviewResult,
)
from src.agents.content_writer import ContentWriter, ContentDraft
from src.agents.data_analyst import (
    AnalysisReport,
    ContentMetrics,
    DataAnalyst,
    MetricType,
    TrendAnalysis,
)
from src.agents.platform_adapter import AdaptedContent, Platform, PlatformAdapter
from src.agents.platform_publisher import (
    PublishBatch,
    PublishRecord,
    PublishStatus,
    PlatformPublisher,
)
from src.agents.topic_researcher import TopicReport, TopicResearcher


class TestBaseAgent:
    """Test cases for BaseAgent class."""

    def test_base_agent_is_abstract(self) -> None:
        """
        Test that BaseAgent cannot be instantiated directly.

        Arrange: Import BaseAgent class
        Act: Try to instantiate BaseAgent
        Assert: TypeError is raised
        """
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore

    def test_base_agent_default_model(self) -> None:
        """
        Test BaseAgent.get_default_model returns correct default.

        Arrange: Create a concrete implementation of BaseAgent
        Act: Call get_default_model
        Assert: Returns claude-sonnet-4-20250514
        """
        class ConcreteAgent(BaseAgent):
            def get_role(self) -> str:
                return "Test"

            def get_goal(self) -> str:
                return "Test"

            def get_backstory(self) -> str:
                return "Test"

        agent = ConcreteAgent()
        assert agent.get_default_model() == "claude-sonnet-4-20250514"

    def test_base_agent_initialization(self) -> None:
        """
        Test BaseAgent initialization with parameters.

        Arrange: Define concrete agent class
        Act: Create instance with custom parameters
        Assert: Parameters are stored correctly
        """
        class ConcreteAgent(BaseAgent):
            def get_role(self) -> str:
                return "Test"

            def get_goal(self) -> str:
                return "Test"

            def get_backstory(self) -> str:
                return "Test"

        agent = ConcreteAgent(
            llm="claude-opus-4-20250514",
            verbose=False,
            allow_delegation=False,
            human_input=True,
        )

        assert agent.llm == "claude-opus-4-20250514"
        assert agent.verbose is False
        assert agent.allow_delegation is False
        assert agent.human_input is True

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.ChatAnthropic")
    def test_base_agent_build(self, mock_llm: Mock, mock_agent: Mock) -> None:
        """
        Test BaseAgent.build creates CrewAI Agent correctly.

        Arrange: Create concrete agent with mocked dependencies
        Act: Call build() method
        Assert: Agent is created with correct parameters
        """
        class ConcreteAgent(BaseAgent):
            def get_role(self) -> str:
                return "Test Role"

            def get_goal(self) -> str:
                return "Test Goal"

            def get_backstory(self) -> str:
                return "Test Backstory"

        agent = ConcreteAgent(tools=[], verbose=True)
        result = agent.build()

        mock_agent.assert_called_once()
        call_kwargs = mock_agent.call_args[1]
        assert call_kwargs["role"] == "Test Role"
        assert call_kwargs["goal"] == "Test Goal"
        assert call_kwargs["backstory"] == "Test Backstory"
        assert call_kwargs["verbose"] is True


class TestTopicResearcher:
    """Test cases for TopicResearcher agent."""

    def test_topic_researcher_role(self) -> None:
        """
        Test TopicResearcher returns correct role.

        Arrange: Create TopicResearcher instance
        Act: Call get_role()
        Assert: Returns "选题研究员"
        """
        researcher = TopicResearcher()
        assert researcher.get_role() == "选题研究员"

    def test_topic_researcher_goal(self) -> None:
        """
        Test TopicResearcher returns correct goal.

        Arrange: Create TopicResearcher instance
        Act: Call get_goal()
        Assert: Goal contains expected keywords
        """
        researcher = TopicResearcher()
        goal = researcher.get_goal()
        assert "热点" in goal
        assert "选题" in goal
        assert "内容方向" in goal

    def test_topic_researcher_default_model(self) -> None:
        """
        Test TopicResearcher uses default model.

        Arrange: Create TopicResearcher instance
        Act: Call get_default_model()
        Assert: Returns claude-sonnet-4-20250514
        """
        researcher = TopicResearcher()
        assert researcher.get_default_model() == "claude-sonnet-4-20250514"

    def test_topic_researcher_tools_management(self) -> None:
        """
        Test TopicResearcher class-level tools management.

        Arrange: Create mock tools
        Act: Set tools via class method
        Assert: Tools are accessible via instance
        """
        mock_tools = [Mock(), Mock()]
        TopicResearcher.set_tools(mock_tools)

        researcher = TopicResearcher()
        assert researcher.get_tools() == mock_tools


class TestTopicReport:
    """Test cases for TopicReport data structure."""

    def test_topic_report_creation(self) -> None:
        """
        Test TopicReport can be created with valid data.

        Arrange: Prepare valid topic report data
        Act: Create TopicReport instance
        Assert: Instance is created with correct attributes
        """
        report = TopicReport(
            title="AI创业实战指南",
            category="科技创业",
            potential_score=85.5,
            reasoning="AI创业是当前热点",
            reference_content=["https://example.com"],
            target_audience="创业者",
            suggested_angle="技术人视角",
            keywords=["AI", "创业"],
        )

        assert report.title == "AI创业实战指南"
        assert report.category == "科技创业"
        assert report.potential_score == 85.5
        assert report.reasoning == "AI创业是当前热点"
        assert len(report.reference_content) == 1
        assert report.target_audience == "创业者"
        assert report.suggested_angle == "技术人视角"
        assert len(report.keywords) == 2

    def test_topic_report_to_dict(self) -> None:
        """
        Test TopicReport.to_dict converts to dictionary.

        Arrange: Create TopicReport instance
        Act: Call to_dict()
        Assert: Returns dictionary with all fields
        """
        report = TopicReport(
            title="测试标题",
            category="测试分类",
            potential_score=75.0,
            reasoning="测试理由",
            reference_content=[],
            target_audience="测试受众",
            suggested_angle="测试角度",
            keywords=["测试"],
        )

        result = report.to_dict()

        assert isinstance(result, dict)
        assert result["title"] == "测试标题"
        assert result["potential_score"] == 75.0
        assert "keywords" in result


class TestContentWriter:
    """Test cases for ContentWriter agent."""

    def test_content_writer_role(self) -> None:
        """
        Test ContentWriter returns correct role.

        Arrange: Create ContentWriter instance
        Act: Call get_role()
        Assert: Returns "内容创作者"
        """
        writer = ContentWriter()
        assert writer.get_role() == "内容创作者"

    def test_content_writer_uses_opus_model(self) -> None:
        """
        Test ContentWriter uses Opus model by default.

        Arrange: Create ContentWriter instance
        Act: Call get_default_model()
        Assert: Returns claude-opus-4-20250514
        """
        writer = ContentWriter()
        assert writer.get_default_model() == "claude-opus-4-20250514"

    def test_content_writer_goal(self) -> None:
        """
        Test ContentWriter returns correct goal.

        Arrange: Create ContentWriter instance
        Act: Call get_goal()
        Assert: Goal contains content creation keywords
        """
        writer = ContentWriter()
        goal = writer.get_goal()
        assert "创作" in goal
        assert "高质量" in goal
        assert "平台调性" in goal


class TestContentDraft:
    """Test cases for ContentDraft data structure."""

    def test_content_draft_creation(self) -> None:
        """
        Test ContentDraft can be created with valid data.

        Arrange: Prepare valid content draft data
        Act: Create ContentDraft instance
        Assert: Instance is created with correct attributes
        """
        draft = ContentDraft(
            title="测试标题",
            content="测试内容",
            summary="测试摘要",
            tags=["标签1", "标签2"],
            platform="xiaohongshu",
        )

        assert draft.title == "测试标题"
        assert draft.content == "测试内容"
        assert draft.summary == "测试摘要"
        assert len(draft.tags) == 2
        assert draft.platform == "xiaohongshu"

    def test_content_draft_to_dict(self) -> None:
        """
        Test ContentDraft.to_dict converts to dictionary.

        Arrange: Create ContentDraft instance
        Act: Call to_dict()
        Assert: Returns dictionary with all fields
        """
        draft = ContentDraft(
            title="标题",
            content="内容",
            summary="摘要",
            tags=["tag"],
            cover_image_prompt="图片提示",
        )

        result = draft.to_dict()

        assert isinstance(result, dict)
        assert result["title"] == "标题"
        assert result["cover_image_prompt"] == "图片提示"

    def test_content_draft_to_markdown(self) -> None:
        """
        Test ContentDraft.to_markdown generates valid markdown.

        Arrange: Create ContentDraft instance
        Act: Call to_markdown()
        Assert: Returns properly formatted markdown
        """
        draft = ContentDraft(
            title="AI创业指南",
            content="这是正文内容",
            summary="这是摘要",
            tags=["AI", "创业"],
        )

        markdown = draft.to_markdown()

        assert "# AI创业指南" in markdown
        assert "**摘要**: 这是摘要" in markdown
        assert "**标签**: AI, 创业" in markdown
        assert "这是正文内容" in markdown


class TestContentReviewer:
    """Test cases for ContentReviewer agent."""

    def test_content_reviewer_role(self) -> None:
        """
        Test ContentReviewer returns correct role.

        Arrange: Create ContentReviewer instance
        Act: Call get_role()
        Assert: Returns "内容审核员"
        """
        reviewer = ContentReviewer()
        assert reviewer.get_role() == "内容审核员"

    def test_content_reviewer_defaults(self) -> None:
        """
        Test ContentReviewer has correct default values.

        Arrange: Create ContentReviewer instance
        Act: Check default values
        Assert: human_input=True, allow_delegation=False
        """
        reviewer = ContentReviewer()
        # Check via the attributes set in __init__
        assert reviewer.human_input is True
        assert reviewer.allow_delegation is False


class TestReviewReport:
    """Test cases for ReviewReport data structure."""

    def test_review_report_creation_approved(self) -> None:
        """
        Test ReviewReport can be created with approved status.

        Arrange: Prepare valid review report data
        Act: Create ReviewReport with APPROVED status
        Assert: Instance is created and is_approved returns True
        """
        report = ReviewReport(
            result=ReviewResult.APPROVED,
            quality_score=85.0,
            compliance_score=95.0,
            spread_score=80.0,
            issues=[],
            suggestions=[],
            highlights=["结构清晰"],
            reviewer_notes="优秀",
        )

        assert report.result == ReviewResult.APPROVED
        assert report.is_approved() is True

    def test_review_report_overall_score(self) -> None:
        """
        Test ReviewReport.overall_score calculation.

        Arrange: Create ReviewReport with specific scores
        Act: Access overall_score property
        Assert: Returns weighted average
        """
        report = ReviewReport(
            result=ReviewResult.APPROVED,
            quality_score=80.0,
            compliance_score=90.0,
            spread_score=70.0,
            issues=[],
            suggestions=[],
            highlights=[],
            reviewer_notes="",
        )

        # Expected: 80*0.4 + 90*0.35 + 70*0.25 = 32 + 31.5 + 17.5 = 81
        assert report.overall_score == 81.0

    def test_review_report_needs_revision(self) -> None:
        """
        Test ReviewReport with NEEDS_REVISION status.

        Arrange: Create ReviewReport with NEEDS_REVISION
        Act: Check is_approved()
        Assert: Returns False
        """
        report = ReviewReport(
            result=ReviewResult.NEEDS_REVISION,
            quality_score=60.0,
            compliance_score=80.0,
            spread_score=70.0,
            issues=["标题不够吸引人"],
            suggestions=["优化标题"],
            highlights=[],
            reviewer_notes="需要修改",
        )

        assert report.result == ReviewResult.NEEDS_REVISION
        assert report.is_approved() is False
        assert len(report.issues) == 1


class TestPlatformAdapter:
    """Test cases for PlatformAdapter agent."""

    def test_platform_adapter_role(self) -> None:
        """
        Test PlatformAdapter returns correct role.

        Arrange: Create PlatformAdapter instance
        Act: Call get_role()
        Assert: Returns "平台适配师"
        """
        adapter = PlatformAdapter()
        assert adapter.get_role() == "平台适配师"

    def test_platform_adapter_specs_xiaohongshu(self) -> None:
        """
        Test PlatformAdapter platform specs for xiaohongshu.

        Arrange: Access PlatformAdapter class
        Act: Get specs for xiaohongshu
        Assert: Returns correct platform specifications
        """
        specs = PlatformAdapter.get_platform_specs(Platform.XIAOHONGSHU)

        assert specs["title_max_length"] == 20
        assert specs["max_tags"] == 10
        assert specs["supports_markdown"] is False
        assert specs["emoji_required"] is True

    def test_platform_adapter_specs_wechat(self) -> None:
        """
        Test PlatformAdapter platform specs for wechat.

        Arrange: Access PlatformAdapter class
        Act: Get specs for wechat
        Assert: Returns correct platform specifications
        """
        specs = PlatformAdapter.get_platform_specs(Platform.WECHAT)

        assert specs["title_max_length"] == 64
        assert specs["supports_markdown"] is True
        assert specs["supports_html"] is True

    def test_platform_enum_values(self) -> None:
        """
        Test Platform enum has all expected values.

        Arrange: Import Platform enum
        Act: Check enum values
        Assert: All expected platforms are present
        """
        assert Platform.WECHAT.value == "wechat"
        assert Platform.XIAOHONGSHU.value == "xiaohongshu"
        assert Platform.DOUYIN.value == "douyin"
        assert Platform.BILIBILI.value == "bilibili"
        assert Platform.ZHIHU.value == "zhihu"
        assert Platform.WEIBO.value == "weibo"


class TestAdaptedContent:
    """Test cases for AdaptedContent data structure."""

    def test_adapted_content_creation(self) -> None:
        """
        Test AdaptedContent can be created with valid data.

        Arrange: Prepare valid adapted content data
        Act: Create AdaptedContent instance
        Assert: Instance is created with correct attributes
        """
        content = AdaptedContent(
            platform=Platform.XIAOHONGSHU,
            title="适配后的标题",
            content="适配后的内容",
            summary="适配后的摘要",
            tags=["标签1", "标签2"],
        )

        assert content.platform == Platform.XIAOHONGSHU
        assert content.title == "适配后的标题"
        assert len(content.tags) == 2

    def test_adapted_content_to_dict(self) -> None:
        """
        Test AdaptedContent.to_dict converts to dictionary.

        Arrange: Create AdaptedContent instance
        Act: Call to_dict()
        Assert: Returns dictionary with platform value
        """
        content = AdaptedContent(
            platform=Platform.WECHAT,
            title="标题",
            content="内容",
            summary="摘要",
            tags=[],
        )

        result = content.to_dict()

        assert result["platform"] == "wechat"


class TestPlatformPublisher:
    """Test cases for PlatformPublisher agent."""

    def test_platform_publisher_role(self) -> None:
        """
        Test PlatformPublisher returns correct role.

        Arrange: Create PlatformPublisher instance
        Act: Call get_role()
        Assert: Returns "平台发布员"
        """
        publisher = PlatformPublisher()
        assert publisher.get_role() == "平台发布员"

    def test_platform_publisher_defaults(self) -> None:
        """
        Test PlatformPublisher has correct default values.

        Arrange: Create PlatformPublisher instance
        Act: Check default values
        Assert: allow_delegation=False, human_input=False
        """
        publisher = PlatformPublisher()
        assert publisher.allow_delegation is False
        assert publisher.human_input is False


class TestPublishRecord:
    """Test cases for PublishRecord data structure."""

    def test_publish_record_creation(self) -> None:
        """
        Test PublishRecord can be created with valid data.

        Arrange: Prepare valid publish record data
        Act: Create PublishRecord instance
        Assert: Instance is created with correct attributes
        """
        record = PublishRecord(
            content_id="draft_123",
            platform=Platform.XIAOHONGSHU,
            status=PublishStatus.PUBLISHED,
            published_url="https://example.com/post/123",
            published_at=datetime.now(),
        )

        assert record.content_id == "draft_123"
        assert record.platform == Platform.XIAOHONGSHU
        assert record.status == PublishStatus.PUBLISHED

    def test_publish_record_is_success(self) -> None:
        """
        Test PublishRecord.is_success for published status.

        Arrange: Create PublishRecord with PUBLISHED status
        Act: Call is_success()
        Assert: Returns True
        """
        record = PublishRecord(
            content_id="draft_123",
            platform=Platform.XIAOHONGSHU,
            status=PublishStatus.PUBLISHED,
        )

        assert record.is_success() is True
        assert record.is_failed() is False
        assert record.is_pending() is False

    def test_publish_record_is_failed(self) -> None:
        """
        Test PublishRecord status checks for failed status.

        Arrange: Create PublishRecord with FAILED status
        Act: Call status check methods
        Assert: Only is_failed returns True
        """
        record = PublishRecord(
            content_id="draft_123",
            platform=Platform.WEIBO,
            status=PublishStatus.FAILED,
            error_message="API error",
            retry_count=2,
        )

        assert record.is_success() is False
        assert record.is_failed() is True
        assert record.is_pending() is False
        assert record.retry_count == 2


class TestPublishBatch:
    """Test cases for PublishBatch data structure."""

    def test_publish_batch_creation(self) -> None:
        """
        Test PublishBatch can be created with valid data.

        Arrange: Prepare content ID and platforms
        Act: Create PublishBatch instance
        Assert: Instance creates records for all platforms
        """
        batch = PublishBatch(
            content_id="draft_123",
            platforms=[Platform.XIAOHONGSHU, Platform.WECHAT],
        )

        assert batch.content_id == "draft_123"
        assert len(batch.records) == 2
        assert Platform.XIAOHONGSHU in batch.records
        assert Platform.WECHAT in batch.records

    def test_publish_batch_update_record(self) -> None:
        """
        Test PublishBatch.update_record updates a record.

        Arrange: Create PublishBatch
        Act: Update a record with new status
        Assert: Record is updated correctly
        """
        batch = PublishBatch(
            content_id="draft_123",
            platforms=[Platform.XIAOHONGSHU],
        )

        updated_record = PublishRecord(
            content_id="draft_123",
            platform=Platform.XIAOHONGSHU,
            status=PublishStatus.PUBLISHED,
            published_url="https://example.com/post/123",
        )

        batch.update_record(updated_record)

        retrieved = batch.get_record(Platform.XIAOHONGSHU)
        assert retrieved.status == PublishStatus.PUBLISHED
        assert retrieved.published_url == "https://example.com/post/123"

    def test_publish_batch_summary_methods(self) -> None:
        """
        Test PublishBatch summary calculation methods.

        Arrange: Create PublishBatch with mixed status records
        Act: Update records and call summary methods
        Assert: Summary methods return correct values
        """
        batch = PublishBatch(
            content_id="draft_123",
            platforms=[
                Platform.XIAOHONGSHU,
                Platform.WECHAT,
                Platform.WEIBO,
            ],
        )

        # Update one to success, one to failed
        batch.update_record(
            PublishRecord(
                content_id="draft_123",
                platform=Platform.XIAOHONGSHU,
                status=PublishStatus.PUBLISHED,
            )
        )
        batch.update_record(
            PublishRecord(
                content_id="draft_123",
                platform=Platform.WECHAT,
                status=PublishStatus.FAILED,
            )
        )

        assert len(batch.get_successful_platforms()) == 1
        assert len(batch.get_failed_platforms()) == 1
        assert len(batch.get_pending_platforms()) == 1
        assert batch.is_all_success() is False

    def test_publish_batch_to_dict(self) -> None:
        """
        Test PublishBatch.to_dict generates correct summary.

        Arrange: Create PublishBatch
        Act: Call to_dict()
        Assert: Returns dict with summary
        """
        batch = PublishBatch(
            content_id="draft_123",
            platforms=[Platform.XIAOHONGSHU, Platform.WECHAT],
        )

        result = batch.to_dict()

        assert result["content_id"] == "draft_123"
        assert result["summary"]["total"] == 2
        assert result["summary"]["pending"] == 2


class TestDataAnalyst:
    """Test cases for DataAnalyst agent."""

    def test_data_analyst_role(self) -> None:
        """
        Test DataAnalyst returns correct role.

        Arrange: Create DataAnalyst instance
        Act: Call get_role()
        Assert: Returns "数据分析师"
        """
        analyst = DataAnalyst()
        assert analyst.get_role() == "数据分析师"

    def test_data_analyst_goal_keywords(self) -> None:
        """
        Test DataAnalyst goal contains expected keywords.

        Arrange: Create DataAnalyst instance
        Act: Call get_goal()
        Assert: Goal contains analytics-related keywords
        """
        analyst = DataAnalyst()
        goal = analyst.get_goal()
        assert any(word in goal for word in ["分析", "洞察", "数据", "建议"])


class TestContentMetrics:
    """Test cases for ContentMetrics data structure."""

    def test_content_metrics_creation(self) -> None:
        """
        Test ContentMetrics can be created with valid data.

        Arrange: Prepare valid metrics data
        Act: Create ContentMetrics instance
        Assert: Instance is created with correct attributes
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        metrics = ContentMetrics(
            content_id="content_123",
            platform=Platform.XIAOHONGSHU,
            metrics={
                AgentMetricType.VIEWS: 1000,
                AgentMetricType.LIKES: 100,
            },
            recorded_at=datetime.now(),
        )

        assert metrics.content_id == "content_123"
        assert metrics.platform == Platform.XIAOHONGSHU

    def test_content_metrics_calculate_engagement_rate(self) -> None:
        """
        Test ContentMetrics.calculate_engagement_rate calculation.

        Arrange: Create ContentMetrics with views and engagements
        Act: Call calculate_engagement_rate()
        Assert: Returns correct engagement rate percentage
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        metrics = ContentMetrics(
            content_id="content_123",
            platform=Platform.XIAOHONGSHU,
            metrics={
                AgentMetricType.VIEWS: 1000,
                AgentMetricType.LIKES: 50,
                AgentMetricType.COMMENTS: 10,
                AgentMetricType.SHARES: 5,
                AgentMetricType.FAVORITES: 15,
            },
            recorded_at=datetime.now(),
        )

        # (50 + 10 + 5 + 15) / 1000 * 100 = 8%
        rate = metrics.calculate_engagement_rate()
        assert rate == 8.0

    def test_content_metrics_zero_views(self) -> None:
        """
        Test ContentMetrics with zero views returns 0 engagement rate.

        Arrange: Create ContentMetrics with 0 views
        Act: Call calculate_engagement_rate()
        Assert: Returns 0.0
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        metrics = ContentMetrics(
            content_id="content_123",
            platform=Platform.XIAOHONGSHU,
            metrics={AgentMetricType.VIEWS: 0},
            recorded_at=datetime.now(),
        )

        assert metrics.calculate_engagement_rate() == 0.0


class TestAnalysisReport:
    """Test cases for AnalysisReport data structure."""

    def test_analysis_report_creation(self) -> None:
        """
        Test AnalysisReport can be created with valid data.

        Arrange: Prepare valid report data
        Act: Create AnalysisReport instance
        Assert: Instance is created correctly
        """
        report = AnalysisReport(
            report_type="weekly",
            period="2025-W12",
            summary="本周表现良好",
            key_findings=["发现1", "发现2"],
            metrics_summary={"total_views": 10000},
            top_performers=[],
            underperformers=[],
            recommendations=["建议1"],
            generated_at=datetime.now(),
        )

        assert report.report_type == "weekly"
        assert len(report.key_findings) == 2
        assert len(report.recommendations) == 1

    def test_analysis_report_to_summary(self) -> None:
        """
        Test AnalysisReport.to_summary generates formatted text.

        Arrange: Create AnalysisReport with data
        Act: Call to_summary()
        Assert: Returns formatted markdown summary
        """
        report = AnalysisReport(
            report_type="weekly",
            period="2025-W12",
            summary="测试摘要",
            key_findings=["关键发现1", "关键发现2"],
            metrics_summary={},
            top_performers=[
                {"title": "热门内容", "views": 5000}
            ],
            underperformers=[],
            recommendations=["优化建议"],
            generated_at=datetime.now(),
        )

        summary = report.to_summary()

        assert "# WEEKLY Report" in summary
        assert "测试摘要" in summary
        assert "1. 关键发现1" in summary
        assert "热门内容: 5000 views" in summary


class TestTrendAnalysis:
    """Test cases for TrendAnalysis data structure."""

    def test_trend_analysis_creation(self) -> None:
        """
        Test TrendAnalysis can be created with valid data.

        Arrange: Prepare valid trend data
        Act: Create TrendAnalysis instance
        Assert: Instance is created correctly
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        trend = TrendAnalysis(
            metric_type=AgentMetricType.VIEWS,
            platform=Platform.XIAOHONGSHU,
            current_value=1500,
            previous_value=1000,
            change_percent=50.0,
            trend="up",
            insight="浏览量增长50%",
        )

        assert trend.metric_type == AgentMetricType.VIEWS
        assert trend.change_percent == 50.0

    def test_trend_analysis_is_positive(self) -> None:
        """
        Test TrendAnalysis.is_positive for positive change.

        Arrange: Create TrendAnalysis with positive change
        Act: Call is_positive()
        Assert: Returns True
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        trend = TrendAnalysis(
            metric_type=AgentMetricType.LIKES,
            platform=Platform.XIAOHONGSHU,
            current_value=150,
            previous_value=100,
            change_percent=50.0,
            trend="up",
            insight="",
        )

        assert trend.is_positive() is True

    def test_trend_analysis_is_significant(self) -> None:
        """
        Test TrendAnalysis.is_significant with threshold.

        Arrange: Create TrendAnalysis with specific change
        Act: Call is_significant() with threshold
        Assert: Returns correct result
        """
        from src.agents.data_analyst import MetricType as AgentMetricType

        trend = TrendAnalysis(
            metric_type=AgentMetricType.VIEWS,
            platform=Platform.XIAOHONGSHU,
            current_value=1150,
            previous_value=1000,
            change_percent=15.0,
            trend="up",
            insight="",
        )

        # 15% >= 10% threshold
        assert trend.is_significant(threshold=10.0) is True
        # 15% < 20% threshold
        assert trend.is_significant(threshold=20.0) is False
