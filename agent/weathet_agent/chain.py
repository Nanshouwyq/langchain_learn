from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

try:
    from weathet_agent.config import (
        MOONSHOT_API_KEY,
        MOONSHOT_BASE_URL,
        MOONSHOT_MODEL,
    )
except ImportError:
    from config import (
        MOONSHOT_API_KEY,
        MOONSHOT_BASE_URL,
        MOONSHOT_MODEL,
    )

if not MOONSHOT_MODEL:
    raise ValueError(
        "未读到 MOONSHOT_MODEL，请确认项目根目录 .env 已配置，"
        f"且 config.PROJECT_ROOT 指向正确位置"
    )

llm = ChatOpenAI(
    model=MOONSHOT_MODEL,
    api_key=MOONSHOT_API_KEY,
    base_url=MOONSHOT_BASE_URL,
    temperature=1,
)


@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    weather_data = {
        "北京": "晴天 气温10-20度",
        "上海": "多云 气温20-26度",
        "广州": "小雨 气温10-20度",
        "深圳": "晴天 气温10-20度",
        "成都": "阴天 气温10-20度",
        "重庆": "多云 气温10-20度",
        "天津": "晴天 气温10-20度",
        "南京": "多云 气温10-20度",
        "杭州": "晴天 气温10-20度",
        "武汉": "多云 气温10-20度",
        "长沙": "晴天 气温10-20度",
        "西安": "多云 气温10-20度",
        "郑州": "晴天 气温10-20度",
        "青岛": "多云 气温10-20度",
        "烟台": "晴天 气温10-20度",
        "威海": "多云 气温10-20度",
        "日照": "晴天 气温10-20度",
        "临沂": "多云 气温10-20度",
    }
    return f"The weather in {city} is {weather_data[city]}."


llm_with_tools = llm.bind_tools([get_weather])


# llm 负责决策
def llm_node(state: MessagesState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# 条件路由负责判断下一步是进工具节点还是直接结束
def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# 工具节点负责调用工具
tool_node = ToolNode(tools=[get_weather])

# reAct
graph = StateGraph(MessagesState)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)


graph.add_edge(START, "llm")
graph.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)
graph.add_edge("tools", "llm")
app = graph.compile()

result = app.invoke(
    {"messages": [HumanMessage(content="今天北京shanghai天气怎么样？")]}
)
print(result["messages"][-1].content)
