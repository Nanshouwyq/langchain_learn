"""多专家客服 LangGraph CLI Demo。

用法（项目根目录）：
  python -m ai_chatbot.main
"""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ai_chatbot.agents import (
    human_review,
    order_agent,
    product_agent,
    route_by_type,
    route_question,
    service_agent,
    tech_agent,
)
from ai_chatbot.service import init_state
from ai_chatbot.state import CustomerServiceState


def need_review(state: CustomerServiceState) -> Literal["review", "end"]:
    if state.get("needs_review"):
        return "review"
    return "end"


def chatbot_graph():
    graph = StateGraph(CustomerServiceState)
    graph.add_node("route", route_question)
    graph.add_node("order", order_agent)
    graph.add_node("product", product_agent)
    graph.add_node("service", service_agent)
    graph.add_node("tech", tech_agent)
    graph.add_node("review", human_review)
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
        {"review": "review", "end": END},
    )
    graph.add_edge("tech", END)
    graph.add_edge("review", END)
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["review"])


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "demo-thread"}}
    app = chatbot_graph()
    state = init_state("这个充电器支持多少瓦快充？", "u001")
    for chunk in app.stream(state, config=config, stream_mode="updates"):
        print(chunk)
    print("-" * 40)
    print(app.get_state(config).values.get("final_response"))
