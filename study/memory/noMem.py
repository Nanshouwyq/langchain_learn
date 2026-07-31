from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI

load_dotenv()

joke_prompt = PromptTemplate.from_template("请讲一个关于{subject}的冷笑话")
poem_prompt = PromptTemplate.from_template("请创作一首关于{subject}的诗")

strOutputParser = StrOutputParser()


# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)
