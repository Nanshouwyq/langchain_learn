from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

from langchain_core.documents import Document

load_dotenv()
# 创建embedding模型（硅基流动等非 OpenAI 接口需关闭 check_embedding_ctx_length，
# 否则会按 tiktoken 发 token 数组，对方只接受文本，报 parameter invalid）
embedding = OpenAIEmbeddings(
    model=os.getenv("SILICONFLOW_MODEL", "BAAI/bge-large-zh-v1.5"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    check_embedding_ctx_length=False,
)
# 构建文档
doc = [
    Document(
        page_content="python 是一门高级、解释型、弱类型、跨平台通用编程语言，语法简洁易懂，被称为「最容易上手的编程语言」，应用覆盖几乎所有互联网、科技领域!",
        metadata={"category": "编程"},
    ),
    Document(page_content="java是一种高级语言!", metadata={"category": "编程"}),
    Document(
        page_content="javascript是一门轻量级、解释型、弱类型的编程语言，最初专为网页交互而生，现在已经是全场景通用语言!",
        metadata={"category": "编程"},
    ),
    Document(page_content="php是一种高级语言!", metadata={"category": "编程"}),
    Document(page_content="c++是一种高级语言!", metadata={"category": "编程"}),
    Document(page_content="c#是一种高级语言!", metadata={"category": "编程"}),
    Document(page_content="c语言是一种高级语言!", metadata={"category": "编程"}),
    Document(page_content="AI是一种人工智能语言!", metadata={"category": "人工智能"}),
]
# 创建向量数据库
vector_store = Chroma.from_documents(
    documents=doc,
    embedding=embedding,
    persist_directory="./chroma_db",
    collection_name="program",
)
print(vector_store._collection.count())
