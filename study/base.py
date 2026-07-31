from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

load_dotenv()


# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个AI助手"),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}"),
    ]
)
