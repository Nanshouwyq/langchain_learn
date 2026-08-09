from ai_chatbot.config import llm
from ai_chatbot.state import CustomerServiceState


def service_agent(state: CustomerServiceState) -> dict:
    question = state["user_question"]
    sensitive_words = ["退货", "换货", "退款", "维修", "赔偿", "投诉"]
    needs_review = any(word in question for word in sensitive_words)
    if needs_review:
        return {
            "needs_review": True,
            "message": [f"用户问题包含敏感词，需要人工审核: {question}"],
            "final_response": "需要人工审核",
            "review_result": "需要人工审核",
        }

    policy = "本产品支持7天无理由退货，15天换货，2年保修"
    prompt = f"""
     你是售后查询助手
     用户问题：{state['user_question']}
     售后政策：{policy}
     请根据产品信息礼貌，负责回答用户问题
    """
    response = llm().invoke(prompt)
    return {
        "needs_review": False,
        "service_result": response.content.strip(),
        "message": [f"售后{state['user_question']}的回答：{response.content.strip()}"],
        "final_response": response.content.strip(),
    }
