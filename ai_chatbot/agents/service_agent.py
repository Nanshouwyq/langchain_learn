from pathlib import Path
import sys

# Code Runner 直接运行本文件时，把 ai_chatbot/ 加入模块搜索路径
_AI_CHATBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_CHATBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_CHATBOT_ROOT))

from config import llm
from state import CustomerServiceState


def service_agent(state: CustomerServiceState) -> CustomerServiceState:
    """
    售后相关问题的处理
    """
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


if __name__ == "__main__":
    state = {
        "user_question": "我想退货",
    }
    result = service_agent(state)
    print(result)
