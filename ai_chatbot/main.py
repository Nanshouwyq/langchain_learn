from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agents import (
    route_question,
    route_by_type,
    order_agent,
    product_agent,
    service_agent,
    tech_agent,
    human_review,
)
from state import CustomerServiceState
import pprint


def init_state(user_question: str, user_id: str) -> CustomerServiceState:
    return {
        "user_id": user_id,
        "user_question": user_question,
        "query_type": "",
        "order_result": "",
        "product_result": "",
        "service_result": "",
        "tech_result": "",
        "message": [],
        "final_response": "",
    }


def need_review(state: CustomerServiceState) -> Literal["review", "end"]:
    if state["needs_review"]:
        return "review"
    else:
        return "end"


# 多agent
def chatbot_graph() -> CustomerServiceState:
    """
    聊天机器人流程图
    """
    graph = StateGraph(CustomerServiceState)
    # 添加节点
    graph.add_node("route", route_question)
    graph.add_node("order", order_agent)
    graph.add_node("product", product_agent)
    graph.add_node("service", service_agent)
    graph.add_node("tech", tech_agent)
    graph.add_node("review", human_review)
    # 添加边
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        route_by_type,
        {
            "order": "order",
            "product": "product",
            "service": "service",
            "tech": "tech",
        },
    )
    graph.add_edge("order", END)
    graph.add_edge("product", END)
    graph.add_conditional_edges(
        "service",
        need_review,
        {
            "review": "review",
            "end": END,
        },
    )
    graph.add_edge("tech", END)
    graph.add_edge("review", END)
    app = graph.compile(checkpointer=MemorySaver(), interrupt_before=["review"])
    return app


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1234567890"}}
    app = chatbot_graph()
    state = init_state("我想退货", "1234567890")
    for chunk in app.stream(state, config=config, stream_mode="updates"):
        print(chunk)
    print("-" * 100)

    paused_state = app.get_state(config=config)
    print(paused_state.next)
    print(paused_state.values["final_response"])
    print("++++++++")
    result = app.invoke(None, config=config)
    print(result["final_response"])
    print(result["message"])
