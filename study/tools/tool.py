import os
from dotenv import load_dotenv
from langchain_core.tools import tool
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
llm_with_tools = llm.bind_tools(tools)
query = "3*12等于多少"
messages = [HumanMessage(content=query)]
# 1先让AI 看问题，决定要不要调用工具
ai_message = llm_with_tools.invoke(messages)
messages.append(ai_message)

# 第二步 根据toolcall是哪个工具调用的，调用工具并获取结果
for tool_call in ai_message.tool_calls:
    if tool_call.get("name") == "add":
        result = add.invoke(tool_call.get("args"))
    elif tool_call.get("name") == "multiply":
        result = multiply.invoke(tool_call.get("args"))
    print(f"工具{tool_call.get('name')}调用结果: {result}")
# 第三步 将工具调用结果添加到会话历史
messages.append(ToolMessage(content=result, tool_call_id=tool_call.get("id")))
# 第四步 再次调用LLM，使用新的会话历史
final_message = llm_with_tools.invoke(messages)
print("===查看AI回答")
print(final_message.content)
print("===查看AI回答结束")
