from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

from langchain_core.documents import Document

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
# 新建
ids = vector_store.add_documents(
    documents=[
        Document(page_content="py是一种高级语言!", metadata={"category": "编程"})
    ],
)
print(ids)
# 更新
update = vector_store.update_document(
    document=Document(
        page_content="python是一种高级语言!", metadata={"category": "编程"}
    ),
    document_id=ids[0],
)
print(update)
# 删除
delete = vector_store.delete(ids=ids)
print(delete)
