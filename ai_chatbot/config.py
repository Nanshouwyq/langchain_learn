from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL")
MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL")
MOONSHOT_THINKING = (os.getenv("MOONSHOT_THINKING") or "disabled").strip().lower()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL")

LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

DEFAULT_THREAD_ID = "ai_chatbot"

_llm = None


def llm() -> ChatOpenAI:
    """客服对话模型（单例）。kimi-k2.6：thinking 关 + 对齐 temperature。"""
    global _llm
    if _llm is None:
        thinking_on = MOONSHOT_THINKING in {"1", "true", "enabled", "on"}
        _llm = ChatOpenAI(
            model=MOONSHOT_MODEL,
            api_key=MOONSHOT_API_KEY,
            base_url=MOONSHOT_BASE_URL,
            temperature=1.0 if thinking_on else 0.6,
            top_p=0.95,
            max_tokens=1024,
            extra_body={
                "thinking": {"type": "enabled" if thinking_on else "disabled"}
            },
        )
    return _llm
