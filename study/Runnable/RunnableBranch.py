from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableBranch
from langchain_openai import ChatOpenAI

load_dotenv()


# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)
tech_chain = (
    ChatPromptTemplate.from_template(
        "作为技术专家，请用200字以内回答以下问题：{question}，并在回答开头第一句写上“技术专家"
    )
    | llm
    | StrOutputParser()
)
finance_chain = (
    ChatPromptTemplate.from_template(
        "作为金融专家，请用200字以内回答以下问题：{question}，并在回答开头第一句写上“金融专家"
    )
    | llm
    | StrOutputParser()
)
genera_chain = (
    ChatPromptTemplate.from_template(
        "作为通用专家，请用200字以内回答以下问题：{question}，并在回答开头第一句写上“通用专家"
    )
    | llm
    | StrOutputParser()
)


def is_tech_question(data: dict) -> bool:
    question = data["question"].lower()
    return any(
        word in question for word in ["技术", "编程", "开发", "算法", "数据"]
    )


def is_finance_question(data: dict) -> bool:
    question = data["question"].lower()
    return any(
        word in question for word in ["金融", "投资", "理财", "股票", "债券"]
    )


# RunnableBranch：前面是 (条件, 链)，最后一项必须是默认链（无条件元组）
branch_chain = RunnableBranch(
    (is_tech_question, tech_chain),
    (is_finance_question, finance_chain),
    genera_chain,  # 默认走通用专家
)
questions = ["python 编程是什么", "如何投资股票", "如何理财", "什么是区块链"]

for question in questions:
    result = branch_chain.invoke({"question": question})
    print(result)
