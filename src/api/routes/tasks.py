"""Task management routes."""

from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    RESEARCH = "research"
    GENERATE = "generate"
    PUBLISH = "publish"
    ANALYZE = "analyze"


class Task(BaseModel):
    """Task model."""

    id: str
    type: TaskType
    status: TaskStatus
    title: str
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None


# In-memory task storage
_task_store: dict[str, Task] = {}


@router.get("/")
async def list_tasks() -> dict[str, Any]:
    """List all tasks."""
    return {
        "tasks": [
            {
                "id": t.id,
                "type": t.type.value,
                "status": t.status.value,
                "title": t.title,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "progress": t.progress,
                "error": t.error,
            }
            for t in _task_store.values()
        ]
    }


@router.post("/create")
async def create_task(
    type: TaskType, title: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a new task."""
    task_id = f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    now = datetime.now()

    task = Task(
        id=task_id,
        type=type,
        status=TaskStatus.PENDING,
        title=title,
        created_at=now,
        updated_at=now,
    )
    _task_store[task_id] = task

    return {
        "success": True,
        "task": {
            "id": task.id,
            "type": task.type.value,
            "status": task.status.value,
            "title": task.title,
        },
    }


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    """Get task details."""
    if task_id not in _task_store:
        return {"success": False, "error": "Task not found"}

    t = _task_store[task_id]
    return {
        "success": True,
        "task": {
            "id": t.id,
            "type": t.type.value,
            "status": t.status.value,
            "title": t.title,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "progress": t.progress,
            "result": t.result,
            "error": t.error,
        },
    }


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel a task."""
    if task_id not in _task_store:
        return {"success": False, "error": "Task not found"}

    task = _task_store[task_id]
    if task.status == TaskStatus.RUNNING:
        task.status = TaskStatus.FAILED
        task.error = "Cancelled by user"
        task.updated_at = datetime.now()

    return {"success": True, "message": "Task cancelled"}
