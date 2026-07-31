from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

load_dotenv()

# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)

prompt = PromptTemplate.from_template("用一句话总结:{topic}")
summary_chain = (
    PromptTemplate.from_template("用一句话总结:{topic}") | llm | StrOutputParser()
)

sentiment_chain = (
    ChatPromptTemplate.from_template("分析情感:{topic}") | llm | StrOutputParser()
)
analysis_chain = (
    {"topic": RunnablePassthrough()}
    | RunnablePassthrough.assign(summay=sentiment_chain)
    | RunnablePassthrough.assign(sentiment=sentiment_chain)
)

result = analysis_chain.invoke("我困了")
print(result)
