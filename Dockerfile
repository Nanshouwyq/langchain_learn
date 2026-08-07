# 最小可运行镜像：默认启动 FastAPI
# 构建: docker compose build
# 启动: docker compose up

FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # 容器内默认对外监听
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    GRADIO_INBROWSER=0

# 先装依赖（利用层缓存）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 再拷贝业务代码
COPY note_assistant ./note_assistant
COPY api ./api
COPY app.py ./
COPY notes ./notes
COPY vectorstore ./vectorstore

EXPOSE 8000 7860

# 默认跑 API；compose 里可覆盖为 Gradio
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
