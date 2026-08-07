"""对外可复用的业务函数（API / 评测 / Gradio 都可调用）"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from note_assistant.agent import create_note_agent, get_agent_config
from note_assistant.chains import ask_notes, build_rag_chain

_agent = None

# 这些工具的返回值应按 system prompt「原样发给用户」，
# 若再拼一遍模型复述就会整段重复。
_PASSTHROUGH_TOOLS = frozenset({"answer_from_notes", "list_notes"})


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_note_agent()
    return _agent


def _last_ai_text(result: dict) -> str:
    messages = result.get("messages") or []
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            content = message.content
            if isinstance(content, list):
                parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                content = "".join(parts) or str(content)
            return str(content).strip()
    return ""


def _chunk_text(chunk) -> str:
    """从流式 chunk 中取出文本增量"""
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


def _emit_text(reply: str, text: str) -> tuple[str, str | None]:
    """合并增量文本；若是累计全文则只取新增部分。返回 (new_reply, emit_or_None)"""
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
    agent = get_agent()
    config = get_agent_config(sid, thread_id=sid)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    reply = _last_ai_text(result) or "暂时没有得到有效回复"
    return {"session_id": sid, "reply": reply}


def agent_chat_stream(message: str, session_id: str | None = None) -> Iterator[dict]:
    """
    Agent 流式对话。

    - answer_from_notes：透出工具内 RAG 的 token 流，并抑制模型复述
    - list_notes 等无内部 LLM：ToolMessage 一次性返回
    - 其它工具：流式输出模型最终回复
    """
    sid = session_id or str(uuid4())
    yield {"type": "session", "session_id": sid}

    agent = get_agent()
    config = get_agent_config(sid, thread_id=sid)
    reply = ""
    announced_tools: set[str] = set()
    # 已展示透传工具结果后，忽略模型复述
    suppress_ai = False
    # 正在等待透传工具（可能伴随嵌套 RAG 流式）
    pending_passthrough = False

    try:
        for chunk, metadata in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="messages",
        ):
            node = (metadata or {}).get("langgraph_node")

            # --- 工具返回 ---
            if isinstance(chunk, ToolMessage):
                name = getattr(chunk, "name", None) or ""
                text = _chunk_text(chunk).strip()
                if name in _PASSTHROUGH_TOOLS:
                    suppress_ai = True
                    pending_passthrough = False
                    announced_tools.clear()
                    # 若嵌套 RAG 已流式推过，不再整段重发；否则（如 list_notes）补发全文
                    if text and not reply.strip():
                        reply = text
                        yield {"type": "reset"}
                        yield {"type": "token", "content": text}
                    if not reply.strip():
                        reply = "暂时没有得到有效回复，请稍后再试。"
                        yield {"type": "token", "content": reply}
                    # 透传内容已就绪：立刻结束，不等 Agent 再复述一整遍
                    yield {"type": "done"}
                    return
                continue

            if not isinstance(chunk, (AIMessage, AIMessageChunk)):
                continue

            tool_calls = getattr(chunk, "tool_calls", None) or []
            tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
            if tool_calls or tool_call_chunks:
                suppress_ai = False
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

            if suppress_ai:
                continue

            if not isinstance(chunk, AIMessageChunk):
                continue

            text = _chunk_text(chunk)
            if not text:
                continue

            # model 节点：Agent 自己的回复
            # 非 model（tools 内嵌套 RAG 等）：透传工具的流式正文
            if node == "model":
                if pending_passthrough:
                    # 透传工具回合里不应再吃 model 的中间文本
                    continue
            elif node and node != "model":
                # 嵌套 LLM 流（answer_from_notes → RAG）
                if not pending_passthrough:
                    continue
            # node 为空时：偏保守，在 pending 时也放行（兼容不同版本 metadata）

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
