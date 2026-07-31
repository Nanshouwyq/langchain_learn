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
joke_chain = joke_prompt | llm | strOutputParser
poem_chain = poem_prompt | llm | strOutputParser

# 并行链：必须用「名字=链」的关键字参数，不能直接传位置参数
parallel_chain = RunnableParallel(joke=joke_chain, poem=poem_chain)


result = parallel_chain.invoke({"subject": "狗"})
print(result)
