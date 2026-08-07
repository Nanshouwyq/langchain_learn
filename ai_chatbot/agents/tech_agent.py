from config import llm
from state import CustomerServiceState


def tech_agent(state: CustomerServiceState) -> CustomerServiceState:
    """
    技术相关问题的处理
    """
    tech_info = "常见问题：设备无法开机-》检查电源，长按电源键10秒重启"

    prompt = f"""
     你是技术查询助手
     用户问题：{state['user_question']}
     文档：{tech_info}
     请根据技术信息礼貌，负责回答用户问题
    """
    response = llm().invoke(prompt)

    return {
        "tech_result": response.content.strip(),
        "message": [
            f"技术支持{state['user_question']}的回答：{response.content.strip()}"
        ],
        "final_response": response.content.strip(),
    }
