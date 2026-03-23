"""
Content Service Layer

提供内容相关的业务逻辑，解耦 Agent 和数据库。
"""

from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.error_handling import Result, error, success
from src.models.content import Content
from src.schemas.validation import ContentStatus

logger = logging.getLogger(__name__)


class ContentService:
    """内容服务。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_content(
        self,
        topic: str,
        title: str,
        body: str,
        platforms: list[str],
        user_id: str,
        images: list[str] | None = None,
        video_url: str | None = None,
        hashtags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Result[Content]:
        """
        创建内容草稿。

        Args:
            topic: 选题
            title: 标题
            body: 正文
            platforms: 目标平台列表
            user_id: 用户 ID
            images: 图片 URL 列表
            video_url: 视频 URL
            hashtags: 话题标签
            metadata: 元数据

        Returns:
            Result[Content]: 创建的内容对象
        """
        try:
            content = Content(
                topic=topic,
                title=title,
                body=body,
                platforms=platforms,
                user_id=user_id,
                images=images or [],
                video_url=video_url,
                hashtags=hashtags or [],
                status=ContentStatus.DRAFT,
                extra_metadata=metadata or {},
                created_at=datetime.utcnow(),
            )

            self.session.add(content)
            await self.session.commit()
            await self.session.refresh(content)

            logger.info(f"创建内容成功: {content.id}")
            return success(content)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建内容失败: {e}")
            return error(str(e), "CREATE_CONTENT_FAILED")

    async def get_content(self, content_id: str, user_id: str) -> Result[Content]:
        """
        获取内容。

        Args:
            content_id: 内容 ID
            user_id: 用户 ID（用于权限检查）

        Returns:
            Result[Content]: 内容对象
        """
        try:
            stmt = select(Content).where(
                Content.id == content_id,
                Content.user_id == user_id,  # 权限检查
            )
            result = await self.session.execute(stmt)
            content = result.scalar_one_or_none()

            if content is None:
                return error(
                    f"内容不存在或无权访问: {content_id}",
                    "CONTENT_NOT_FOUND",
                )

            return success(content)

        except Exception as e:
            logger.error(f"获取内容失败: {e}")
            return error(str(e), "GET_CONTENT_FAILED")

    async def update_content_status(
        self,
        content_id: str,
        status: ContentStatus,
        user_id: str,
    ) -> Result[Content]:
        """
        更新内容状态。

        Args:
            content_id: 内容 ID
            status: 新状态
            user_id: 用户 ID

        Returns:
            Result[Content]: 更新后的内容对象
        """
        try:
            # 获取内容
            result = await self.get_content(content_id, user_id)
            if not result.success:
                return result

            content = result.data

            # 验证状态转换
            if not self._is_valid_status_transition(content.status, status):
                return error(
                    f"无效的状态转换: {content.status} -> {status}",
                    "INVALID_STATUS_TRANSITION",
                )

            # 更新状态
            content.status = status
            content.updated_at = datetime.utcnow()

            await self.session.commit()
            await self.session.refresh(content)

            logger.info(f"更新内容状态成功: {content_id} -> {status}")
            return success(content)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新内容状态失败: {e}")
            return error(str(e), "UPDATE_STATUS_FAILED")

    async def list_contents(
        self,
        user_id: str,
        status: ContentStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Result[list[Content]]:
        """
        列出内容。

        Args:
            user_id: 用户 ID
            status: 状态过滤
            limit: 返回数量
            offset: 偏移量

        Returns:
            Result[list[Content]]: 内容列表
        """
        try:
            stmt = select(Content).where(Content.user_id == user_id)

            if status:
                stmt = stmt.where(Content.status == status)

            stmt = stmt.order_by(Content.created_at.desc()).limit(limit).offset(offset)

            result = await self.session.execute(stmt)
            contents = result.scalars().all()

            return success(list(contents))

        except Exception as e:
            logger.error(f"列出内容失败: {e}")
            return error(str(e), "LIST_CONTENTS_FAILED")

    async def delete_content(self, content_id: str, user_id: str) -> Result[bool]:
        """
        删除内容。

        Args:
            content_id: 内容 ID
            user_id: 用户 ID

        Returns:
            Result[bool]: 是否删除成功
        """
        try:
            # 获取内容
            result = await self.get_content(content_id, user_id)
            if not result.success:
                return result

            content = result.data

            # 检查是否可以删除
            if content.status == ContentStatus.PUBLISHED:
                return error(
                    "已发布的内容不能删除",
                    "CANNOT_DELETE_PUBLISHED",
                )

            await self.session.delete(content)
            await self.session.commit()

            logger.info(f"删除内容成功: {content_id}")
            return success(True)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除内容失败: {e}")
            return error(str(e), "DELETE_CONTENT_FAILED")

    @staticmethod
    def _is_valid_status_transition(
        current: ContentStatus,
        target: ContentStatus,
    ) -> bool:
        """
        验证状态转换是否有效。

        状态机：
        draft -> pending_review -> approved -> scheduled -> publishing -> published
                                 -> rejected -> draft
                                             -> failed -> draft
        """
        valid_transitions = {
            ContentStatus.DRAFT: {
                ContentStatus.PENDING_REVIEW,
            },
            ContentStatus.PENDING_REVIEW: {
                ContentStatus.APPROVED,
                ContentStatus.REJECTED,
            },
            ContentStatus.APPROVED: {
                ContentStatus.SCHEDULED,
                ContentStatus.PUBLISHING,
            },
            ContentStatus.REJECTED: {
                ContentStatus.DRAFT,
            },
            ContentStatus.SCHEDULED: {
                ContentStatus.PUBLISHING,
                ContentStatus.DRAFT,  # 取消定时
            },
            ContentStatus.PUBLISHING: {
                ContentStatus.PUBLISHED,
                ContentStatus.FAILED,
            },
            ContentStatus.FAILED: {
                ContentStatus.DRAFT,
                ContentStatus.PUBLISHING,  # 重试
            },
            ContentStatus.PUBLISHED: set(),  # 已发布不能转换
        }

        return target in valid_transitions.get(current, set())
