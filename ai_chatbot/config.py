from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL")
MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL")
MOONSHOT_TEMPERATURE = os.getenv("MOONSHOT_TEMPERATURE")
MOONSHOT_MAX_TOKENS = os.getenv("MOONSHOT_MAX_TOKENS")
MOONSHOT_TOP_P = os.getenv("MOONSHOT_TOP_P")
MOONSHOT_FREQUENCY_PENALTY = os.getenv("MOONSHOT_FREQUENCY_PENALTY")
MOONSHOT_PRESENCE_PENALTY = os.getenv("MOONSHOT_PRESENCE_PENALTY")

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL")

SILICONFLOW_PRESENCE_PENALTY = os.getenv("SILICONFLOW_PRESENCE_PENALTY")


LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

TEMPERATURE = 0.1
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETEIEVER_K = 3
# 查询改写会多一次 LLM 调用；关掉可明显加速日常问答
ENABLE_QUERY_REWRITE = False
VECTOR_STORE_COLLECTION_NAME = "ai_chatbot"
DEFAULT_THREAD_ID = "ai_chatbot"


def llm():
    # kimi-k2.6 只允许 temperature=1，不要改成 0.1 / 0.7 等
    return ChatOpenAI(
        model=MOONSHOT_MODEL,
        temperature=1,
        api_key=MOONSHOT_API_KEY,
        base_url=MOONSHOT_BASE_URL,
    )
