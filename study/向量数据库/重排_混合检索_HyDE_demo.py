"""
重排 / 混合检索 / HyDE 简单 Demo（小白版）

怎么跑：
  cd langchain-learn
  source .venv/bin/activate
  python study/向量数据库/重排_混合检索_HyDE_demo.py

三种技术各解决什么问题：
  HyDE      → 问题和笔记措辞差很远时，先「编一段假答案」再去搜
  混合检索  → 语义像 + 关键词像，两路一起找，再合并
  重排      → 先多捞几条，再用更仔细的办法排出真正相关的
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MOONSHOT_MODEL", "kimi-k2.6"),
        api_key=os.getenv("MOONSHOT_API_KEY"),
        base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
        temperature=1,
    )


def get_embedding() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=os.getenv("SILICONFLOW_MODEL", "BAAI/bge-large-zh-v1.5"),
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        check_embedding_ctx_length=False,
    )


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# 故意准备一些「措辞不同 / 专有词」的文档，方便看出三种技术差异
DOCS = [
    Document(
        page_content="Chroma 是一个本地向量数据库，适合把笔记做成向量后做相似度搜索。",
        metadata={"id": "d1", "source": "chroma.md"},
    ),
    Document(
        page_content="BM25 是经典的关键词检索算法，靠词频和文档长度打分，专有名词命中很强。",
        metadata={"id": "d2", "source": "bm25.md"},
    ),
    Document(
        page_content="Python 是一门适合做 AI 和数据分析的编程语言，语法简洁。",
        metadata={"id": "d3", "source": "python.md"},
    ),
    Document(
        page_content="RAG 的流程是：切分文档 → 向量化 → 检索相关片段 → 交给大模型生成答案。",
        metadata={"id": "d4", "source": "rag.md"},
    ),
    Document(
        page_content="报错信息 ERR_VECTOR_TIMEOUT 通常表示向量服务响应超时，需要检查网络和超时配置。",
        metadata={"id": "d5", "source": "error.md"},
    ),
    Document(
        page_content="重排（Rerank）会先粗召回很多候选，再精排选出真正相关的几条。",
        metadata={"id": "d6", "source": "rerank.md"},
    ),
]


def build_stores(docs: list[Document]):
    """向量库 + BM25 关键词检索器"""
    vs = Chroma.from_documents(
        documents=docs,
        embedding=get_embedding(),
        collection_name="advanced_rag_demo",
    )
    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = 3
    return vs, bm25


def show_docs(title: str, docs: list[Document]) -> None:
    print(title)
    if not docs:
        print("  （空）")
        return
    for i, d in enumerate(docs, 1):
        print(f"  {i}. [{d.metadata.get('id')}] {d.page_content}")


# ------------------------------------------------------------
# 1) HyDE：先写「假答案」，再用假答案去检索
# ------------------------------------------------------------
def demo_hyde(vs: Chroma) -> None:
    section("1) HyDE（Hypothetical Document Embeddings）")
    print(
        """
【人话】
用户问得很口语/抽象时，直接拿问题去搜，可能对不上笔记原文。
HyDE 做法：
  ① 让 LLM 先「假装写一段可能的答案」
  ② 用这段假答案去向量库检索
因为假答案的措辞更像笔记正文，往往更好找。
"""
    )
    question = "本地怎么存笔记向量啊？"
    # 普通检索
    normal = vs.as_retriever(search_kwargs={"k": 2}).invoke(question)

    # HyDE：先生成假文档
    hyde_prompt = ChatPromptTemplate.from_template(
        """请根据问题写一段简短的「可能答案」（像百科解释，2-3 句）。
