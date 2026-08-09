"""构建Agent

图结构（create_agent + return_direct）：

  START → model ──有工具──► tools ──► ?
                 └无工具──► END         │
                                       ├ answer_from_notes / list_notes
                                       │   (return_direct=True) → END
                                       └ create/update/delete_note
                                           → model（短确认）→ END
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import before_model
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

from .chains import get_llm
from .config import DEFAULT_THREAD_ID
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """你是学习笔记助手。规则：
1. 问知识点 → 只调用 answer_from_notes（结果会直接给用户，勿复述）
2. 列笔记/按标签找 → list_notes
3. 明确要求创建/更新/删除时才用对应写工具；写完只用一句话确认
4. 不要编造笔记内容；回答简洁
"""


def missing_tool_messages(messages: list[AnyMessage]) -> list[ToolMessage]:
    """补齐「有 tool_calls 却没有对应 ToolMessage」的空洞，避免下次请求 400。"""
    answered: set[str] = set()
    for message in messages:
        if isinstance(message, ToolMessage) and message.tool_call_id:
            answered.add(message.tool_call_id)

    missing: list[ToolMessage] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for call in getattr(message, "tool_calls", None) or []:
            call_id = call.get("id")
            if not call_id or call_id in answered:
                continue
            missing.append(
                ToolMessage(
                    content="[工具调用未完成或已中断，已自动跳过]",
                    tool_call_id=call_id,
                    name=call.get("name") or "unknown_tool",
                )
            )
            answered.add(call_id)
    return missing


@before_model
def repair_orphaned_tool_calls(state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
    """每次进 model 前修复不完整的工具调用历史。"""
    missing = missing_tool_messages(list(state.get("messages") or []))
    if not missing:
        return None
    return {"messages": missing}


def create_note_agent():
    """创建笔记 Agent（透传工具 return_direct，写操作后再回 model）"""
    return create_agent(
        model=get_llm(purpose="agent"),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
        middleware=[repair_orphaned_tool_calls],
        name="note_assistant",
    )


def get_agent_config(session_id, thread_id=None) -> dict:
    # LangGraph checkpointer 要求 thread_id 放在 configurable 里
    return {
        "configurable": {
            "session_id": session_id,
            "thread_id": thread_id or DEFAULT_THREAD_ID,
        }
    }


def repair_thread_state(agent, config: dict) -> None:
    """流式请求开始前主动修补 checkpoint，避免脏历史进模型。"""
    try:
        snapshot = agent.get_state(config)
    except Exception:
        return
    values = getattr(snapshot, "values", None) or {}
    messages = list(values.get("messages") or [])
    missing = missing_tool_messages(messages)
    if not missing:
        return
    try:
        agent.update_state(config, {"messages": missing})
    except Exception:
        return
