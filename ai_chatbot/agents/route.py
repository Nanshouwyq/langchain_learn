from typing import Literal

from ai_chatbot.config import llm
from ai_chatbot.state import CustomerServiceState

VALID_TYPES = ("order", "product", "service", "tech")


def route_question(state: CustomerServiceState) -> dict:
    """路由节点：判断用户问题类型。"""
    prompt = f"""
    你是一个客服专家，根据用户的问题，判断用户的问题是那一类问题。
    用户的问题是：{state['user_question']}

    类型选项：
    -order:订单查询,物流追踪
    -product:产品咨询,功能介绍，产品参数
    -service:售后服务，退换货，保修政策，维修申请
    -tech:技术支持，故障排查，使用问题

    请返回类型选项中的一个,只返回类型名称,不要返回其他内容。
    """
    text = llm().invoke(prompt).content.strip().lower()
    result = "product"
    for item in VALID_TYPES:
        if item in text:
            result = item
            break

    return {"query_type": result, "message": [f"用户问题被路由到{result}专家"]}


def route_by_type(
    state: CustomerServiceState,
) -> Literal["order", "product", "service", "tech"]:
    return state["query_type"]  # type: ignore[return-value]
