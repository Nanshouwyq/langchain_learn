from ai_chatbot.config import llm
from ai_chatbot.state import CustomerServiceState


def order_agent(state: CustomerServiceState) -> dict:
    order_info = f"用户{state['user_id']}_001 状态：已发货，预计明天送达"
    prompt = f"""
    你是一个专业的订单客服，用户{state['user_id']}咨询订单{state['user_question']}，
    以下是订单信息：{order_info}
    请根据订单信息回答用户问题
    """
    response = llm().invoke(prompt)
    return {
        "order_result": response.content.strip(),
        "message": [f"订单{state['user_question']}的回答：{response.content.strip()}"],
        "final_response": response.content.strip(),
    }
