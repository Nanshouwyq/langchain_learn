# langchain-learn

LangChain 学习与实践仓库：包含 `study/` 示例代码，以及可运行的学习笔记智能助手（RAG + Agent + Gradio）。

## 项目结构

```
langchain-learn/
├── app.py                 # Gradio Web 入口
├── api/main.py            # FastAPI 骨架（/health /chat /rag）
├── web/                   # Vue3 前端（对接 note_assistant）
├── note_assistant/        # 笔记助手核心
│   ├── agent.py           # LangGraph Agent
│   ├── chains.py          # RAG 检索链 / 向量库
│   ├── service.py         # 供 API/评测复用的业务函数
│   ├── tools.py           # 笔记增删改查 & 问答工具
│   ├── eval/              # 评测迷你版（黄金集 + 脚本）
│   ├── models.py
│   └── config.py
├── notes/                 # Markdown 笔记（知识库源）
├── vectorstore/           # Chroma 本地向量库
└── study/                 # LangChain 学习示例
```

## 快速开始

```bash
# 安装依赖
uv sync
# 或
pip install -e .

# 配置环境变量（参考 .env.example）
cp .env.example .env

# 启动 Web 界面
source .venv/bin/activate
python app.py
```

浏览器打开：`http://127.0.0.1:7860`

## 评测迷你版

```bash
# 跑黄金集（默认 ask_notes / 纯 RAG）
python -m note_assistant.eval.run_eval

# 只跑前 2 条（冒烟）
python -m note_assistant.eval.run_eval --limit 2
```

- 用例：`note_assistant/eval/eval_cases.json`（可按回答风格改 `must_include`）
- 报告：`note_assistant/eval/last_report.json`
- 改 Prompt / TopK / 切分后重跑，对比 `pass_rate`

## FastAPI 骨架

```bash
uv sync   # 确保 fastapi / uvicorn 已安装
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- 文档：`http://127.0.0.1:8000/docs`
- `GET /health` 健康检查
- `POST /chat` Agent 对话（可调工具，带 `session_id`）
- `POST /rag` 纯 RAG 问答

示例：

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/rag -H 'Content-Type: application/json' \
  -d '{"question":"什么是RAG？"}'
curl -s http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"列出所有笔记"}'
```

## Vue 前端（web/）

```bash
# 需要 Node 18+（推荐 nvm use 20）
cd web
pnpm install
pnpm dev
```

打开 http://127.0.0.1:5173 ，开发代理会把 `/api` 转到后端 `:8000`。

## Docker 部署（最小骨架）

```bash
# 确保根目录有 .env（含 API Key），且不要把 .env 打进镜像
docker compose up --build api

# 同时启动 Gradio 网页
docker compose --profile web up --build
```

- API：http://127.0.0.1:8000/docs  
- Gradio：http://127.0.0.1:7860（需 `--profile web`）  
- `notes/`、`vectorstore/` 已挂载到宿主机，数据可持久化  

相关文件：`Dockerfile`、`docker-compose.yml`、`.dockerignore`

## 功能概览

- 笔记管理：创建 / 列表 / 更新 / 删除（`note_assistant/tools.py`）
- 基于笔记问答：Chroma 检索 + LLM 生成（`ask_notes`）
- Agent 编排：按用户意图调用工具（`note_assistant/agent.py`）
- Gradio 对话：流式输出、快捷问题、清空会话（`app.py`）

## RAG / Agent 问答加速实践

一次「基于笔记回答问题」往往偏慢，常见原因是链路过长：

1. Agent 先调一次模型决定用哪个工具  
2. `answer_from_notes` 内可能再做查询改写（又一次 LLM）+ 向量检索 + 生成答案  
3. Agent 再对工具结果二次总结  

相当于一次问答可能打 **3～4 次模型**。

已落地的加速手段：

| 改动 | 效果 |
|------|------|
| 默认关闭查询改写 `ENABLE_QUERY_REWRITE=False` | 少 1 次 LLM |
| 缓存 LLM / Embedding / RAG 链 | 避免每次重建连接 |
| 日常跳过重复打开向量库的空库检查 | 减少本地 IO |
| 提示 Agent：工具结果原样返回，不要二次扩写 | 减少末轮生成耗时 |

补充建议：

- 检索不准时，在 `note_assistant/config.py` 把 `ENABLE_QUERY_REWRITE` 改回 `True`
- 可换更快模型，或要求回答更短
- 更彻底：纯问答不走 Agent，直接调 `ask_notes`，可少一整轮工具决策
