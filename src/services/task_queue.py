"""任务队列服务"""
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.error_handling import Result, error, success
from src.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskQueue:
    """异步任务队列"""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_async_engine(self.db_url)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def submit_task(
        self,
        task_type: str,
        payload: dict | None = None,
    ) -> Result[Task]:
        """提交任务"""
        async with self.SessionLocal() as session:
            try:
                task = Task(
                    task_type=task_type,
                    payload=payload or {},
                    status=TaskStatus.PENDING,
                )
                session.add(task)
                await session.commit()
                await session.refresh(task)

                logger.info(f"提交任务成功: {task.id} ({task_type})")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"提交任务失败: {e}")
                return error(f"提交任务失败: {e}", "TASK_SUBMIT_ERROR")

    async def get_pending_tasks(self, limit: int = 10) -> Result[list[Task]]:
        """获取待处理任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task)
                    .where(Task.status == TaskStatus.PENDING)
                    .limit(limit)
                )
                tasks = result.scalars().all()
                return success(list(tasks))

            except Exception as e:
                logger.error(f"获取待处理任务失败: {e}")
                return error(f"获取待处理任务失败: {e}", "TASK_GET_ERROR")

    async def start_task(self, task_id: str) -> Result[Task]:
        """开始执行任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.info(f"开始执行任务: {task.id}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"开始任务失败: {e}")
                return error(f"开始任务失败: {e}", "TASK_START_ERROR")

    async def complete_task(
        self,
        task_id: str,
        result_data: dict | None = None,
    ) -> Result[Task]:
        """完成任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.COMPLETED
                task.result = result_data
                task.completed_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.info(f"完成任务: {task.id}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"完成任务失败: {e}")
                return error(f"完成任务失败: {e}", "TASK_COMPLETE_ERROR")

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
    ) -> Result[Task]:
        """任务失败"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.FAILED
                task.error = error_message
                task.completed_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.error(f"任务失败: {task.id} - {error_message}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"标记任务失败失败: {e}")
                return error(f"标记任务失败失败: {e}", "TASK_FAIL_ERROR")
