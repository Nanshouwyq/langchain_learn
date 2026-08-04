from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

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

db_path = Path(__file__).resolve().parent / "checkpoints.sqlite"
config1 = {"configurable": {"thread_id": "1234567890"}}

# SqliteSaver 需要独立包 langgraph-checkpoint-sqlite
with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
    app = graph.compile(checkpointer=checkpointer)

    result1 = app.invoke(
        {"messages": [HumanMessage(content="你好，我是小明，很高兴认识你。")]},
        config=config1,
    )
    print(result1["messages"][-1].content)

    result1 = app.invoke(
        {"messages": [HumanMessage(content="我是谁")]},
        config=config1,
    )
    print(result1["messages"][-1].content)
