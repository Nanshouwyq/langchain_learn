"""
RAG 增强技术入门 Demo（Agent 小白版）

怎么跑：
  cd langchain-learn
  source .venv/bin/activate
  python study/向量数据库/RAG增强技术入门.py

建议：先通读本文件注释，再整文件运行看输出。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 加载项目根目录 .env
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


# ---------- 准备一小份「假笔记」 ----------
RAW_NOTES = [
    Document(
        page_content=(
            "LangChain 是构建 LLM 应用的框架。"
            "它把 Prompt、模型、检索、工具串成链路。"
            "RAG 就是先检索再生成。"
        ),
        metadata={"source": "langchain.md", "tag": "框架"},
    ),
    Document(
        page_content=(
            "Chroma 是常用的本地向量数据库。"
            "可以把文本变成向量后做相似度搜索。"
            "适合学习笔记这种小规模知识库。"
        ),
        metadata={"source": "chroma.md", "tag": "向量库"},
    ),
    Document(
        page_content=(
            "Python 语法简洁，常用于 AI 和数据分析。"
            "列表、字典、函数是入门必会内容。"
        ),
        metadata={"source": "python.md", "tag": "语言"},
    ),
]


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# 1) 切分增强：Chunk + Overlap
# ============================================================
def demo_chunk_overlap() -> list[Document]:
    section("1) 切分增强：Chunk + Overlap（块重叠）")
    print(
        """
【人话】
长文章不能整篇塞进模型，要切成小块。
overlap = 相邻两块重叠一部分，避免一句话被从中间砍断。

【例子】
原文：ABCDEFGHIJ
chunk=4, overlap=1 时，可能切成：
  ABCD
   DEFG   ← 和上一块重叠了 D
    GHIJ
"""
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=40,
        chunk_overlap=10,
        separators=["。", "，", "\n", " ", ""],
    )
    chunks = splitter.split_documents(RAW_NOTES)
    print(f"原始文档 {len(RAW_NOTES)} 篇 → 切成 {len(chunks)} 块")
    for i, c in enumerate(chunks[:3], 1):
        print(f"  块{i}: {c.page_content[:50]}... | meta={c.metadata}")
    return chunks


# ============================================================
# 2) Top-K 检索
# ============================================================
def build_vectorstore(chunks: list[Document]) -> Chroma:
    return Chroma.from_documents(
        documents=chunks,
        embedding=get_embedding(),
        collection_name="rag_enhance_demo",
    )


def demo_topk(vs: Chroma) -> None:
    section("2) Top-K 检索（取最像的前 K 条）")
    print(
        """
【人话】
向量库里有很多笔记块。问一个问题时，按「语义像不像」排序，
只取前 K 条给模型看。K 越大信息越多，但也越吵、越慢。

【例子】
k=1 → 只给最像的 1 段
k=3 → 给最像的 3 段（note_assistant 默认就是 3）
"""
    )
    question = "什么是向量数据库？"
    for k in (1, 2):
        docs = vs.as_retriever(search_kwargs={"k": k}).invoke(question)
        print(f"\n问题: {question} | k={k} → 取回 {len(docs)} 条")
        for d in docs:
            print(f"  - ({d.metadata.get('source')}) {d.page_content[:40]}...")


# ============================================================
# 3) 查询改写 Query Rewrite
# ============================================================
def demo_query_rewrite() -> str:
    section("3) 查询改写 Query Rewrite")
    print(
        """
【人话】
用户说话很口语：「那个 chroma 啥玩意儿来着帮我讲讲」
检索更喜欢干净短句：「Chroma 向量数据库是什么」
所以先让 LLM 把问题改写成「更适合检索」的版本。

【注意】
会多一次 LLM 调用，更慢。note_assistant 里默认关闭：
ENABLE_QUERY_REWRITE = False
"""
    )
    raw = "那个 chroma 啥玩意儿来着帮我讲讲呗"
    prompt = ChatPromptTemplate.from_template(
        """把用户问题改写成更适合检索的短句。
要求：保留主题，去掉口语，不超过 15 字，不要回答问题。
用户问题：{question}
改写："""
    )
    rewritten = (prompt | get_llm() | StrOutputParser()).invoke({"question": raw})
    rewritten = rewritten.strip().strip('"“”')
    print(f"原问题: {raw}")
    print(f"改写后: {rewritten}")
    return rewritten


# ============================================================
# 4) 多路检索 + 合并去重
# ============================================================
def demo_multi_retrieve_merge(vs: Chroma, rewritten: str) -> None:
    section("4) 多路检索 + 合并去重")
    print(
        """
