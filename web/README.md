# 学习笔记助手 · 前端

pnpm + Vue 3 + TypeScript + Pinia + Ant Design Vue + Tailwind CSS

## 启动

```bash
# 终端 1：后端
cd ..
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2：前端（需要 Node 18+，推荐 nvm use 20）
cd web
pnpm install
pnpm dev
```

打开：http://127.0.0.1:5173

## 能力

- **Agent 模式**：`POST /api/chat` → 可管理笔记
- **RAG 模式**：`POST /api/rag` → 仅笔记问答
- 快捷问题、会话 `session_id`、API 健康检查
- Vite 代理：`/api/*` → `http://127.0.0.1:8000/*`
