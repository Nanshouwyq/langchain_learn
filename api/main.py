"""笔记助手 FastAPI 骨架

用法（项目根目录）：
  uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

接口：
  GET  /health
  POST /chat          Agent 对话（可调工具，一次性返回）
  POST /chat/stream   Agent 对话（SSE 流式）
  POST /rag           纯 RAG 问答（一次性返回）
  POST /rag/stream    纯 RAG 问答（SSE 流式）
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from note_assistant.service import (
    agent_chat,
    agent_chat_stream,
    rag_answer,
    rag_answer_stream,
)

app = FastAPI(title="Note Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入")
    session_id: str | None = Field(None, description="会话 ID，不传则新建")


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class RagRequest(BaseModel):
    question: str = Field(..., min_length=1)


class RagResponse(BaseModel):
    answer: str


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
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = agent_chat(req.message, session_id=req.session_id)
    return ChatResponse(**result)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    return _sse_response(agent_chat_stream(req.message, session_id=req.session_id))


@app.post("/rag", response_model=RagResponse)
def rag(req: RagRequest):
    return RagResponse(answer=rag_answer(req.question))


@app.post("/rag/stream")
def rag_stream(req: RagRequest):
    return _sse_response(rag_answer_stream(req.question))
