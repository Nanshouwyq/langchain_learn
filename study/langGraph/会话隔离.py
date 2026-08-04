from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    model="kimi-k2.6",
    api_key="sk-oTFSw8B01qqN57DM6nDQtIOlajzkhwpIpcLQQP8FP7xbOFQr",
    base_url="https://api.moonshot.cn/v1",
    temperature=1,
)


def chatbot_node(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot_node)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)
app = graph.compile(checkpointer=MemorySaver())
config1 = {"configurable": {"thread_id": "1234567890"}}
config2 = {"configurable": {"thread_id": "1234567891"}}
result1 = app.invoke(
    {"messages": [HumanMessage(content="你好，我是小明，很高兴认识你。")]},
    config=config1,
)
result2 = app.invoke(
    {"messages": [HumanMessage(content="你好，我是小hong，很高兴认识你。")]},
    config=config2,
)
print(result1["messages"][-1].content)
print(result2["messages"][-1].content)

result1 = app.invoke(
    {"messages": [HumanMessage(content="我是谁")]},
    config=config1,
)
result2 = app.invoke(
    {"messages": [HumanMessage(content="我是谁")]},
    config=config2,
)
print(result1["messages"][-1].content)
print(result2["messages"][-1].content)
