"""
Unit tests for Content Service.

测试内容服务层的业务逻辑。
"""

import pytest
from datetime import datetime

from src.services.content_service import ContentService
from src.schemas.validation import ContentStatus


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


@pytest.mark.unit
class TestContentService:
    """内容服务测试。"""

    @pytest.mark.asyncio
    async def test_create_content_success(self, db_session):
        """测试创建内容成功。"""
        service = ContentService(db_session)

        result = await service.create_content(
            topic="AI 编程工具",
            title="5 个提升效率的 AI 编程工具",
            body="本文介绍...",
            platforms=["xiaohongshu", "wechat"],
            user_id="user-001",
        )

        assert_success_result(result)
        assert result.data.topic == "AI 编程工具"
        assert result.data.status == ContentStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_content_with_images(self, db_session):
        """测试创建带图片的内容。"""
        service = ContentService(db_session)

        result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
            images=["https://example.com/image1.jpg"],
            hashtags=["AI", "编程"],
        )

        assert_success_result(result)
        assert len(result.data.images) == 1
        assert result.data.hashtags == ["AI", "编程"]

    @pytest.mark.asyncio
    async def test_get_content_success(self, db_session):
        """测试获取内容成功。"""
        service = ContentService(db_session)

        # 先创建
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
        )

        # 再获取
        get_result = await service.get_content(
            content_id=create_result.data.id,
            user_id="user-001",
        )

        assert_success_result(get_result)
        assert get_result.data.id == create_result.data.id

    @pytest.mark.asyncio
    async def test_get_content_not_found(self, db_session):
        """测试获取不存在的内容。"""
        service = ContentService(db_session)

        result = await service.get_content(
            content_id="nonexistent-id",
            user_id="user-001",
        )

        assert_error_result(result, "CONTENT_NOT_FOUND")

    @pytest.mark.asyncio
    async def test_get_content_wrong_user(self, db_session):
        """测试获取其他用户的内容（权限检查）。"""
        service = ContentService(db_session)

        # 用户 A 创建内容
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-a",
        )

        # 用户 B 尝试获取
        get_result = await service.get_content(
            content_id=create_result.data.id,
            user_id="user-b",
        )

        assert_error_result(get_result, "CONTENT_NOT_FOUND")

    @pytest.mark.asyncio
    async def test_update_status_draft_to_pending_review(self, db_session):
        """测试状态转换: draft -> pending_review。"""
        service = ContentService(db_session)

        # 创建
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
        )

        # 更新状态
        update_result = await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.PENDING_REVIEW,
            user_id="user-001",
        )

        assert_success_result(update_result)
        assert update_result.data.status == ContentStatus.PENDING_REVIEW

    @pytest.mark.asyncio
    async def test_update_status_approved_to_draft_invalid(self, db_session):
        """测试无效状态转换: approved -> draft。"""
        service = ContentService(db_session)

        # 创建并审批
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
        )

        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.PENDING_REVIEW,
            user_id="user-001",
        )

        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.APPROVED,
            user_id="user-001",
        )

        # 尝试无效转换
        update_result = await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.DRAFT,
            user_id="user-001",
        )

        assert_error_result(update_result, "INVALID_STATUS_TRANSITION")

    @pytest.mark.asyncio
    async def test_list_contents(self, db_session):
        """测试列出内容。"""
        service = ContentService(db_session)

        # 创建多个内容
        for i in range(5):
            await service.create_content(
                topic=f"测试选题 {i}",
                title=f"测试标题 {i}",
                body="测试正文",
                platforms=["xiaohongshu"],
                user_id="user-001",
            )

        result = await service.list_contents(
            user_id="user-001",
            limit=3,
            offset=0,
        )

        assert_success_result(result)
        assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_list_contents_filter_by_status(self, db_session):
        """测试按状态过滤内容。"""
        service = ContentService(db_session)

        # 创建多个内容并更新状态
        for i in range(3):
            create_result = await service.create_content(
                topic=f"测试选题 {i}",
                title=f"测试标题 {i}",
                body="测试正文",
                platforms=["xiaohongshu"],
                user_id="user-001",
            )

            if i < 2:
                await service.update_content_status(
                    content_id=create_result.data.id,
                    status=ContentStatus.PENDING_REVIEW,
                    user_id="user-001",
                )

        # 只获取 pending_review
        result = await service.list_contents(
            user_id="user-001",
            status=ContentStatus.PENDING_REVIEW,
        )

        assert_success_result(result)
        assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_delete_content_draft(self, db_session):
        """测试删除草稿内容。"""
        service = ContentService(db_session)

        # 创建
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
        )

        # 删除
        delete_result = await service.delete_content(
            content_id=create_result.data.id,
            user_id="user-001",
        )

        assert_success_result(delete_result)

        # 验证已删除
        get_result = await service.get_content(
            content_id=create_result.data.id,
            user_id="user-001",
        )

        assert_error_result(get_result, "CONTENT_NOT_FOUND")

    @pytest.mark.asyncio
    async def test_delete_published_content_forbidden(self, db_session):
        """测试删除已发布内容（禁止）。"""
        service = ContentService(db_session)

        # 创建并发布
        create_result = await service.create_content(
            topic="测试选题",
            title="测试标题",
            body="测试正文",
            platforms=["xiaohongshu"],
            user_id="user-001",
        )

        # 模拟发布状态
        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.PENDING_REVIEW,
            user_id="user-001",
        )
        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.APPROVED,
            user_id="user-001",
        )
        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.PUBLISHING,
            user_id="user-001",
        )
        await service.update_content_status(
            content_id=create_result.data.id,
            status=ContentStatus.PUBLISHED,
            user_id="user-001",
        )

        # 尝试删除
        delete_result = await service.delete_content(
            content_id=create_result.data.id,
            user_id="user-001",
        )

        assert_error_result(delete_result, "CANNOT_DELETE_PUBLISHED")


