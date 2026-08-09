from ai_chatbot.state import CustomerServiceState


def human_review(state: CustomerServiceState) -> dict:
    """CLI 用人工审核（input）。API 流式请走 service.resume_review_stream。"""
    print(f"需要人工审核: {state['user_question']}")
    result = input("请输入审核结果（通过/拒绝）: ").strip()
    notes = input("请输入审核备注: ").strip()

    if result == "通过":
        response = (
            f"您的申请已通过审核，工单号为12009，备注: {notes}，客服将在24小时内联系你"
        )
    else:
        response = (
            f"您的申请未通过审核，请重新申请，备注: {notes}，如有疑问，请联系客服"
        )
    return {
        "review_result": result,
        "review_notes": notes,
        "final_response": response,
        "message": [
            f"售后Agent：检测到敏感操作，人工审核结果: {result}",
            f"人工审核备注: {notes}",
        ],
    }
