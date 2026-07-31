from email import message
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

message_history = InMemoryChatMessageHistory()
strOutputParser = StrOutputParser()


print("查看聊天历史")
message = message_history.messages
for m in message:
    print(m.type, m.content)
print("查看聊天历史结束")


# ChatOpenAI 兼容 OpenAI 协议；这里接 Moonshot（Kimi）

llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,  # Moonshot kimi-k2.6 仅允许 temperature=1
)
# 用字典记录不同用户的history
store = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个AI助手"),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}"),
    ]
)

baseChain = prompt | llm | strOutputParser

with_history = RunnableWithMessageHistory(
    baseChain,
    get_session_history,  # 函数名
    input_messages_key="input",
    history_messages_key="history",
)
print("===带记忆的对话展示")
config = {"configurable": {"session_id": "1234567890"}}
result = with_history.invoke({"input": "我叫张山"}, config)
print(result)
result = with_history.invoke({"input": "我叫什么名字"}, config)
print(result)
print("===查看会话历史")
history = get_session_history("1234567890").messages
for m in history:
    print(m.type, m.content)
print("===查看会话历史结束")
