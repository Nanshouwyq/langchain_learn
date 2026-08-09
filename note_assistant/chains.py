# RAG检索链构建
from pathlib import Path
import sys
import gc
import shutil
import time

from .config import (
    MOONSHOT_MODEL,
    MOONSHOT_API_KEY,
    MOONSHOT_BASE_URL,
    MOONSHOT_THINKING,
    AGENT_MAX_TOKENS,
    RAG_MAX_TOKENS,
    CONTEXT_MAX_CHARS,
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
    ENABLE_QUERY_REWRITE,
)


from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

_llm_by_purpose: dict[str, ChatOpenAI] = {}
_embedding_model = None
_rag_chain = None
_rag_chain_stream = None
_vectorstore_checked_ok = False


def get_llm(*, purpose: str = "default") -> ChatOpenAI:
    """获取对话模型（按用途缓存）。

    purpose:
      - agent：工具决策，短输出（AGENT_MAX_TOKENS）
      - rag / default：笔记问答（RAG_MAX_TOKENS）

    kimi-k2.6：thinking 与 temperature/top_p 必须对齐，否则易 20015。
    """
    key = purpose if purpose in {"agent", "rag"} else "rag"
    cached = _llm_by_purpose.get(key)
    if cached is not None:
        return cached

    thinking_on = MOONSHOT_THINKING in {"1", "true", "enabled", "on"}
    thinking_type = "enabled" if thinking_on else "disabled"
    max_tokens = AGENT_MAX_TOKENS if key == "agent" else RAG_MAX_TOKENS
    llm = ChatOpenAI(
        model=MOONSHOT_MODEL,
        api_key=MOONSHOT_API_KEY,
        base_url=MOONSHOT_BASE_URL,
        temperature=1.0 if thinking_on else 0.6,
        top_p=0.95,
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": thinking_type}},
    )
    _llm_by_purpose[key] = llm
    return llm


def reset_llm_clients() -> None:
    """热重载时清空模型与 RAG 缓存。"""
    global _llm_by_purpose, _rag_chain, _rag_chain_stream
    _llm_by_purpose = {}
    _rag_chain = None
    _rag_chain_stream = None


# 获取嵌入模型
def get_embedding_model() -> OpenAIEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = OpenAIEmbeddings(
            model=SILICONFLOW_MODEL,
            api_key=SILICONFLOW_API_KEY,
            base_url=SILICONFLOW_BASE_URL,
            check_embedding_ctx_length=False,
            # SiliconFlow 对超长/过大 batch 会返回 20015，控制每批条数
            chunk_size=16,
        )
    return _embedding_model


