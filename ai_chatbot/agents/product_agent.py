from ai_chatbot.config import llm
from ai_chatbot.state import CustomerServiceState


def product_agent(state: CustomerServiceState) -> dict:
    product_info = "本产品支持快充，最大功率 65w，兼容多种设备"
    prompt = f"""
     你是产品查询助手
     用户问题：{state['user_question']}
     产品信息：{product_info}
     请根据产品信息回答用户问题
    """
    response = llm().invoke(prompt)
    return {
        "product_result": response.content.strip(),
        "message": [f"产品{state['user_question']}的回答：{response.content.strip()}"],
        "final_response": response.content.strip(),
    }
