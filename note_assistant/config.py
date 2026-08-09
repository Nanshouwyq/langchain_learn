from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

NOTES_DIR = PROJECT_ROOT / "notes"
VECTOR_STORE_DIR = PROJECT_ROOT / "vectorstore"
VECTORE_DB_FILE = VECTOR_STORE_DIR / "chroma.sqlite3"
VECTOR_STORE_STATE_FILE = VECTOR_STORE_DIR / "build_state.txt"

# 自动创建
for dir in (NOTES_DIR, VECTOR_STORE_DIR):
    dir.mkdir(exist_ok=True)


MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL")
MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL")
MOONSHOT_TEMPERATURE = os.getenv("MOONSHOT_TEMPERATURE")
MOONSHOT_MAX_TOKENS = os.getenv("MOONSHOT_MAX_TOKENS")
MOONSHOT_TOP_P = os.getenv("MOONSHOT_TOP_P")
MOONSHOT_FREQUENCY_PENALTY = os.getenv("MOONSHOT_FREQUENCY_PENALTY")
MOONSHOT_PRESENCE_PENALTY = os.getenv("MOONSHOT_PRESENCE_PENALTY")
# kimi-k2.6 默认 thinking 开，首轮 tool 决策常 8～15s；disabled 可明显加速
# 取值：disabled | enabled（对应 extra_body.thinking.type）
MOONSHOT_THINKING = (os.getenv("MOONSHOT_THINKING") or "disabled").strip().lower()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL")

SILICONFLOW_PRESENCE_PENALTY = os.getenv("SILICONFLOW_PRESENCE_PENALTY")


LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

TEMPERATURE = 0.1
# BGE 约 512 token 上限（中文约 500 字）；超长会触发 SiliconFlow 20015
CHUNK_SIZE = 450
CHUNK_OVERLAP = 80
# 检索块数：过大 → 上下文长 → RAG 生成极慢（trace 里可达 30～90s）
RETEIEVER_K = 4
# 拼进 prompt 的上下文上限（字符），超出截断
CONTEXT_MAX_CHARS = int(os.getenv("CONTEXT_MAX_CHARS") or "2200")
# 限制生成长度，避免「完整覆盖」式长答拖垮延迟
AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS") or "512")
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS") or "1024")
# 查询改写会多一次 LLM 调用；关掉可明显加速日常问答
ENABLE_QUERY_REWRITE = False
# Agent 模式里，知识问答可短路直连 RAG，跳过首轮 model（省 3～10s）
ENABLE_RAG_SHORTCUT = (os.getenv("ENABLE_RAG_SHORTCUT") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
VECTOR_STORE_COLLECTION_NAME = "note_assistant"
DEFAULT_THREAD_ID = "note_assistant"
