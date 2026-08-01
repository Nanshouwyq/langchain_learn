"""构建gradio 界面-web入口"""

from functools import partial
from uuid import uuid4

import gradio as gr
from langchain_core.messages import AIMessage, AIMessageChunk

from note_assistant.agent import create_note_agent, get_agent_config

agent = create_note_agent()


def _chunk_text(chunk) -> str:
    """从流式 chunk 中取出文本增量"""
    content = getattr(chunk, "content", None)
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)


def chat(message: str, history: list, session_id: str):
    """发送一条用户消息，并以流式方式更新助手回复"""
    message = (message or "").strip()
    if not message:
        yield history, ""
        return

    history = list(history or [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "思考中..."})
    yield history, ""

    reply = ""
    # 工具调用后开启新一轮模型输出时，清空缓冲，只展示最终回答
    reset_after_tools = False
    try:
        config = get_agent_config(session_id, thread_id=session_id)
        for chunk, _metadata in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="messages",
        ):
            if not isinstance(chunk, (AIMessage, AIMessageChunk)):
                continue
            if getattr(chunk, "tool_call_chunks", None) or getattr(
                chunk, "tool_calls", None
            ):
                reset_after_tools = True
                continue
            text = _chunk_text(chunk)
            if not text:
                continue
            if reset_after_tools:
                reply = ""
                reset_after_tools = False
            reply += text
            history[-1] = {"role": "assistant", "content": reply}
            yield history, ""

        if not reply:
            history[-1] = {
                "role": "assistant",
                "content": "暂时没有得到有效回复，请稍后再试。",
            }
            yield history, ""
    except Exception as e:
        history[-1] = {"role": "assistant", "content": f"处理失败: {e}"}
        yield history, ""


def clear_chat():
    """清空对话，并换新 session，避免记忆串线"""
    return [], "", str(uuid4())


def quick_chat(prompt: str, history: list, session_id: str):
    """快捷问题：直接把预设文案当作用户输入发送"""
    yield from chat(prompt, history, session_id)


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
