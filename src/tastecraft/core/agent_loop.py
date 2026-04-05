"""Core agent loop using Anthropic Python SDK."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message

from tastecraft.tools.base import BaseTool, ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of an agent loop execution."""

    success: bool
    output: str
    turns: int = 0
    tool_calls: int = 0
    elapsed_seconds: float = 0.0
    messages: list[dict[str, Any]] = field(default_factory=list)


async def agent_loop(
    system_prompt: str,
    tools: ToolRegistry,
    initial_message: str,
    *,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
    max_turns: int = 20,
    api_key: str | None = None,
) -> AgentResult:
    """
    Core agent loop. Spawned fresh for each pipeline run.

    Stateless — taste profile and context injected via system_prompt.
    Each turn: call Claude -> if tool_use, execute tools and continue -> else return text.
    """
    client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": initial_message}]
    tool_schemas = tools.all_schemas()
    total_tool_calls = 0
    start = time.monotonic()

    for turn in range(max_turns):
        logger.info("Agent turn %d/%d", turn + 1, max_turns)

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        response: Message = await client.messages.create(**kwargs)

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Extract tool_use blocks
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # No tool calls — agent is done
            text_parts = [b.text for b in response.content if b.type == "text"]
            output = "".join(text_parts)
            elapsed = time.monotonic() - start
            logger.info(
                "Agent finished in %d turns, %d tool calls, %.1fs",
                turn + 1,
                total_tool_calls,
                elapsed,
            )
            return AgentResult(
                success=True,
                output=output,
                turns=turn + 1,
                tool_calls=total_tool_calls,
                elapsed_seconds=elapsed,
                messages=messages,
            )

        # Execute each tool call
        tool_results: list[dict[str, Any]] = []
        for tu in tool_uses:
            total_tool_calls += 1
            tool = tools.get(tu.name)
            if tool is None:
                logger.warning("Unknown tool requested: %s", tu.name)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": f"Error: unknown tool '{tu.name}'",
                    "is_error": True,
                })
                continue

            logger.info("Executing tool: %s(%s)", tu.name, _truncate(str(tu.input), 200))
            result = await tool.safe_execute(**tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result.to_content_str(),
            })

        messages.append({"role": "user", "content": tool_results})

    # Max turns exhausted
    elapsed = time.monotonic() - start
    logger.warning("Agent hit max turns (%d)", max_turns)
    return AgentResult(
        success=False,
        output=f"Agent reached max turns ({max_turns}) without completing.",
        turns=max_turns,
        tool_calls=total_tool_calls,
        elapsed_seconds=elapsed,
        messages=messages,
    )


def _truncate(s: str, max_len: int) -> str:
    return s if len(s) <= max_len else s[: max_len - 3] + "..."
