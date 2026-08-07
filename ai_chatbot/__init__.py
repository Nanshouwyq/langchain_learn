"""
ai_chatbot
多智能体客服助手
基于 LangGraph 构建的客服工作流，整合核心能力：
- 问题路由与多专家 Agent（订单 / 产品 / 售后 / 技术）
- 人工审核中断（Human-in-the-loop）
- 对话状态与记忆（Checkpoint）
- 多节点状态流转与最终回复汇总
"""

__version__ = "0.1.0"
