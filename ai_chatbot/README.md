# AI Chatbot（多专家客服 · 流式）

路由到订单 / 产品 / 售后 / 技术专家，后端 SSE 流式输出，前端逐字展示。

## 启动

```bash
# 终端 1：后端（项目根目录）
uvicorn ai_chatbot.api:app --reload --host 127.0.0.1 --port 8001

# 终端 2：前端
cd ai_chatbot/web
pnpm install   # 或 npm install
pnpm dev       # http://127.0.0.1:5174
```

确保根目录 `.env` 已配置 `MOONSHOT_*`（建议 `MOONSHOT_THINKING=disabled`）。

## 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/chat` | 一次性返回 |
| POST | `/chat/stream` | SSE：`session` / `status` / `token` / `review_required` / `done` / `error` |
| POST | `/chat/review` | 人工审核后继续流式回复 |

流式示例：

```bash
curl -N http://127.0.0.1:8001/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"这个充电器支持多少瓦快充？"}'
```

含「退货」等敏感词的售后问题会触发 `review_required`，前端弹窗审核后调用 `/chat/review`。

## 目录

```
ai_chatbot/
  api.py           # FastAPI
  service.py       # 路由 + LLM 流式
  agents/          # 专家节点（LangGraph CLI 仍可用）
  main.py          # python -m ai_chatbot.main
  web/             # Vue3 流式前端
```
