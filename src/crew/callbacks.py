"""
CrewAI 回调管理器 — 将执行事件转换为 WS 事件

供 ContentOrchestrator 调用，实时推送 agent/tool 执行状态到前端。
"""

from datetime import datetime
from typing import Any

from src.api.ws import sio


class CallbackHandler:
    """
    CrewAI 回调处理器。

    职责：
    - 在 agent 开始/完成时发射 WS 事件
    - 在工具调用开始/结束时发射 WS 事件
    - 记录每个 agent 和 tool 的执行时间
    """

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.agent_start_time: dict[str, datetime] = {}
        self.tool_start_time: dict[str, datetime] = {}

    async def emit_workflow_started(
        self,
        agents: list[str],
        inputs: dict[str, Any],
    ) -> None:
        """发送工作流开始事件。"""
        await sio.emit(
            "event",
            {
                "type": "workflow_started",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "execution_id": self.execution_id,
                    "crew_type": "content",
                    "agents": agents,
                    "inputs": inputs,
                },
            },
        )

    async def emit_agent_started(
        self,
        agent_id: str,
        agent_name: str,
        input_data: dict[str, Any],
    ) -> None:
        """发送 agent 开始执行事件。"""
        self.agent_start_time[agent_id] = datetime.now()
        await sio.emit(
            "event",
            {
                "type": "agent_started",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "execution_id": self.execution_id,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "input": input_data,
                },
            },
        )

    async def emit_agent_completed(
        self,
        agent_id: str,
        agent_name: str,
        output: dict[str, Any],
    ) -> None:
        """发送 agent 完成事件。"""
        start = self.agent_start_time.get(agent_id, datetime.now())
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        await sio.emit(
            "event",
            {
                "type": "agent_completed",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "execution_id": self.execution_id,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "output": output,
                    "duration_ms": duration_ms,
                },
            },
        )

    async def emit_agent_failed(
        self,
        agent_id: str,
        agent_name: str,
        error: str,
    ) -> None:
        """发送 agent 失败事件。"""
        start = self.agent_start_time.get(agent_id, datetime.now())
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        await sio.emit(
            "event",
            {
                "type": "agent_failed",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "execution_id": self.execution_id,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "error": error,
                    "duration_ms": duration_ms,
                },
            },
        )

    async def emit_tool_start(
        self,
        agent_id: str,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> None:
        """发送工具调用开始事件。"""
        key = f"{agent_id}:{tool_name}"
        self.tool_start_time[key] = datetime.now()
        await sio.emit(
            "event",
            {
                "type": "tool_call_start",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "execution_id": self.execution_id,
                    "agent_id": agent_id,
                    "tool_name": tool_name,
                    "input": input_data,
                },
            },
        )

    async def emit_tool_end(
        self,
        agent_id: str,
        tool_name: str,
        status: str,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """发送工具调用结束事件。"""
        key = f"{agent_id}:{tool_name}"
        start = self.tool_start_time.get(key, datetime.now())
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        payload: dict[str, Any] = {
            "type": "tool_call_end",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "execution_id": self.execution_id,
                "agent_id": agent_id,
                "tool_name": tool_name,
                "status": status,
                "duration_ms": duration_ms,
            },
        }
        if output is not None:
            payload["data"]["output"] = output
        if error is not None:
            payload["data"]["error"] = error

        await sio.emit("event", payload)