@pytest.mark.unit
class TestStatusStateMachine:
    """状态机测试。"""

    def test_valid_transitions(self):
        """测试所有有效状态转换。"""
        valid_transitions = [
            (ContentStatus.DRAFT, ContentStatus.PENDING_REVIEW),
            (ContentStatus.PENDING_REVIEW, ContentStatus.APPROVED),
            (ContentStatus.PENDING_REVIEW, ContentStatus.REJECTED),
            (ContentStatus.APPROVED, ContentStatus.SCHEDULED),
            (ContentStatus.APPROVED, ContentStatus.PUBLISHING),
            (ContentStatus.REJECTED, ContentStatus.DRAFT),
            (ContentStatus.SCHEDULED, ContentStatus.PUBLISHING),
            (ContentStatus.SCHEDULED, ContentStatus.DRAFT),  # 取消定时
            (ContentStatus.PUBLISHING, ContentStatus.PUBLISHED),
            (ContentStatus.PUBLISHING, ContentStatus.FAILED),
            (ContentStatus.FAILED, ContentStatus.DRAFT),
            (ContentStatus.FAILED, ContentStatus.PUBLISHING),  # 重试
        ]

        for current, target in valid_transitions:
            assert ContentService._is_valid_status_transition(current, target), \
                f"Expected transition {current} -> {target} to be valid"

    def test_invalid_transitions(self):
        """测试无效状态转换。"""
        invalid_transitions = [
            (ContentStatus.DRAFT, ContentStatus.PUBLISHED),  # 跳过审批
            (ContentStatus.APPROVED, ContentStatus.DRAFT),  # 不能回退
            (ContentStatus.PUBLISHED, ContentStatus.DRAFT),  # 已发布不能回退
            (ContentStatus.PUBLISHED, ContentStatus.FAILED),  # 已发布不能失败
        ]

        for current, target in invalid_transitions:
            assert not ContentService._is_valid_status_transition(current, target), \
                f"Expected transition {current} -> {target} to be invalid"
