"""Agent monitoring API routes.

Provides endpoints for the Multi-Agent Dashboard to monitor
agent status, metrics, and execution history.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Agent Monitor"])

# In-memory agent registry (will be replaced with actual CrewAI integration)
_agent_registry: dict[str, dict[str, Any]] = {}


def _get_default_agents() -> list[dict[str, Any]]:
    """Return default agent definitions matching the Crew system."""
    now = datetime.now().isoformat()
    return [
        {
            "id": "agent_001",
            "name": "ContentOrchestrator",
            "role": "内容编排者",
            "goal": "协调子Agent完成内容生产全流程",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_002",
            "name": "Researcher",
            "role": "热点研究员",
            "goal": "追踪热点、分析趋势、提供研究报告",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_003",
            "name": "Marketer",
            "role": "营销策划师",
            "goal": "制定内容策略、规划传播方案",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_004",
            "name": "Copywriter",
            "role": "文案创作者",
            "goal": "创作高质量文案、生成多版本供选择",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_005",
            "name": "Designer",
            "role": "视觉设计师",
            "goal": "生成配图、设计封面、优化视觉呈现",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_006",
            "name": "ContentReviewer",
            "role": "内容审核员",
            "goal": "审核内容质量、把关品牌调性",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_007",
            "name": "PlatformAdapter",
            "role": "平台适配师",
            "goal": "根据平台特性调整内容格式",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_008",
            "name": "PlatformPublisher",
            "role": "平台发布员",
            "goal": "执行发布操作、处理发布结果",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
        {
            "id": "agent_009",
            "name": "DataAnalyst",
            "role": "数据分析师",
            "goal": "采集平台数据、生成分析报告",
            "status": "idle",
            "last_activity": now,
            "metrics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "tokens_used": 0,
            },
        },
    ]


# --- Agent endpoints ---


@router.get("/agents")
async def list_agents() -> dict[str, Any]:
    """List all registered agents."""
    agents = _get_default_agents()
    # Merge with runtime state if available
    for agent in agents:
        if agent["id"] in _agent_registry:
            agent.update(_agent_registry[agent["id"]])
    return {"success": True, "data": agents}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict[str, Any]:
    """Get agent details."""
    agents = _get_default_agents()
    for agent in agents:
        if agent["id"] == agent_id:
            if agent_id in _agent_registry:
                agent.update(_agent_registry[agent_id])
            return {"success": True, "data": agent}
    return {"success": False, "error": f"Agent {agent_id} not found"}


@router.get("/agents/{agent_id}/history")
async def get_agent_history(agent_id: str) -> dict[str, Any]:
    """Get agent execution history."""
    # Placeholder - will be populated by actual executions
    return {"success": True, "data": []}


# --- Crew endpoints ---


@router.get("/crews")
async def list_crews() -> dict[str, Any]:
    """List all crews."""
    crews = [
        {
            "id": "crew_001",
            "name": "ContentCrew",
            "status": "idle",
            "agents": [
                "agent_001", "agent_002", "agent_003",
                "agent_004", "agent_005", "agent_006", "agent_007",
            ],
            "current_step": 0,
            "total_steps": 7,
        },
        {
            "id": "crew_002",
            "name": "PublishCrew",
            "status": "idle",
            "agents": ["agent_007", "agent_008"],
            "current_step": 0,
            "total_steps": 2,
        },
        {
            "id": "crew_003",
            "name": "AnalyticsCrew",
            "status": "idle",
            "agents": ["agent_009"],
            "current_step": 0,
            "total_steps": 1,
        },
    ]
    return {"success": True, "data": crews}


@router.get("/crews/{crew_id}")
async def get_crew(crew_id: str) -> dict[str, Any]:
    """Get crew details."""
    crews = (await list_crews())["data"]
    for crew in crews:
        if crew["id"] == crew_id:
            return {"success": True, "data": crew}
    return {"success": False, "error": f"Crew {crew_id} not found"}


@router.post("/crews")
async def start_crew(data: dict[str, Any]) -> dict[str, Any]:
    """Start a new crew execution."""
    return {
        "success": True,
        "data": {
            "id": f"crew_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": "ContentCrew",
            "status": "running",
            "topic": data.get("topic", ""),
            "platforms": data.get("platforms", []),
            "started_at": datetime.now().isoformat(),
        },
    }


# --- Task endpoints (v1) ---


@router.get("/tasks")
async def list_tasks_v1(
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List tasks with optional filtering."""
    # Placeholder
    return {
        "success": True,
        "data": [],
        "meta": {"total": 0, "page": page, "limit": limit},
    }


@router.get("/tasks/{task_id}")
async def get_task_v1(task_id: str) -> dict[str, Any]:
    """Get task details."""
    return {"success": False, "error": f"Task {task_id} not found"}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel a running task."""
    return {"success": True, "data": {"task_id": task_id, "status": "cancelled"}}


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str) -> dict[str, Any]:
    """Retry a failed task."""
    return {"success": True, "data": {"task_id": task_id, "status": "pending"}}


# --- System endpoints ---


@router.get("/system/stats")
async def get_system_stats() -> dict[str, Any]:
    """Get system-wide statistics."""
    return {
        "success": True,
        "data": {
            "active_crews": 0,
            "active_agents": 0,
            "pending_tasks": 0,
            "completed_today": 0,
            "total_tokens_today": 0,
            "api_calls_today": 0,
        },
    }


@router.get("/system/health")
async def system_health() -> dict[str, Any]:
    """System health check."""
    return {"success": True, "data": {"status": "healthy"}}
