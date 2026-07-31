"""构建Agent"""

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from chains import get_llm
from tools import ALL_TOOLS
from config import DEFAULT_THREAD_ID

SYSTEM_PROMPT = """
你是一个学习笔记助手，根据检索到的笔记内容回答问题。
你的职责：
 1.帮助用户操作笔记（增删改查）
 2.如果笔记中没有相关信息，请明确告知用户
 3.用户询问某个知识点，请先使用answer_from_notes工具检索笔记内容，如果笔记中没有相关信息，请明确告知用户
工作规则：
 1.不要凭空编造笔记
 2.如果用户询问某个知识点，请先使用answer_from_notes工具检索笔记内容，如果笔记中没有相关信息，请明确告知用户
 3.只有用户明确要求更改笔记时才调用相应工具
 4.用户询问有没有某类笔记时优先调用list_notes工具
 5.所有的回答要求简洁，自然，直接。
"""


def create_note_agent():
    """创建笔记Agent"""
    return create_agent(
        model=get_llm(),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
        name="note_assistant",
    )


def get_agent_config(session_id, thread_id=None) -> dict:
    # LangGraph checkpointer 要求 thread_id 放在 configurable 里
    return {
        "configurable": {
            "session_id": session_id,
            "thread_id": thread_id or DEFAULT_THREAD_ID,
        }
    }


if __name__ == "__main__":
    config = get_agent_config("123", "456")
    print(config)
    agent = create_note_agent()

    def ask(text: str):
        return agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config=config,
        )

    print(ask("创建一个笔记，标题为：笔记助手，内容为：笔记助手是一个帮助用户管理笔记的工具"))
    print(ask("列出所有笔记"))
    print(ask("更新笔记助手，内容为：笔记助手是一个帮助用户管理笔记的工具"))
    print(ask("删除笔记助手"))
    print(ask("回答问题：笔记助手是什么？"))
    print(ask("回答问题：笔记助手有什么功能？"))
    print(ask("回答问题：笔记助手怎么使用？"))
    print(ask("回答问题：笔记助手怎么使用？"))
