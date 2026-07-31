import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, ToolMessage

load_dotenv()


@tool
def add(a: int, b: int) -> int:
    """加法

    Args:
        a: 第一个加数
        b: 第二个加数

    Returns:
        两数之和
    """
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """乘法

    Args:
        a: 第一个乘数
        b: 第二个乘数

    Returns:
        两数之积
    """
    return a * b


tools = [add, multiply]
llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)
agent = create_agent(model=llm, tools=tools)

query = "先算 25乘以4，再算4乘以8，最后两个结果相加"
result = agent.invoke({"messages": [HumanMessage(content=query)]})
print(result["messages"][-1].content)
print("===查看AI回答结束")
