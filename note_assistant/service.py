"""对外可复用的业务函数（API / 评测 / Gradio 都可调用）"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from note_assistant.agent import (
    create_note_agent,
    get_agent_config,
    repair_thread_state,
)
from note_assistant.chains import ask_notes, build_rag_chain, reset_llm_clients
from note_assistant.config import ENABLE_RAG_SHORTCUT

_agent = None
# 热重载：清掉旧 LLM / agent，避免沿用 thinking 或采样参数
reset_llm_clients()
_agent = None


# return_direct=True 的工具：执行后图直接 END，结果原样给用户
_PASSTHROUGH_TOOLS = frozenset({"answer_from_notes", "list_notes"})

# 这些意图才走 Agent；其余知识问答短路直连 RAG（跳过首轮 model）
_AGENT_INTENT_KEYWORDS = (
    "创建笔记",
    "新建笔记",
    "写一篇笔记",
    "删除笔记",
    "删掉笔记",
    "更新笔记",
    "修改笔记",
    "列出笔记",
    "列出所有",
    "有哪些笔记",
    "所有笔记",
    "笔记列表",
    "按标签",
)


def _needs_agent_tools(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    return any(k in text for k in _AGENT_INTENT_KEYWORDS)


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_note_agent()
    return _agent


def _chunk_text(chunk) -> str:
    """从消息 / chunk 中取出文本"""
    content = getattr(chunk, "content", None)
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)


def _last_reply_text(result: dict) -> str:
    """
    取最终回复：
    - 透传工具：最后一条匹配的 ToolMessage
    - 其它：最后一条有正文的 AIMessage
    """
    messages = result.get("messages") or []
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            name = getattr(message, "name", None) or ""
            if name in _PASSTHROUGH_TOOLS:
                text = _chunk_text(message).strip()
                if text:
                    return text
        if isinstance(message, AIMessage) and message.content:
            if getattr(message, "tool_calls", None):
                continue
            text = _chunk_text(message).strip()
            if text:
                return text
    return ""


def _emit_text(reply: str, text: str) -> tuple[str, str | None]:
    """合并增量文本；若是累计全文则只取新增部分。"""
    if not text:
        return reply, None
    if reply and text.startswith(reply):
        text = text[len(reply) :]
        if not text:
            return reply, None
    elif reply and reply.startswith(text) and text != reply:
        return reply, None
    return reply + text, text


def rag_answer(question: str) -> str:
    """纯 RAG 问答（评测默认走这条，更快）"""
    return ask_notes(question)


def rag_answer_stream(question: str) -> Iterator[dict]:
    """纯 RAG 流式问答。yield: {type: token|done|error, ...}"""
    rag_chain = build_rag_chain(streaming=True)
    if rag_chain is None:
        yield {
            "type": "token",
            "content": "当前没有可检索的笔记，请先创建或者准备一些笔记内容",
        }
        yield {"type": "done"}
        return

    try:
        for text in rag_chain.stream(question):
            if text:
                yield {"type": "token", "content": text}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


def agent_chat(message: str, session_id: str | None = None) -> dict:
    """
    Agent 对话（可调工具）。
    返回: {session_id, reply}
    """
    sid = session_id or str(uuid4())
    # 知识问答短路：跳过首轮 model + tool 调度
    if ENABLE_RAG_SHORTCUT and not _needs_agent_tools(message):
        return {"session_id": sid, "reply": ask_notes(message)}

    agent = get_agent()
    config = get_agent_config(sid, thread_id=sid)
    repair_thread_state(agent, config)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    reply = _last_reply_text(result) or "暂时没有得到有效回复"
    return {"session_id": sid, "reply": reply}


def agent_chat_stream(
    message: str, session_id: str | None = None
) -> Iterator[dict]:
    """
    Agent 流式对话（与图结构对齐）：

    - 普通知识问答（默认）：短路直连 RAG 流，跳过首轮 model
    - answer_from_notes：透出工具内 RAG token；工具 return_direct → 图 END
    - list_notes：ToolMessage 一次返回；return_direct → 图 END
    - 写操作工具：再回 model，流式输出短确认
    """
    sid = session_id or str(uuid4())
    yield {"type": "session", "session_id": sid}

    if ENABLE_RAG_SHORTCUT and not _needs_agent_tools(message):
        yield {"type": "status", "content": "正在检索笔记…"}
        try:
            for event in rag_answer_stream(message):
                yield event
        except Exception as e:
            yield {"type": "error", "message": str(e)}
        return

    agent = get_agent()
    config = get_agent_config(sid, thread_id=sid)
    repair_thread_state(agent, config)
    reply = ""
    announced_tools: set[str] = set()
    # 正在执行透传工具（允许嵌套 RAG 的非 model 节点 token）
    pending_passthrough = False

    try:
        for chunk, metadata in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="messages",
        ):
            node = (metadata or {}).get("langgraph_node")

            if isinstance(chunk, ToolMessage):
                name = getattr(chunk, "name", None) or ""
                text = _chunk_text(chunk).strip()
                if name in _PASSTHROUGH_TOOLS:
                    pending_passthrough = False
                    announced_tools.clear()
                    # RAG 已流式推过则不再整段重发；list_notes 等在此补发
                    if text and not reply.strip():
                        reply = text
                        yield {"type": "reset"}
                        yield {"type": "token", "content": text}
                continue

            if not isinstance(chunk, (AIMessage, AIMessageChunk)):
                continue

            tool_calls = getattr(chunk, "tool_calls", None) or []
            tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
            if tool_calls or tool_call_chunks:
                names: list[str] = []
                for tc in list(tool_calls) + list(tool_call_chunks):
                    name = (
                        tc.get("name")
                        if isinstance(tc, dict)
                        else getattr(tc, "name", None)
                    )
                    if name:
                        names.append(str(name))
                if any(n in _PASSTHROUGH_TOOLS for n in names):
                    pending_passthrough = True
                    reply = ""
                    yield {"type": "reset"}
                for name in names:
                    if name not in announced_tools:
                        announced_tools.add(name)
                        yield {
                            "type": "status",
                            "content": f"正在调用工具：{name}…",
                        }
                continue

            if not isinstance(chunk, AIMessageChunk):
                continue

            text = _chunk_text(chunk)
            if not text:
                continue

            # model：普通回复 / 写操作后的确认
            # 非 model：透传工具内嵌套 RAG 流
            if node == "model":
                if pending_passthrough:
                    continue
            elif node and node != "model":
                if not pending_passthrough:
                    continue

            reply, emit = _emit_text(reply, text)
            if emit:
                yield {"type": "token", "content": emit}

        if not reply:
            yield {
                "type": "token",
                "content": "暂时没有得到有效回复，请稍后再试。",
            }
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}