【人话】
用「原问题」搜一次，再用「改写后的问题」搜一次，
两拨结果合起来，重复的去掉。召回面更宽。

【像】
左口袋掏出几张纸条 + 右口袋掏出几张 → 摊桌上去掉重复的。
"""
    )
    raw = "那个 chroma 啥玩意儿来着帮我讲讲呗"
    retriever = vs.as_retriever(search_kwargs={"k": 2})
    docs_a = retriever.invoke(raw)
    docs_b = retriever.invoke(rewritten)

    def merge(docs: list[Document]) -> list[Document]:
        seen, out = set(), []
        for d in docs:
            key = (d.metadata.get("source", ""), d.page_content)
            if key in seen:
                continue
            seen.add(key)
            out.append(d)
        return out

    merged = merge(docs_a + docs_b)
    print(f"原问检索: {len(docs_a)} 条 | 改写检索: {len(docs_b)} 条 | 合并去重后: {len(merged)} 条")
    for d in merged:
        print(f"  - {d.metadata.get('source')}: {d.page_content[:36]}...")


# ============================================================
# 5) Grounded Prompt（生成时「踩着笔记回答」）
# ============================================================
def demo_grounded_prompt(vs: Chroma) -> None:
    section("5) Grounded Prompt（约束模型别瞎编）")
    print(
        """
【人话】
检索到的内容叫 context。Prompt 要明确告诉模型：
- 只根据笔记答
- 无关的忽略
- 没有就说没有

这就是「接地气回答」，减少幻觉。
"""
    )
    question = "Chroma 适合做什么？"
    docs = vs.as_retriever(search_kwargs={"k": 2}).invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = ChatPromptTemplate.from_template(
        """你是学习助手。只能根据【笔记】回答。
若笔记没有相关信息，请明确说「笔记中没有」。
不要编造。

【笔记】
{context}

【问题】
{question}

【回答】"""
    )
    answer = (prompt | get_llm() | StrOutputParser()).invoke(
        {"context": context, "question": question}
    )
    print(f"问题: {question}")
    print(f"回答: {answer}")


# ============================================================
# 6) Agentic RAG（Agent 决定要不要检索）
# ============================================================
def demo_agentic_rag_idea() -> None:
    section("6) Agentic RAG（Agent + 检索工具）")
    print(
        """
【人话】
普通 RAG：每次提问都检索。
Agentic RAG：先让 Agent 判断「这个问题要不要查笔记」。
  - 「列出所有笔记」→ 调 list_notes，不走向量检索
  - 「什么是 RAG」→ 调 answer_from_notes（内部才是 RAG）
  - 「今天星期几」→ 可能根本不查笔记

【极简伪代码】
@tool
def answer_from_notes(question: str) -> str:
    return rag_chain.invoke(question)   # 真正的 RAG

agent = create_agent(model=llm, tools=[answer_from_notes, list_notes, ...])
agent.invoke("什么是 Chroma？")
# Agent 自己选择：调用 answer_from_notes → 拿到笔记答案 → 回复你

【你项目里】
note_assistant/tools.py 的 answer_from_notes
note_assistant/agent.py 的 create_note_agent
就是这种模式。
"""
    )


# ============================================================
# 7) 还没用、但常听到的增强（只需建立印象）
# ============================================================
def demo_advanced_names() -> None:
    section("7) 进阶名词速览（note_assistant 暂未实现）")
    print(
        """
1) Hybrid Search 混合检索
   向量检索（语义） + 关键词检索（BM25）一起用，再合并。
   适合：专有名词、报错码这类「必须字面命中」的问题。

2) Rerank 重排
   先粗召回 20 条，再用更强模型精排，只留最好的 3 条。
   适合：召回多、噪声大。

3) HyDE
   先让 LLM「假装写一篇答案」，再用这篇假答案去检索。
   适合：问题和笔记措辞差很远。

4) Contextual Compression 上下文压缩
   检索回来的段落太长，先压成和问题相关的句子再给模型。

记住口诀：
  改写/多路 → 找得更全
  重排/压缩 → 给得更准
  Agent     → 用得更聪明
"""
    )


def main() -> None:
    print("RAG 增强技术入门 Demo 开始…（需要可用的 API Key）")
    chunks = demo_chunk_overlap()
    vs = build_vectorstore(chunks)
    demo_topk(vs)
    rewritten = demo_query_rewrite()
    demo_multi_retrieve_merge(vs, rewritten)
    demo_grounded_prompt(vs)
    demo_agentic_rag_idea()
    demo_advanced_names()
    print("\n全部演示结束。对照 note_assistant/chains.py 会更容易看懂。")


if __name__ == "__main__":
    main()
