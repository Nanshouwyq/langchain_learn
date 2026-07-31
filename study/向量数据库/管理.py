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
print("============")
query = "什么是人工智能"
results = vector_store.similarity_search(query, k=2)
print(results)
print("============")
query = "什么是人工智能"
results = vector_store.similarity_search(query, k=2, filter={"category": "编程"})
print(results)