不要说你不知道，直接写内容。
问题：{question}
假答案："""
    )
    fake_doc = (hyde_prompt | get_llm() | StrOutputParser()).invoke(
        {"question": question}
    )
    hyde_hits = vs.as_retriever(search_kwargs={"k": 2}).invoke(fake_doc)

    print(f"问题: {question}")
    print(f"假答案: {fake_doc.strip()}")
    show_docs("\n直接用原问题检索:", normal)
    show_docs("\n用 HyDE 假答案检索:", hyde_hits)


# ------------------------------------------------------------
# 2) 混合检索：向量 + BM25，再用 RRF 合并
# ------------------------------------------------------------
def rrf_fuse(
    result_lists: list[list[Document]], k: int = 3, rrf_k: int = 60
) -> list[Document]:
    """
    Reciprocal Rank Fusion（倒数排名融合）
    某文档在各路结果里排名越靠前，加分越多。
    score = Σ 1 / (rrf_k + rank)
    """
    scores: dict[str, float] = defaultdict(float)
    doc_map: dict[str, Document] = {}
    for docs in result_lists:
        for rank, doc in enumerate(docs, start=1):
            doc_id = doc.metadata.get("id") or doc.page_content
            scores[doc_id] += 1.0 / (rrf_k + rank)
            doc_map[doc_id] = doc
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in ranked[:k]]


def demo_hybrid(vs: Chroma, bm25: BM25Retriever) -> list[Document]:
    section("2) 混合检索 Hybrid Search（向量 + 关键词）")
    print(
        """
【人话】
- 向量检索：懂「意思像不像」（Chroma 说本地存向量 ≈ 问「怎么存笔记向量」）
- BM25：懂「字面像不像」（专有词 ERR_VECTOR_TIMEOUT 这种特别强）
两边各找几条，用 RRF 合并排序 = 混合检索。
"""
    )
    # 这个问题里有强烈的「关键词」信号
    question = "出现 ERR_VECTOR_TIMEOUT 怎么办？"

    vector_docs = vs.as_retriever(search_kwargs={"k": 3}).invoke(question)
    bm25_docs = bm25.invoke(question)
    fused = rrf_fuse([vector_docs, bm25_docs], k=3)

    print(f"问题: {question}")
    show_docs("\n仅向量检索:", vector_docs)
    show_docs("\n仅 BM25 关键词:", bm25_docs)
    show_docs("\n混合检索（RRF 合并）:", fused)
    return fused


# ------------------------------------------------------------
# 3) 重排 Rerank：多捞一些，再精排
# ------------------------------------------------------------
def llm_rerank(question: str, docs: list[Document], top_n: int = 2) -> list[Document]:
    """
    教学用：让 LLM 当重排器（生产环境常用 CrossEncoder / 专用 Rerank API）。
    让模型返回文档 id 的排序，例如：d5,d2,d1
    """
    if not docs:
        return []

    numbered = "\n".join(
        f"- {d.metadata.get('id')}: {d.page_content}" for d in docs
    )
    prompt = ChatPromptTemplate.from_template(
        """你是检索结果重排器。根据问题和候选文档的相关性，从高到低排序。
只输出文档 id，用英文逗号分隔，不要解释。
例如：d5,d1,d2

问题：{question}

候选文档：
{numbered}

排序："""
    )
    raw = (prompt | get_llm() | StrOutputParser()).invoke(
        {"question": question, "numbered": numbered}
    )
    ids = re.findall(r"d\d+", raw.lower())
    doc_map = {d.metadata.get("id"): d for d in docs}
    ranked = [doc_map[i] for i in ids if i in doc_map]
    # 模型漏掉的，按原顺序补在后面
    for d in docs:
        if d not in ranked:
            ranked.append(d)
    return ranked[:top_n]


def demo_rerank(vs: Chroma) -> None:
    section("3) 重排 Rerank")
    print(
        """
【人话】
第一步粗召回：先找 4 条「可能相关」的（快但不准）
第二步精排：让重排器仔细比「谁更相关」，只留 Top2

本 demo 用 LLM 模拟重排；真实项目常用 bge-reranker 等模型。
"""
    )
    question = "向量库检索太慢超时了，错误码相关怎么处理？"
    # 粗召回多一点
    candidates = vs.as_retriever(search_kwargs={"k": 4}).invoke(question)
    reranked = llm_rerank(question, candidates, top_n=2)

    print(f"问题: {question}")
    show_docs("\n粗召回 k=4:", candidates)
    show_docs("\n重排后 Top2:", reranked)


def main() -> None:
    print("开始 Demo：HyDE / 混合检索 / 重排（需要可用 API Key）")
    vs, bm25 = build_stores(DOCS)
    demo_hyde(vs)
    demo_hybrid(vs, bm25)
    demo_rerank(vs)
    print(
        """
全部结束。

记忆口诀：
  HyDE     → 问题不像笔记时：先写假答案再搜
  混合检索 → 既要语义，也要关键词（报错码/专有名）
  重排     → 先多捞，再精挑
"""
    )


if __name__ == "__main__":
    main()
