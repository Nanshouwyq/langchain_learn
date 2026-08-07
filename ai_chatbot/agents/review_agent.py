from pathlib import Path
import sys

# Code Runner 直接运行本文件时，把 ai_chatbot/ 加入模块搜索路径
_AI_CHATBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_CHATBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_CHATBOT_ROOT))

from state import CustomerServiceState


def human_review(state: CustomerServiceState) -> CustomerServiceState:
    """
    人工审核（需要在真实终端里运行，才能使用 input()）
    """
    print(f"需要人工审核: {state['user_question']}")

    result = input("请输入审核结果（通过/拒绝）: ").strip()
    notes = input("请输入审核备注: ").strip()

    if result == "通过":
        response = f"""
        您的申请已通过审核，工单号为12009，
        备注: {notes}
        客服将在24小时内联系你
        """
    else:
        response = f"""
        您的申请未通过审核，请重新申请，
        备注: {notes}
        如有疑问，请联系客服
        """
    return {
        "review_result": result,
        "review_notes": notes,
        "final_response": response,
        "message": [
            f"售后Agent：检测到敏感操作，人工审核结果: {result}",
            f"人工审核备注: {notes}",
        ],
    }


if __name__ == "__main__":
    demo_state = {
        "user_question": "我想退货",
        "service_result": "",
    }
    print(human_review(demo_state))
