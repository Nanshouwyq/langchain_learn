"""多专家客服：可复用业务层（支持 SSE 流式）。"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from langchain_core.messages import AIMessageChunk

from ai_chatbot.agents.route import VALID_TYPES, route_question
from ai_chatbot.config import llm
from ai_chatbot.state import CustomerServiceState

# session_id → 待人工审核的问题
_pending_reviews: dict[str, dict] = {}

_EXPERT_LABELS = {
    "order": "订单专家",
    "product": "产品专家",
    "service": "售后专家",
    "tech": "技术支持",
}


def init_state(user_question: str, user_id: str) -> CustomerServiceState:
    return {
        "user_id": user_id,
        "user_question": user_question,
        "query_type": "",
        "order_result": "",
        "product_result": "",
        "service_result": "",
        "tech_result": "",
        "message": [],
        "final_response": "",
        "needs_review": False,
        "review_result": "",
        "review_notes": "",
    }


def _chunk_text(chunk) -> str:
    content = getattr(chunk, "content", None)
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text") or "")
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)


def _needs_human_review(question: str) -> bool:
    sensitive = ("退货", "换货", "退款", "维修", "赔偿", "投诉")
    return any(word in question for word in sensitive)


def _build_expert_prompt(query_type: str, question: str, user_id: str) -> str:
    if query_type == "order":
        order_info = f"用户{user_id}_001 状态：已发货，预计明天送达"
        return (
            f"你是专业的订单客服。用户 {user_id} 问：{question}\n"
            f"订单信息：{order_info}\n"
            "请根据订单信息简洁礼貌地回答。"
        )
    if query_type == "product":
        return (
            f"你是产品咨询助手。用户问题：{question}\n"
            "产品信息：本产品支持快充，最大功率 65W，兼容多种设备。\n"
            "请根据产品信息简洁回答。"
        )
    if query_type == "service":
        return (
            f"你是售后助手。用户问题：{question}\n"
            "售后政策：支持 7 天无理由退货，15 天换货，2 年保修。\n"
            "请礼貌、负责地简洁回答。"
        )
    # tech
    return (
        f"你是技术支持助手。用户问题：{question}\n"
        "常见问题：设备无法开机 → 检查电源，长按电源键 10 秒重启。\n"
        "请礼貌、负责地简洁回答。"
    )


def _classify(question: str, user_id: str) -> str:
    state = init_state(question, user_id)
    result = route_question(state)
    qt = (result.get("query_type") or "product").strip().lower()
    return qt if qt in VALID_TYPES else "product"


def _stream_llm(prompt: str) -> Iterator[str]:
    for chunk in llm().stream(prompt):
        if isinstance(chunk, AIMessageChunk) or hasattr(chunk, "content"):
            text = _chunk_text(chunk)
            if text:
                yield text


def chat_stream(
    message: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> Iterator[dict]:
    """SSE 事件：session / status / token / review_required / done / error"""
    sid = session_id or str(uuid4())
    uid = user_id or sid
    yield {"type": "session", "session_id": sid}

    question = (message or "").strip()
    if not question:
        yield {"type": "error", "message": "消息不能为空"}
        return

    try:
        yield {"type": "status", "content": "正在识别问题类型…"}
        query_type = _classify(question, uid)
        label = _EXPERT_LABELS.get(query_type, query_type)
        yield {
            "type": "status",
            "content": f"已路由到「{label}」({query_type})",
            "query_type": query_type,
        }

        # 售后敏感词 → 人工审核（前端弹窗后调 /chat/review）
        if query_type == "service" and _needs_human_review(question):
            _pending_reviews[sid] = {
                "user_question": question,
                "user_id": uid,
                "query_type": query_type,
            }
            yield {
                "type": "review_required",
                "session_id": sid,
                "content": "该售后问题涉及敏感操作，需要人工审核后才能继续。",
            }
            yield {"type": "done"}
            return

        yield {"type": "status", "content": f"{label} 正在作答…"}
        prompt = _build_expert_prompt(query_type, question, uid)
        for text in _stream_llm(prompt):
            yield {"type": "token", "content": text}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


def resume_review_stream(
    session_id: str,
    result: str,
    notes: str = "",
) -> Iterator[dict]:
    """人工审核通过/拒绝后，流式返回最终答复。"""
    yield {"type": "session", "session_id": session_id}
    pending = _pending_reviews.pop(session_id, None)
    if not pending:
        yield {"type": "error", "message": "没有待审核的会话，或已过期"}
        return

    try:
        ok = result.strip() in {"通过", "pass", "approved", "同意"}
        yield {
            "type": "status",
            "content": f"人工审核结果：{'通过' if ok else '未通过'}",
        }
        if ok:
            prompt = (
                f"你是客服。用户申请已通过人工审核。\n"
                f"原问题：{pending['user_question']}\n"
                f"审核备注：{notes or '无'}\n"
                "请生成简短确认回复，告知工单号 12009，客服将在 24 小时内联系。"
            )
        else:
            prompt = (
                f"你是客服。用户申请未通过人工审核。\n"
                f"原问题：{pending['user_question']}\n"
                f"审核备注：{notes or '无'}\n"
                "请礼貌说明未通过，并建议重新申请或联系客服。"
            )
        for text in _stream_llm(prompt):
            yield {"type": "token", "content": text}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


def chat(message: str, session_id: str | None = None) -> dict:
    """非流式：聚合 stream 结果。"""
    sid = session_id or str(uuid4())
    reply = ""
    query_type = None
    review_required = False
    for event in chat_stream(message, session_id=sid):
        if event.get("type") == "session":
            sid = event["session_id"]
        elif event.get("type") == "token":
            reply += event.get("content") or ""
        elif event.get("type") == "status" and event.get("query_type"):
            query_type = event["query_type"]
        elif event.get("type") == "review_required":
            review_required = True
            reply = event.get("content") or reply
        elif event.get("type") == "error":
            raise RuntimeError(event.get("message") or "chat failed")
    return {
        "session_id": sid,
        "reply": reply or "暂时没有得到有效回复",
        "query_type": query_type,
        "review_required": review_required,
    }