def _invalidate_rag_cache():
    """笔记变更 / 重建向量库后清空缓存"""
    global _rag_chain, _rag_chain_stream, _vectorstore_checked_ok
    _rag_chain = None
    _rag_chain_stream = None
    _vectorstore_checked_ok = False


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
    """构建检索上下文；同笔记多段命中时尽量拼全，减少「只出前半篇」。"""
    raw_documents = retriver.invoke(question)
    if not ENABLE_QUERY_REWRITE:
        docs = raw_documents
    else:
        # 使用改写后的用户问题得到的检索结果（多一次 LLM，默认关闭以加速）
        rewritten_question = rewrite_query_for_retrieval(question)
        print(f"rewritten_question: {rewritten_question}")
        if rewritten_question == question:
            docs = raw_documents
        else:
            rewritten_documents = retriver.invoke(rewritten_question)
            docs = _merge_documents(raw_documents + rewritten_documents)

    # 按来源聚合：同一笔记的多个 chunk 按出现顺序拼在一起，便于覆盖全文结构
    by_source: dict[str, list] = {}
    order: list[str] = []
    for document in docs:
        src = document.metadata.get("source") or document.metadata.get("filename") or ""
        if src not in by_source:
            by_source[src] = []
            order.append(src)
        by_source[src].append(document.page_content)

    blocks = []
    used = 0
    for src in order:
        name = Path(src).name if src else "note"
        body = "\n\n".join(by_source[src])
        block = f"### 来源: {name}\n{body}"
        # 控制上下文长度：过长会显著拉高 RAG 生成耗时
        if used and used + len(block) + 2 > CONTEXT_MAX_CHARS:
            break
        if len(block) > CONTEXT_MAX_CHARS - used:
            block = block[: max(0, CONTEXT_MAX_CHARS - used)].rstrip() + "\n…(已截断)"
        blocks.append(block)
        used += len(block) + 2
    return "\n\n".join(blocks)


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
        rewritten_question = (
            prompt | get_llm(purpose="agent") | StrOutputParser()
        ).invoke({"question": question})
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
    _invalidate_rag_cache()
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
    global _vectorstore_checked_ok
    note_paths = list(NOTES_DIR.rglob("*.md"))
    if not note_paths:
        return False
    # 没有sqlite 文件，说明本地向量库没有新建
    if not VECTORE_DB_FILE.exists():
        _vectorstore_checked_ok = False
        return True
    # 文档比建库时间更新，说明本地向量库还没建出来
    if _noted_changed():
        _vectorstore_checked_ok = False
        return True
    # 日常问答：文件与时间戳都正常时跳过打开 Chroma 的空库检查
    if _vectorstore_checked_ok:
        return False

    vectorstore = None
    client = None
    try:
        vectorstore = Chroma(
            collection_name=VECTOR_STORE_COLLECTION_NAME,
            embedding_function=get_embedding_model(),
            persist_directory=str(VECTOR_STORE_DIR),
        )
        client = vectorstore._client
        # 检查 collection 是否为空 ，防止向量库文件存在但collection 没有入库数据（如数据库贝手动删除或者损坏）导致检索失败
        empty = vectorstore._collection.count() == 0
        _vectorstore_checked_ok = not empty
        return empty
    except Exception:
        _vectorstore_checked_ok = False
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
    _invalidate_rag_cache()
    return vectorstore


def build_rag_chain(*, streaming: bool = False):
    """构建面向笔记问答的RAG链（带缓存，避免每次问答都重新连库）

    streaming=False：工具 / invoke 用，避免嵌套流式 token 泄漏进 Agent 流
    streaming=True：/rag/stream 用，真正逐 token 输出
    """
    global _rag_chain, _rag_chain_stream
    # 当没有笔记时，清空本地向量库并返回NONE
    if not list(NOTES_DIR.rglob("*.md")):
        clear_vector_store()
        return None
    # 日常问答只读取本地向量库：首次使用或者文档变更时，再统一全量重建一次
    if vectorstore_need_rebuild():
        rebuild_vectorstore()

    cached = _rag_chain_stream if streaming else _rag_chain
    if cached is not None:
        return cached

    # 读取chroma db内容
    vectorstore = Chroma(
        collection_name=VECTOR_STORE_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=str(VECTOR_STORE_DIR),
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETEIEVER_K})
    prompt = ChatPromptTemplate.from_template(
        """你是学习助手，只依据检索笔记回答。

笔记：
{context}

问题：{question}

要求：
1. 直答要点，控制在约 300～500 字；需要时用短列表。
2. 关键定义/代码可简短引用，不要大段原文粘贴，不要铺开无关小节。
3. 笔记没有相关信息时明确说没有，不要编造。
"""
    )
    chain = (
        {
            "context": lambda question: _build_retrieval_context(
                question, retriver=retriever
            ),
            "question": RunnablePassthrough(),
        }
        | prompt
        | get_llm(purpose="rag")
        | StrOutputParser()
    )
    if streaming:
        _rag_chain_stream = chain
    else:
        _rag_chain = chain
    return chain


def ask_notes(question: str) -> str:
    """基于笔记回答。

    使用 stream 聚合：在 Agent 的 messages 流里可透出 token（改善首字等待），
    同时仍返回完整字符串给 ToolMessage。
    """
    rag_chain = build_rag_chain(streaming=True)
    if rag_chain is None:
        return "当前没有可检索的笔记，请先创建或者准备一些笔记内容"
    parts: list[str] = []
    for text in rag_chain.stream(question):
        if text:
            parts.append(text)
    joined = "".join(parts).strip()
    return joined if joined else "暂时没有得到有效回复"


# if __name__ == "__main__":
#     chain = ask_notes("我是一个新手，不知道langchain 请帮我介绍一下")
#     print("---------chain---------")
#     print(chain)
