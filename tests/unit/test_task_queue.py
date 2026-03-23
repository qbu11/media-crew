"""
Unit tests for TaskQueue service.

Tests cover:
- Submit tasks
- Get pending tasks
- Start, complete, fail tasks
- Error handling
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.task import Task, TaskStatus
from src.services.task_queue import TaskQueue


@pytest.fixture
async def task_queue():
    """Create a TaskQueue with in-memory database."""
    db_url = "sqlite+aiosqlite:///:memory:"
    tq = TaskQueue(db_url=db_url)

    # Create tables
    async with tq.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield tq

    async with tq.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await tq.engine.dispose()


class TestSubmitTask:
    async def test_submit_success(self, task_queue):
        result = await task_queue.submit_task("hotspot_detection", {"keywords": ["AI"]})
        assert result.success is True
        assert result.data.task_type == "hotspot_detection"
        assert result.data.status == TaskStatus.PENDING
        assert result.data.payload == {"keywords": ["AI"]}

    async def test_submit_no_payload(self, task_queue):
        result = await task_queue.submit_task("content_generation")
        assert result.success is True
        assert result.data.payload == {}

    async def test_submit_multiple(self, task_queue):
        await task_queue.submit_task("task_1")
        await task_queue.submit_task("task_2")
        await task_queue.submit_task("task_3")

        result = await task_queue.get_pending_tasks(limit=10)
        assert result.success is True
        assert len(result.data) == 3


class TestGetPendingTasks:
    async def test_get_pending(self, task_queue):
        await task_queue.submit_task("task_1")
        await task_queue.submit_task("task_2")

        result = await task_queue.get_pending_tasks()
        assert result.success is True
        assert len(result.data) == 2

    async def test_get_pending_with_limit(self, task_queue):
        for i in range(5):
            await task_queue.submit_task(f"task_{i}")

        result = await task_queue.get_pending_tasks(limit=3)
        assert result.success is True
        assert len(result.data) == 3

    async def test_get_pending_excludes_running(self, task_queue):
        r1 = await task_queue.submit_task("task_1")
        await task_queue.submit_task("task_2")

        # Start task_1
        await task_queue.start_task(r1.data.id)

        result = await task_queue.get_pending_tasks()
        assert result.success is True
        assert len(result.data) == 1


class TestStartTask:
    async def test_start_success(self, task_queue):
        submit_result = await task_queue.submit_task("test_task")
        task_id = submit_result.data.id

        result = await task_queue.start_task(task_id)
        assert result.success is True
        assert result.data.status == TaskStatus.RUNNING
        assert result.data.started_at is not None

    async def test_start_not_found(self, task_queue):
        result = await task_queue.start_task("nonexistent-id")
        assert result.success is False
        assert result.error_code == "TASK_NOT_FOUND"


class TestCompleteTask:
    async def test_complete_success(self, task_queue):
        submit_result = await task_queue.submit_task("test_task")
        task_id = submit_result.data.id

        await task_queue.start_task(task_id)
        result = await task_queue.complete_task(task_id, {"output": "done"})
        assert result.success is True
        assert result.data.status == TaskStatus.COMPLETED
        assert result.data.result == {"output": "done"}
        assert result.data.completed_at is not None

    async def test_complete_not_found(self, task_queue):
        result = await task_queue.complete_task("nonexistent-id")
        assert result.success is False


class TestFailTask:
    async def test_fail_success(self, task_queue):
        submit_result = await task_queue.submit_task("test_task")
        task_id = submit_result.data.id

        await task_queue.start_task(task_id)
        result = await task_queue.fail_task(task_id, "Connection timeout")
        assert result.success is True
        assert result.data.status == TaskStatus.FAILED
        assert result.data.error == "Connection timeout"
        assert result.data.completed_at is not None

    async def test_fail_not_found(self, task_queue):
        result = await task_queue.fail_task("nonexistent-id", "error")
        assert result.success is False
