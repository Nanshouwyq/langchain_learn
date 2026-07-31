from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

from langchain_core.documents import Document

from langchain_core.runnables import RunnablePassthrough

load_dotenv()
embedding = OpenAIEmbeddings(
    model=os.getenv("SILICONFLOW_MODEL", "BAAI/bge-large-zh-v1.5"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    check_embedding_ctx_length=False,
)
vector_store = Chroma(
    embedding_function=embedding,
    persist_directory="./chroma_db",
    collection_name="program",
)
# 构建检索器
retriever = vector_store.as_retriever(search_kwargs={"k": 2})


# 格式化文档
def format_docs(docs) -> str:
    return "\n\n".join([doc.page_content for doc in docs])


# 构建提示词
prompt = ChatPromptTemplate.from_template(
    """
        你是一个AI助手，请根据以下文档回答问题：
        {context}
        问题：{question}
        回答：
   """
)
# 构建LLM（对话用 Moonshot；embedding 专用参数不要传给 ChatOpenAI）
llm = ChatOpenAI(
    model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
    temperature=1,
)
# 构建RAG链
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
# 执行RAG链
result = rag_chain.invoke("python和javascript 的区别 ")
print(result)
