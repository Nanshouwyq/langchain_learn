# RAG检索链构建
from http import client
from pathlib import Path
from pydoc import cli
import sys
import gc
import shutil
import time
from chromadb import Key
from chromadb.types import C
from config import (
    MOONSHOT_MODEL,
    MOONSHOT_API_KEY,
    MOONSHOT_BASE_URL,
    SILICONFLOW_MODEL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    NOTES_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTOR_STORE_COLLECTION_NAME,
    VECTOR_STORE_DIR,
    RETEIEVER_K,
    VECTOR_STORE_STATE_FILE,
    VECTORE_DB_FILE,
)


from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MOONSHOT_MODEL,
        api_key=MOONSHOT_API_KEY,
        base_url=MOONSHOT_BASE_URL,
        temperature=1,
    )


# 获取嵌入模型
def get_embedding_model() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=SILICONFLOW_MODEL,
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
        check_embedding_ctx_length=False,
    )


def load_note_documents() -> list[Document]:
    """加载 notes/ 下 Markdown（不依赖已停更的 langchain-community）"""
    notes_dir = Path(NOTES_DIR)
    documents: list[Document] = []
    for path in sorted(notes_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path),
                    "filename": path.name,
                },
            )
        )
    return documents


def split_documents(documents):
    """分割笔记文档"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", "", "，", "。", "？", "！"],
    )
    return text_splitter.split_documents(documents)


# 使用原始用户问题得到检索结果
def _build_retrieval_context(question: str, retriver) -> str:
    """构建检索上下文"""
    raw_documents = retriver.invoke(question)
    # 使用改写后的用户问题得到的检索结果
    rewritten_question = rewrite_query_for_retrieval(question)
    print(f"rewritten_question: {rewritten_question}")
    if rewritten_question == question:
        merge_documents = raw_documents
    else:
        rewritten_documents = retriver.invoke(rewritten_question)
        merge_documents = _merge_documents(raw_documents + rewritten_documents)
    return "\n\n".join(document.page_content for document in merge_documents)


def rewrite_query_for_retrieval(question: str) -> str:
    """改写用户问题"""
    prompt = ChatPromptTemplate.from_template(
        """
        你是一个学习助手，根据用户问题重写一个更适合检索的问题。
        要求：
        - 保留核心主题
        - 去掉口语词和无关废话
        - 不要扩写，不要回答
        - 不超过 20 个字

        用户问题: {question}
        改写后的问题:
        """
    )

    try:
        rewritten_question = (prompt | get_llm() | StrOutputParser()).invoke(
            {"question": question}
        )
    except Exception as e:
        print(f"改写用户问题失败: {e}")
        return question
    rewritten_question = rewritten_question.strip().strip('“”"‘')
    rewritten_question = " ".join(rewritten_question.split())
    return rewritten_question or question


def _merge_documents(documents) -> list:
    """合并文档"""
    merged_documents = []
    # 两次检索的结构会有重叠，这里安来源和正文去重
    seen = set()
    for document in documents:
        key = (document.metadata.get("source", ""), document.page_content)
        if key in seen:
            continue
        seen.add(key)
        merged_documents.append(document)
    return merged_documents


def clear_vector_store():
    """清空本地向量库"""
    vectorstore = None
    client = None
    try:
        vectorstore = Chroma(
            collection_name=VECTOR_STORE_COLLECTION_NAME,
            embedding_function=get_embedding_model(),
            persist_directory=str(VECTOR_STORE_DIR),
        )
        client = vectorstore._client
        vectorstore.delete_collection()
        client.clear_system_cache()
        client.close()
    except Exception:
        pass
    finally:
        del vectorstore
        del client
        # 做主动的垃圾回收
        gc.collect()
    # 最后把本地目录也清空，确保下一次重建拿到的是干净环境
    if VECTOR_STORE_DIR.exists():
        shutil.rmtree(VECTOR_STORE_DIR, ignore_errors=True)
    VECTOR_STORE_DIR.mkdir(exist_ok=True)


def _read_build_timestamp():
    # 读取build_txt 里面记录的上次成功建库时间戳（无文件则视为0）
    if not VECTOR_STORE_STATE_FILE.exists():
        return 0.0
    try:
        return float(VECTOR_STORE_STATE_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0.0


"""判断是否需要重建本地向量库"""


def _noted_changed() -> bool:
    note_paths = list(NOTES_DIR.rglob("*.md"))
    if not note_paths:
        return False
    # 比较文档的最后修改时间 和上次建库时间
    latest_note_mtime = max(
        [NOTES_DIR.stat().st_mtime] + [path.stat().st_mtime for path in note_paths]
    )
    # 如果最新文档修改时间大于上次建库时间，说明文档有更新
    return latest_note_mtime > _read_build_timestamp()


def vectorstore_need_rebuild() -> bool:
    note_paths = list(NOTES_DIR.rglob("*.md"))
    if not note_paths:
        return False
    # 没有sqlite 文件，说明本地向量库没有新建
    if not VECTORE_DB_FILE.exists():
        return True
    # 文档比建库时间更新，说明本地向量库还没建出来
    if _noted_changed():
        return True
    vectorstore = None
    clinet = None
    try:
        vectorstore = Chroma(
            collection_name=VECTOR_STORE_COLLECTION_NAME,
            embedding_function=get_embedding_model(),
            persist_directory=str(VECTOR_STORE_DIR),
        )
        client = vectorstore._client
        # 检查 collection 是否为空 ，防止向量库文件存在但collection 没有入库数据（如数据库贝手动删除或者损坏）导致检索失败

        return vectorstore._collection.count() == 0
    except Exception:
        return True
    finally:
        try:
            if client is not None:
                client.clear_system_cache()
                client.close()
        except Exception:
            pass
        del vectorstore
        del client
        gc.collect()


def create_vectorstore(documents) -> Chroma:
    """基于切分后的文档创建向量库"""
    return Chroma.from_documents(
        documents=documents,
        embedding=get_embedding_model(),
        collection_name=VECTOR_STORE_COLLECTION_NAME,
        persist_directory=str(VECTOR_STORE_DIR),
    )


def _write_build_timestamp():
    """写入建库时间戳"""
    VECTOR_STORE_STATE_FILE.write_text(str(time.time()), encoding="utf-8")


def rebuild_vectorstore():
    """重建本地向量库"""

    documents = load_note_documents()
    if not documents:
        clear_vector_store()
        return None
    chunks = split_documents(documents)
    clear_vector_store()
    vectorstore = create_vectorstore(chunks)
    _write_build_timestamp()
    return vectorstore


def build_rag_chain():
    """构建面向笔记问答的RAG链"""
    # 当没有笔记时，清空本地向量库并返回NONE
    if not list(NOTES_DIR.rglob("*.md")):
        clear_vector_store()
        return None
    # 日常问答只读取本地向量库：首次使用或者文档变更时，再统一全量重建一次
    if vectorstore_need_rebuild():
        rebuild_vectorstore()
    # 读取chroma db内容
    vectorstore = Chroma(
        collection_name=VECTOR_STORE_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=str(VECTOR_STORE_DIR),
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETEIEVER_K})
    prompt = ChatPromptTemplate.from_template(
        """
         你是一个学习助手，根据检索到的笔记回答问题:
        检索到的笔记内容：{context}
        问题: {question}
        请先判断哪些片段和问题最相关，忽略无关内容。
        如果检索内容里有相关问题的定义或者实例，请直接引用，不要用自己的话重复。
        如果笔记中没有相关信息，请明确告知用户
       
        """
    )
    # 返回构建的RAG链
    return (
        {
            # lambda 是「匿名函数」：写法为 lambda 参数: 表达式，相当于临时定义一个小函数。
            # 下面这行意思是：拿到 question 后，调用 _build_retrieval_context(question) 作为 context。
            # 其实也可以直接写成 "context": _build_retrieval_context,（效果相同）
            "context": lambda question: _build_retrieval_context(
                question, retriver=retriever
            ),
            "question": RunnablePassthrough(),
        }
        | prompt
        | get_llm()
        | StrOutputParser()
    )


def ask_notes(question: str) -> str:
    """基于笔记内容回答问题"""
    rag_chain = build_rag_chain()
    if rag_chain is None:
        return "当前没有可检索的笔记，请先创建或者准备一些笔记内容"
    return rag_chain.invoke(question)


if __name__ == "__main__":
    chain = ask_notes("我是一个新手，不知道langchain 请帮我介绍一下")
    print("---------chain---------")
    print(chain)
