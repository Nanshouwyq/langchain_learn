"""构建gradio 界面-web入口"""

from functools import partial
from uuid import uuid4

import gradio as gr
from langchain_core.messages import AIMessage

from note_assistant.agent import create_note_agent, get_agent_config

agent = create_note_agent()


def _extract_reply(result) -> str:
    """从 agent 返回的 messages 中取出最后一条助手回复"""
    messages = result.get("messages") or []
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            content = message.content
            if isinstance(content, list):
                texts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                content = "".join(texts) or str(content)
            return str(content).strip()
    return "暂时没有得到有效回复，请稍后再试。"


def chat(message: str, history: list, session_id: str):
    """发送一条用户消息并更新对话历史"""
    message = (message or "").strip()
    if not message:
        return history, ""

    history = list(history or [])
    history.append({"role": "user", "content": message})

    try:
        config = get_agent_config(session_id, thread_id=session_id)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        reply = _extract_reply(result)
    except Exception as e:
        reply = f"处理失败: {e}"

    history.append({"role": "assistant", "content": reply})
    return history, ""


def clear_chat():
    """清空对话，并换新 session，避免记忆串线"""
    return [], "", str(uuid4())


def quick_chat(prompt: str, history: list, session_id: str):
    """快捷问题：直接把预设文案当作用户输入发送"""
    return chat(prompt, history, session_id)


def create_interface():
    """创建gradio 界面"""
    with gr.Blocks(title="学习笔记智能助手") as demo:
        session_state = gr.State(value=str(uuid4()))
        gr.Markdown(
            """
            # 学习笔记智能助手
            基于 LangChain 和 Gradio 创建，既能管理笔记，也能基于笔记内容进行问答。
            """
        )
        chatbot = gr.Chatbot(label="对话区", height=520)
        with gr.Row(equal_height=True):
            msg = gr.Textbox(
                placeholder="输入问题，例如：列出所有笔记 / 什么是 RAG",
                scale=8,
                lines=1,
                max_lines=1,
                show_label=False,
                container=False,
            )
            send_button = gr.Button(
                "发送",
                variant="primary",
                scale=1,
                min_width=88,
            )
        with gr.Row():
            clear_button = gr.Button("清空对话")
            gr.Markdown("**快捷问题**")
        with gr.Row():
            quick_btn1 = gr.Button("列出所有笔记", size="sm")
            quick_btn2 = gr.Button("python 基础讲了什么", size="sm")
            quick_btn3 = gr.Button("帮我创建一篇机器学习笔记", size="sm")
            quick_btn4 = gr.Button("什么是RAG", size="sm")

        # 发送：按钮 / 回车
        send_button.click(
            fn=chat,
            inputs=[msg, chatbot, session_state],
            outputs=[chatbot, msg],
        )
        msg.submit(
            fn=chat,
            inputs=[msg, chatbot, session_state],
            outputs=[chatbot, msg],
        )

        # 清空对话
        clear_button.click(
            fn=clear_chat,
            inputs=None,
            outputs=[chatbot, msg, session_state],
        )

        # 快捷问题
        quick_btn1.click(
            fn=partial(quick_chat, "列出所有笔记"),
            inputs=[chatbot, session_state],
            outputs=[chatbot, msg],
        )
        quick_btn2.click(
            fn=partial(quick_chat, "python 基础讲了什么"),
            inputs=[chatbot, session_state],
            outputs=[chatbot, msg],
        )
        quick_btn3.click(
            fn=partial(quick_chat, "帮我创建一篇机器学习笔记"),
            inputs=[chatbot, session_state],
            outputs=[chatbot, msg],
        )
        quick_btn4.click(
            fn=partial(quick_chat, "什么是RAG"),
            inputs=[chatbot, session_state],
            outputs=[chatbot, msg],
        )

    return demo


if __name__ == "__main__":
    create_interface().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(),
    )
