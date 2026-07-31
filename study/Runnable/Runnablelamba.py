from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

load_dotenv()


def text_langth_analysis(text) -> dict:
    return {
        "text": text,
        "length": len(text),
    }


# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)
text_langth_analysis_lambda = RunnableLambda(text_langth_analysis)
result = text_langth_analysis_lambda.invoke("Hello, world!")
print(result)


def add_time(data: dict) -> dict:
    return {
        "question": data["question"].strip(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def to_report(text: str) -> dict:
    return {
        "answer": text.strip(),
        "char_count": len(text),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


prompt = PromptTemplate.from_template("当前时间是{time}，请回答以下问题：{question}")
chain = (
    RunnableLambda(add_time)
    | prompt
    | llm
    | StrOutputParser()
    | RunnableLambda(to_report)
)
result = chain.invoke({"question": "什么是langchain"})
print(result)
