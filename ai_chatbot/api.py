"""多专家客服 FastAPI（SSE 流式）

用法（项目根目录）：
  uvicorn ai_chatbot.api:app --reload --host 127.0.0.1 --port 8001

接口：
  GET  /health
  POST /chat              一次性返回
  POST /chat/stream       SSE 流式
  POST /chat/review       人工审核后继续（SSE）
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_chatbot.service import chat, chat_stream, resume_review_stream

app = FastAPI(title="AI Chatbot Customer Service API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    user_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    query_type: str | None = None
    review_required: bool = False


class ReviewRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    result: str = Field(..., description="通过 / 拒绝")
    notes: str = ""


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_response(events: Iterator[dict]) -> StreamingResponse:
    def generate():
        try:
            for event in events:
                yield _sse(event)
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai_chatbot"}


@app.post("/chat", response_model=ChatResponse)
def chat_api(body: ChatRequest):
    result = chat(body.message, session_id=body.session_id)
    return ChatResponse(**result)


@app.post("/chat/stream")
def chat_stream_api(body: ChatRequest):
    return _sse_response(
        chat_stream(
            body.message,
            session_id=body.session_id,
            user_id=body.user_id,
        )
    )


@app.post("/chat/review")
def chat_review_api(body: ReviewRequest):
    return _sse_response(
        resume_review_stream(
            session_id=body.session_id,
            result=body.result,
            notes=body.notes,
        )
    )
