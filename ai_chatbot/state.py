from typing import Annotated
import operator
from typing_extensions import TypedDict


# 定义客服系统在多个节点直接的流转状态
class CustomerServiceState(TypedDict):
    user_question: str
    user_id: str
    query_type: str

    # 提供不同的专家Agent的结果
    order_result: str
    payment_result: str
    service_result: str
    tech_result: str

    # 最终的响应接多
    final_response: str
    # 记录对话历史
    message: Annotated[list[str], operator.add]

    # 增加人工审核相关属性
    needs_review: bool
    review_result: str
    review_notes: str
