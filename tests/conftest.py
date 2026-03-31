"""
Pytest configuration and shared fixtures for CrewAI tests.

Provides fixtures for:
- Mock LLM responses
- Mock platform API responses
- Test database (SQLite in-memory)
- Common test data
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.agents.base_agent import BaseAgent
from src.agents.content_reviewer import ContentReviewer, ReviewResult, ReviewReport
from src.agents.content_creator import ContentCreator, ContentDraft
from src.agents.data_analyst import DataAnalyst, AnalysisReport, ContentMetrics, TrendAnalysis
from src.agents.platform_adapter import Platform, PlatformAdapter
from src.agents.platform_publisher import (
    PlatformPublisher,
    PublishBatch,
    PublishRecord,
    PublishStatus,
)
from src.crew.crews.base_crew import BaseCrew, CrewInput, CrewResult, CrewStatus
from src.models.base import Base
from src.models.analytics import Analytics, MetricSnapshot
from src.models.content import Content, ContentBrief as ContentBriefDB, ContentDraft as ContentDraftDB
from src.models.publish_log import PlatformPost, PublishLog
from src.schemas.analytics_report import (
    AnalyticsReport as AnalyticsReportSchema,
    MetricType,
    TimePeriod,
)
from src.schemas.content_brief import (
    AudienceInsight,
    ContentBrief as ContentBriefSchema,
    ContentType,
    PlatformType,
    TargetAudience,
    TrendingTopic,
)
from src.schemas.content_draft import (
    ContentBlock,
    ContentDraft as ContentDraftSchema,
    DraftStatus,
    PlatformContent,
    QualityScore,
)
from src.schemas.publish_result import (
    PlatformPostInfo,
    PublishError,
    PublishResult,
    PublishStatus as PublishStatusSchema,
    ScheduleType,
)
from src.tools.analytics_tools import DataCollectTool, AnalyticsReportTool
from src.tools.base_tool import BaseTool, ToolResult, ToolStatus
from src.tools.content_tools import HashtagSuggestTool, ImageSearchTool, SEOOptimizeTool
from src.tools.search_tools import (
    CompetitorAnalysisTool,
    HotSearchTool,
    TrendAnalysisTool,
)


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def test_engine():
    """
    Create an in-memory SQLite database for testing.

    Yields:
        Engine: SQLAlchemy engine
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a test database session.

    Yields:
        Session: SQLAlchemy session
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """
    Create an async test database session for content_service tests.

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker as async_sessionmaker

    # Create async engine
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()


@pytest.fixture(scope="function")
async def client():
    """
    Create an async HTTP client for testing FastAPI endpoints.

    Yields:
        AsyncClient: HTTPX async client
    """
    from httpx import ASGITransport, AsyncClient
    from src.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def sample_content_brief(test_session: Session) -> ContentBriefDB:
    """
    Create a sample content brief in the test database.

    Args:
        test_session: Test database session

    Returns:
        ContentBriefDB: Sample content brief instance
    """
    brief = ContentBriefDB(
        topic="AI创业实战指南",
        sub_topics=["MVP开发", "融资策略"],
        keywords=["AI创业", "人工智能", "创业指南"],
        target_audience=[
            {
                "segment": "entrepreneur",
                "size_estimate": "10万+",
                "interests": ["AI技术", "创业融资"],
                "pain_points": ["资金短缺", "团队管理"],
                "preferred_content_type": "article",
                "active_hours": ["9:00-11:00", "18:00-21:00"],
            }
        ],
        trending_topics=[
            {
                "keyword": "AI Agent",
                "search_volume": 50000,
                "growth_rate": 150.0,
                "competition_level": "medium",
                "related_keywords": ["智能体", "AI助手"],
                "source_platform": "xiaohongshu",
            }
        ],
        content_angle="从技术人角度分享AI创业踩坑经验",
        tone="professional",
        suggested_content_type="article",
        primary_platform="xiaohongshu",
        secondary_platforms=["wechat", "zhihu"],
        key_points=["技术栈选择", "融资经验", "团队搭建"],
        call_to_action="关注我获取更多干货",
        hashtags=["#AI创业", "#科技创业"],
    )
    test_session.add(brief)
    test_session.commit()
    test_session.refresh(brief)
    return brief


@pytest.fixture(scope="function")
def sample_content_draft(
    test_session: Session,
    sample_content_brief: ContentBriefDB,
) -> ContentDraftDB:
    """
    Create a sample content draft in the test database.

    Args:
        test_session: Test database session
        sample_content_brief: Sample content brief

    Returns:
        ContentDraft: Sample content draft instance
    """
    draft = ContentDraftDB(
        brief_id=sample_content_brief.id,
        status="approved",
        version=1,
        topic="AI创业实战指南",
        content_type="article",
        platforms=["xiaohongshu", "wechat"],
        platform_content=[
            {
                "platform": "xiaohongshu",
                "title": "AI创业3年，我踩过的5个坑",
                "plain_text": "作为连续创业者...",
                "hashtags": ["#AI创业", "#创业干货"],
                "character_count": 850,
            }
        ],
        brand_voice="专业但不失亲和",
        tone="professional",
        reviews=[],
        current_score=None,
        tags=["AI", "创业", "经验"],
        category="创业经验",
    )
    test_session.add(draft)
    test_session.commit()
    test_session.refresh(draft)
    return draft


@pytest.fixture(scope="function")
def sample_publish_log(
    test_session: Session,
    sample_content_draft: ContentDraftDB,
) -> PublishLog:
    """
    Create a sample publish log in the test database.

    Args:
        test_session: Test database session
        sample_content_draft: Sample content draft

    Returns:
        PublishLog: Sample publish log instance
    """
    log = PublishLog(
        draft_id=sample_content_draft.id,
        status="published",
        schedule_type="immediate",
        platforms=["xiaohongshu"],
        successful_posts=[
            {
                "platform": "xiaohongshu",
                "post_id": "64a1b2c3d4e5f6g7h8i9j0",
                "post_url": "https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
                "published_at": datetime.now().isoformat(),
            }
        ],
        failed_platforms=[],
        errors=[],
        success_count=1,
        failure_count=0,
    )
    test_session.add(log)
    test_session.commit()
    test_session.refresh(log)
    return log


# =============================================================================
# LLM Mock Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def mock_llm_response() -> Dict[str, Any]:
    """
    Provide mock LLM response data.

    Returns:
        Dictionary with mock LLM response structure
    """
    return {
        "content": "这是一个模拟的 LLM 响应内容。",
        "role": "assistant",
        "model": "claude-sonnet-4-20250514",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        },
    }


@pytest.fixture(scope="function")
def mock_llm(mocker: MockerFixture) -> Mock:
    """
    Mock the LLM (ChatAnthropic) for testing.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        Mock: Mocked ChatAnthropic instance
    """
    mock = mocker.patch("src.agents.base_agent.ChatAnthropic")
    mock_instance = Mock()
    mock_instance.model = "claude-sonnet-4-20250514"
    mock.return_value = mock_instance
    return mock_instance


@pytest.fixture(scope="function")
def mock_crewai_agent(mocker: MockerFixture) -> Mock:
    """
    Mock CrewAI Agent class.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        Mock: Mocked Agent class
    """
    mock_agent = mocker.patch("crewai.Agent")
    mock_instance = MagicMock()
    mock_instance.role = "Test Agent"
    mock_instance.goal = "Test goal"
    mock_instance.backstory = "Test backstory"
    mock_agent.return_value = mock_instance
    return mock_agent


# =============================================================================
# Platform API Mock Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def mock_platform_api_response() -> Dict[str, Any]:
    """
    Provide mock platform API response data.

    Returns:
        Dictionary with mock platform API response structure
    """
    return {
        "code": 0,
        "message": "success",
        "data": {
            "post_id": "test_post_123",
            "post_url": "https://example.com/post/test_post_123",
            "published_at": datetime.now().isoformat(),
        },
    }


@pytest.fixture(scope="function")
def mock_hot_search_response() -> List[Dict[str, Any]]:
    """
    Provide mock hot search API response.

    Returns:
        List of mock hot search topics
    """
    return [
        {
            "rank": 1,
            "keyword": "AI创业实战",
            "heat": 1000000,
            "category": "科技",
            "url": "https://example.com/search?q=AI创业实战",
        },
        {
            "rank": 2,
            "keyword": "Claude 4发布",
            "heat": 950000,
            "category": "AI",
            "url": "https://example.com/search?q=Claude+4",
        },
        {
            "rank": 3,
            "keyword": "2025创业趋势",
            "heat": 880000,
            "category": "商业",
            "url": "https://example.com/search?q=2025创业趋势",
        },
    ]


@pytest.fixture(scope="function")
def mock_analytics_response() -> Dict[str, Any]:
    """
    Provide mock analytics API response.

    Returns:
        Dictionary with mock analytics data
    """
    return {
        "content_id": "test_content_123",
        "platform": "xiaohongshu",
        "metrics": {
            "views": 15234,
            "likes": 1245,
            "comments": 89,
            "shares": 34,
            "favorites": 56,
            "engagement_rate": 0.087,
        },
        "collected_at": datetime.now().isoformat(),
    }


# =============================================================================
# Common Test Data Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def sample_topic_report() -> ContentDraft:
    """
    Provide a sample topic report.

    Returns:
        ContentDraft: Sample content draft instance (replaces TopicReport)
    """
    return ContentDraft(
        title="AI创业实战指南",
        content="# 坑1：技术选型\n\n详细内容...",
        summary="AI创业是当前热点，搜索量增长150%",
        tags=["AI创业", "人工智能", "创业指南", "技术转型"],
        style_notes="从技术人角度分享踩坑经验",
        platform="xiaohongshu",
        metadata={"category": "科技创业"},
    )


@pytest.fixture(scope="function")
def sample_content_draft_obj() -> ContentDraft:
    """
    Provide a sample content draft object.

    Returns:
        ContentDraft: Sample content draft instance
    """
    return ContentDraft(
        title="AI创业3年，我踩过的5个坑",
        content="# 坑1：技术选型\n\n详细内容...",
        summary="分享AI创业过程中的技术选型踩坑经验",
        tags=["AI创业", "技术", "经验"],
        cover_image_prompt="AI技术栈图解，现代简约风格",
        platform="xiaohongshu",
        metadata={"word_count": 1200},
    )


@pytest.fixture(scope="function")
def sample_review_report() -> ReviewReport:
    """
    Provide a sample review report.

    Returns:
        ReviewReport: Sample review report instance
    """
    return ReviewReport(
        result=ReviewResult.APPROVED,
        quality_score=85.0,
        compliance_score=95.0,
        spread_score=80.0,
        issues=[],
        suggestions=["增加数据图表", "优化标题吸引力"],
        highlights=["结构清晰", "案例丰富"],
        reviewer_notes="内容质量优秀，建议微调后发布",
    )


@pytest.fixture(scope="function")
def sample_publish_record() -> PublishRecord:
    """
    Provide a sample publish record.

    Returns:
        PublishRecord: Sample publish record instance
    """
    return PublishRecord(
        content_id="draft_123",
        platform=Platform.XIAOHONGSHU,
        status=PublishStatus.PUBLISHED,
        published_url="https://xiaohongshu.com/explore/abc123",
        published_at=datetime.now(),
    )


@pytest.fixture(scope="function")
def sample_analysis_report() -> AnalysisReport:
    """
    Provide a sample analysis report.

    Returns:
        AnalysisReport: Sample analysis report instance
    """
    return AnalysisReport(
        report_type="weekly",
        period="2025-W12",
        summary="本周内容表现良好，小红书平台表现突出",
        key_findings=[
            "小红书互动率高于平均水平35%",
            "视频内容比图文获得更多曝光",
        ],
        metrics_summary={
            "total_views": 50000,
            "avg_engagement_rate": 8.5,
            "total_content": 10,
        },
        top_performers=[
            {"title": "AI创业指南", "views": 15000, "platform": "xiaohongshu"}
        ],
        underperformers=[
            {"title": "技术趋势分析", "views": 2000, "platform": "zhihu"}
        ],
        recommendations=[
            "增加小红书内容密度",
            "优化知乎标题",
        ],
        generated_at=datetime.now(),
    )


@pytest.fixture(scope="function")
def sample_crew_input() -> CrewInput:
    """
    Provide a sample crew input.

    Returns:
        CrewInput: Sample crew input instance
    """
    return CrewInput(
        inputs={
            "industry": "AI",
            "keywords": ["AI创业", "人工智能"],
            "target_platform": "xiaohongshu",
        },
        metadata={"test": True},
    )


@pytest.fixture(scope="function")
def sample_crew_result() -> CrewResult:
    """
    Provide a sample crew result.

    Returns:
        CrewResult: Sample crew result instance
    """
    return CrewResult(
        status=CrewStatus.COMPLETED,
        data={"output": "Test output"},
        execution_time=1.5,
    )


# =============================================================================
# Schema Test Data Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def sample_content_brief_schema() -> ContentBriefSchema:
    """
    Provide a sample ContentBrief schema instance.

    Returns:
        ContentBriefSchema: Sample schema instance
    """
    return ContentBriefSchema(
        id="brief-20250320-001",
        topic="AI创业实战指南",
        sub_topics=["MVP开发", "融资策略"],
        keywords=["AI创业", "人工智能", "创业指南"],
        target_audience=[
            AudienceInsight(
                segment=TargetAudience.ENTREPRENEUR,
                size_estimate="10万+",
                interests=["AI技术", "创业融资"],
                pain_points=["资金短缺", "团队管理"],
                preferred_content_type=ContentType.ARTICLE,
            )
        ],
        trending_topics=[
            TrendingTopic(
                keyword="AI Agent",
                search_volume=50000,
                growth_rate=150.0,
                competition_level="medium",
                related_keywords=["智能体", "AI助手"],
                source_platform=PlatformType.XIAOHONGSHU,
            )
        ],
        content_angle="从技术人角度分享AI创业踩坑经验",
        tone="professional",
        suggested_content_type=ContentType.ARTICLE,
        primary_platform=PlatformType.XIAOHONGSHU,
        secondary_platforms=[PlatformType.WECHAT, PlatformType.ZHIHU],
        key_points=["技术栈选择", "融资经验", "团队搭建"],
        call_to_action="关注我获取更多干货",
        hashtags=["#AI创业", "#科技创业"],
    )


@pytest.fixture(scope="function")
def sample_content_draft_schema() -> ContentDraftSchema:
    """
    Provide a sample ContentDraft schema instance.

    Returns:
        ContentDraft: Sample schema instance
    """
    return ContentDraftSchema(
        id="draft-20250320-001",
        brief_id="brief-20250320-001",
        status=DraftStatus.APPROVED,
        topic="AI创业实战指南",
        content_type=ContentType.ARTICLE,
        platforms=[PlatformType.XIAOHONGSHU, PlatformType.WECHAT],
        platform_content=[
            PlatformContent(
                platform=PlatformType.XIAOHONGSHU,
                title="AI创业3年，我踩过的5个坑",
                content_blocks=[
                    ContentBlock(type="text", content="详细内容...")
                ],
                plain_text="作为连续创业者...",
                hashtags=["#AI创业", "#创业干货"],
                character_count=850,
            )
        ],
        tone="professional",
        current_score=QualityScore(
            relevance=9.0,
            readability=8.5,
            engagement_potential=8.0,
            brand_alignment=9.0,
            platform_fit=8.5,
        ),
        tags=["AI", "创业", "经验"],
        category="创业经验",
    )


@pytest.fixture(scope="function")
def sample_publish_result_schema() -> PublishResult:
    """
    Provide a sample PublishResult schema instance.

    Returns:
        PublishResult: Sample schema instance
    """
    return PublishResult(
        id="publish-20250320-001",
        draft_id="draft-20250320-001",
        status=PublishStatusSchema.PUBLISHED,
        schedule_type=ScheduleType.IMMEDIATE,
        started_at=datetime.now() - timedelta(minutes=2),
        completed_at=datetime.now(),
        platforms=[PlatformType.XIAOHONGSHU, PlatformType.WECHAT],
        successful_posts=[
            PlatformPostInfo(
                platform=PlatformType.XIAOHONGSHU,
                post_id="64a1b2c3d4e5f6g7h8i9j0",
                post_url="https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
                published_at=datetime.now() - timedelta(minutes=1),
            )
        ],
        failed_platforms=[],
        errors=[],
        retry_attempts=0,
        max_retries=3,
        success_count=1,
        failure_count=0,
        total_count=1,
    )


@pytest.fixture(scope="function")
def sample_analytics_report_schema() -> AnalyticsReportSchema:
    """
    Provide a sample AnalyticsReport schema instance.

    Returns:
        AnalyticsReport: Sample schema instance
    """
    from src.schemas.analytics_report import (
        EngagementRate,
        MetricValue,
        PerformanceInsight,
        PlatformAnalytics,
    )

    return AnalyticsReportSchema(
        id="analytics-20250320-001",
        content_id="publish-20250320-001",
        publish_result_id="publish-20250320-001",
        draft_id="draft-20250320-001",
        period=TimePeriod.DAY_7,
        period_start=datetime.now() - timedelta(days=7),
        period_end=datetime.now(),
        platform_analytics=[
            PlatformAnalytics(
                platform=PlatformType.XIAOHONGSHU,
                post_id="64a1b2c3d4e5f6g7h8i9j0",
                post_url="https://xiaohongshu.com/explore/64a1b2c3d4e5f6g7h8i9j0",
                metrics={
                    MetricType.VIEWS: MetricValue(
                        type=MetricType.VIEWS,
                        value=15234,
                        previous_value=8567,
                    ),
                    MetricType.LIKES: MetricValue(
                        type=MetricType.LIKES,
                        value=1245,
                        previous_value=678,
                    ),
                },
                engagement_rate=EngagementRate(
                    overall=0.087,
                    like_rate=0.082,
                    comment_rate=0.006,
                    share_rate=0.002,
                    save_rate=0.004,
                ),
                performance_score=8.2,
                period_start=datetime.now() - timedelta(days=7),
                period_end=datetime.now(),
            )
        ],
        total_views=15234,
        total_likes=1245,
        total_comments=89,
        total_shares=34,
        avg_engagement_rate=8.7,
        insights=[
            PerformanceInsight(
                category="strength",
                title="小红书表现突出",
                description="小红书平台互动率高于平均水平35%",
                actionable=True,
                confidence=0.9,
            )
        ],
        next_steps=["在3天内发布系列内容第二篇"],
        follow_up_topics=["AI融资技巧", "团队管理"],
    )


# =============================================================================
# Tool Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def sample_hot_search_tool() -> HotSearchTool:
    """
    Provide a sample HotSearchTool instance.

    Returns:
        HotSearchTool: Sample tool instance
    """
    return HotSearchTool(config={"tikhub_token": "test_token"})


@pytest.fixture(scope="function")
def sample_competitor_analysis_tool() -> CompetitorAnalysisTool:
    """
    Provide a sample CompetitorAnalysisTool instance.

    Returns:
        CompetitorAnalysisTool: Sample tool instance
    """
    return CompetitorAnalysisTool(config={"tikhub_token": "test_token"})


@pytest.fixture(scope="function")
def sample_trend_analysis_tool() -> TrendAnalysisTool:
    """
    Provide a sample TrendAnalysisTool instance.

    Returns:
        TrendAnalysisTool: Sample tool instance
    """
    return TrendAnalysisTool(config={"tikhub_token": "test_token"})


@pytest.fixture(scope="function")
def sample_image_search_tool() -> ImageSearchTool:
    """
    Provide a sample ImageSearchTool instance.

    Returns:
        ImageSearchTool: Sample tool instance
    """
    return ImageSearchTool(config={"api_key": "test_key"})


@pytest.fixture(scope="function")
def sample_hashtag_suggest_tool() -> HashtagSuggestTool:
    """
    Provide a sample HashtagSuggestTool instance.

    Returns:
        HashtagSuggestTool: Sample tool instance
    """
    return HashtagSuggestTool(config={})


@pytest.fixture(scope="function")
def sample_seo_optimize_tool() -> SEOOptimizeTool:
    """
    Provide a sample SEOOptimizeTool instance.

    Returns:
        SEOOptimizeTool: Sample tool instance
    """
    return SEOOptimizeTool(config={})


@pytest.fixture(scope="function")
def sample_data_collect_tool() -> DataCollectTool:
    """
    Provide a sample DataCollectTool instance.

    Returns:
        DataCollectTool: Sample tool instance
    """
    return DataCollectTool(config={"tikhub_token": "test_token"})


@pytest.fixture(scope="function")
def sample_analytics_report_tool() -> AnalyticsReportTool:
    """
    Provide a sample AnalyticsReportTool instance.

    Returns:
        AnalyticsReportTool: Sample tool instance
    """
    return AnalyticsReportTool(config={})


# =============================================================================
# Async Support
# =============================================================================


@pytest.fixture(scope="function")
def event_loop():
    """
    Create an event loop for async tests.

    Yields:
        Event loop for async test execution
    """
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Helpers
# =============================================================================


@pytest.fixture(scope="function")
def assert_valid_tool_result():
    """
    Provide a helper function to validate tool results.

    Returns:
        Callable: Function that validates ToolResult objects
    """
    def _assert(result: ToolResult, expected_status: ToolStatus = ToolStatus.SUCCESS) -> None:
        """Assert that a ToolResult has the expected status."""
        assert isinstance(result, ToolResult)
        assert result.status == expected_status
        if expected_status == ToolStatus.SUCCESS:
            assert result.data is not None
            assert result.error is None
        elif expected_status == ToolStatus.FAILED:
            assert result.error is not None

    return _assert


@pytest.fixture(scope="function")
def mock_http_request(mocker: MockerFixture) -> Mock:
    """
    Mock HTTP requests for external API calls.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        Mock: Mocked requests function
    """
    mock = mocker.patch("requests.get")
    mock.return_value = Mock(
        status_code=200,
        json=lambda: {"data": "mocked response"},
        text="mocked text",
    )
    return mock


# =============================================================================
# Environment Setup
# =============================================================================


@pytest.fixture(scope="function", autouse=True)
def set_test_environment(mocker: MockerFixture) -> None:
    """
    Set environment variables for testing.

    Automatically applied to all tests.

    Args:
        mocker: Pytest mocker fixture
    """
    mocker.patch.dict(
        "os.environ",
        {
            "ANTHROPIC_API_KEY": "test-key",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
        },
    )


@pytest.fixture(scope="function")
def temp_config_file(tmp_path) -> str:
    """
    Create a temporary config file for testing.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        str: Path to temporary config file
    """
    config_data = {
        "tikhub_token": "test_token",
        "api_key": "test_api_key",
        "platforms": {
            "xiaohongshu": {"enabled": True},
            "wechat": {"enabled": True},
        },
    }
    config_file = tmp_path / "test_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
    return str(config_file)


# =============================================================================
# Security Test Fixtures (from CEO Review)
# =============================================================================


@pytest.fixture(scope="function")
def test_user():
    """测试用户。"""
    from src.core.auth import User, UserRole
    return User(
        id="test-user-001",
        username="testuser",
        role=UserRole.USER,
    )


@pytest.fixture(scope="function")
def test_admin():
    """测试管理员。"""
    from src.core.auth import User, UserRole
    return User(
        id="test-admin-001",
        username="admin",
        role=UserRole.ADMIN,
    )


@pytest.fixture(scope="function")
def jwt_manager():
    """JWT 管理器。"""
    from src.core.auth import JWTManager
    return JWTManager(
        secret_key="test-secret-key-for-testing-only",
        expires_in=3600,
    )


@pytest.fixture(scope="function")
def encryption_manager():
    """加密管理器。"""
    from src.core.auth import EncryptionManager
    return EncryptionManager()


@pytest.fixture(scope="function")
def mock_llm_response_for_content():
    """Mock LLM 内容生成响应。"""
    return {
        "topic": "AI 编程工具",
        "title": "5 个提升效率的 AI 编程工具",
        "body": "本文介绍 5 个能显著提升编程效率的 AI 工具...\n\n1. Claude\n2. ChatGPT\n3. GitHub Copilot\n4. Cursor\n5. Tabnine",
        "hashtags": ["AI", "编程", "效率工具"],
        "images": [],
    }


@pytest.fixture(scope="function")
def mock_hotspot_data():
    """Mock 热点数据。"""
    return [
        {
            "title": "AI 编程工具爆火",
            "source": "weibo",
            "score": 95.5,
            "trend": "rising",
            "url": "https://weibo.com/test-1",
        },
        {
            "title": "Claude 4 发布",
            "source": "zhihu",
            "score": 88.2,
            "trend": "stable",
            "url": "https://zhihu.com/test-2",
        },
    ]


# =============================================================================
# Test Utility Functions
# =============================================================================


def assert_success_result(result):
    """断言结果成功。"""
    assert result.success is True
    assert result.data is not None
    assert result.error is None


def assert_error_result(result, error_code: str = None):
    """断言结果失败。"""
    assert result.success is False
    assert result.error is not None
    if error_code:
        assert result.error_code == error_code
