# LlamaIndex 入门指南

**标签**: LlamaIndex, LLM, RAG

LlamaIndex（曾用名 GPT Index）是面向 **数据增强 LLM 应用** 的框架，擅长把私有文档、数据库、API 接到大模型上，做问答、检索与 Agent。本文按「概念—组件—模式—对比—落地」整理，便于笔记检索与复习。

---

## 一、它是什么、解决什么问题

| 概念 | 英文 | 说明 |
|------|------|------|
| LlamaIndex | LlamaIndex | 以「索引 + 检索 + 查询」为核心的 LLM 数据框架 |
| 数据增强 | Data-Augmented LLM | 让模型基于外部知识回答，而不仅靠参数记忆 |
| RAG | Retrieval-Augmented Generation | 先检索相关片段，再生成答案 |
| Query Engine | Query Engine | 接收自然语言问题，返回回答（可带引用来源） |
| Chat Engine | Chat Engine | 带多轮对话状态的问答引擎 |
| Workflow | Workflow | 用事件驱动编排多步骤 Agent / 复杂流程 |

**典型要解决的问题：**

1. 把 PDF、Markdown、网页、数据库等接入 LLM  
2. 构建高质量 RAG（切分、索引、检索、重排、生成）  
3. 多文档问答、摘要、结构化抽取  
4. 检索器组合（混合检索、路由、子问题分解）  
5. 文档 Agent：对知识库提问并调用工具  

---

## 二、核心组件一览

| 组件 | 英文 | 作用 |
|------|------|------|
| 文档 | Document | 原始知识单元（文本 + 元数据） |
| 节点 | Node / TextNode | 切分后的块，索引与检索的基本单位 |
| 节点解析器 | NodeParser / SentenceSplitter | 把 Document 切成 Node |
| 索引 | Index | 对 Node 建立可查询结构（向量、列表、树、关键词等） |
| 向量存储 | VectorStore | 持久化向量（Chroma、FAISS、PGVector 等） |
| 嵌入 | Embedding | 文本转向量 |
| 检索器 | Retriever | 根据查询返回相关 Node |
| 响应合成 | Response Synthesizer | 把检索结果整理后交给 LLM 生成最终答案 |
| 查询引擎 | Query Engine | Retriever + 合成器的高层封装 |
| 聊天引擎 | Chat Engine | 多轮对话封装 |
| 工具 / Agent | Tool / Agent | 让模型调用检索或其他工具完成任务 |

---

## 三、从数据到答案的主流程

```text
数据源 → Document → 切分为 Node → Embedding → Index / VectorStore
                                                      ↓
用户问题 → Retriever（Top-K）→ Response Synthesizer → LLM → 答案（可带 citation）
```

| 阶段 | 关键点 |
|------|--------|
| 加载 | 选择合适的 Reader / Connector |
| 切分 | chunk 大小与 overlap 影响召回 |
| 索引 | 向量索引最常用；也可组合关键词/图谱 |
| 检索 | Top-K、相似度、元数据过滤、重排 |
| 合成 | 如何把多段上下文塞进 Prompt 再生成 |

---

## 四、Document 与 Node

| 概念 | 定义 |
|------|------|
| Document | 一篇完整材料，含 `text` 与 `metadata` |
| Node | 切分后的片段；检索命中的通常是 Node |
| metadata | 来源路径、标题、页码、类别等，用于过滤与溯源 |
| 关系 | Node 之间可保留前后文、父子、引用等关系（高级用法） |

**和 LangChain 的粗略对应：**

| LlamaIndex | LangChain |
|------------|-----------|
| Document / Node | Document（常直接切成多个 Document） |
| metadata | metadata |
| Index | VectorStore + 检索封装 |
| Query Engine | RAG Chain（retriever \| prompt \| llm） |

---

## 五、常见 Index 类型

| Index | 思路 | 适用场景 |
|-------|------|----------|
| VectorStoreIndex | 向量相似度检索 | 最常用的 RAG 默认选择 |
| SummaryIndex / ListIndex | 遍历或摘要式合成 | 全文总结、小语料 |
| TreeIndex | 树状层级摘要 | 长文档分层查询 |
| KeywordTableIndex | 关键词映射到节点 | 关键词明确的检索 |
| KnowledgeGraphIndex | 实体关系图谱 | 需要关系推理的知识问答 |
| Composable / Router | 多索引路由 | 多数据源、多策略组合 |

> 入门优先掌握 **VectorStoreIndex + QueryEngine**，再学 Router / Agent。

---

## 六、查询侧三大引擎

| 引擎 | 输入输出 | 何时用 |
|------|----------|--------|
| Query Engine | 一问一答（可流式） | 单次知识问答、批处理问答 |
| Chat Engine | 多轮对话 | 需要上下文连续的助手 |
| Retriever | 只返回 Node，不生成 | 只要检索结果，自己拼 Prompt |

**Query Engine 内部通常包含：**

1. 查询改写 / 变换（可选）  
2. Retriever 取回 Node  
3. 节点后处理（过滤、重排、截断）  
4. Response Synthesizer + LLM 生成  

---

## 七、检索增强常用技巧

| 技巧 | 英文 | 说明 |
|------|------|------|
| Top-K 检索 | Top-K Retrieval | 取最相似的 K 个片段 |
| 元数据过滤 | Metadata Filtering | 按来源、类别、时间缩小范围 |
| 混合检索 | Hybrid Search | 向量 + 关键词（如 BM25）互补 |
| 重排序 | Reranking | 用更强模型对候选再排序 |
| 句子窗口 / 自动合并 | Sentence Window / Auto Merging | 检索小块，返回时扩成更大上下文 |
| 子问题分解 | Sub-Question | 复杂问题拆成多个子查询再汇总 |
| 路由 | Router | 按问题类型选择不同索引或引擎 |

---

## 八、LLM 与 Embedding 配置思路

| 概念 | 说明 |
|------|------|
| LLM | 负责生成、改写、Agent 决策 |
| Embeddings | 负责向量化文档与查询 |
| 兼容 OpenAI 协议 | 可通过自定义/第三方封装接入 Moonshot、SiliconFlow 等 |
| Settings / 全局默认 | 可设置默认 LLM、Embedding、chunk 参数 |

**实践注意：**

1. 聊天模型与 Embedding 模型不要混用  
2. 换 Embedding 模型后，旧向量库通常要**重建索引**  
3. 中文场景优先选对中文效果好的 Embedding  
4. 密钥放环境变量，避免写死在代码里  

---

## 九、Agent 与工具（入门级）

| 概念 | 说明 |
|------|------|
| QueryEngineTool | 把某个 Query Engine 包成工具供 Agent 调用 |
| Function/Tool | 自定义函数工具（计算、API、查库） |
| AgentWorker / AgentRunner | 规划并调用工具，直到得出最终答复 |
| Workflow | 更细粒度的多步骤、事件驱动编排 |

**何时上 Agent：** 需要在多个知识库间选择、先检索再计算、或多步工具协作；简单单库问答用 Query Engine 即可。

---

## 十、LlamaIndex vs LangChain（怎么选）

| 维度 | LlamaIndex | LangChain |
|------|------------|-----------|
| 定位重心 | 数据连接、索引与 RAG 查询 | 通用链路编排、LCEL、生态广 |
| RAG 抽象 | Index / QueryEngine 更「开箱」 | Retriever + Chain 自己拼装更灵活 |
| Agent | 有，且 Workflow 在增强 | Tool Calling + LangGraph 很强 |
| 表达方式 | 引擎/索引对象 API | Runnable 管道 `\|` 组合 |
| 学习建议 | 做文档问答、知识库优先可先看它 | 做复杂工作流、多集成时可优先它 |

两者不是互斥：可以一个做检索索引，一个做业务编排；入门阶段选一个主线吃透即可。

---

## 十一、最小示例心智模型

```text
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

docs = SimpleDirectoryReader("notes").load_data()
index = VectorStoreIndex.from_documents(docs)
qe = index.as_query_engine()
print(qe.query("什么是过拟合？"))
```

对应步骤：

1. `SimpleDirectoryReader`：加载 `notes/` 下文档  
2. `from_documents`：切分 + 向量化 + 建索引  
3. `as_query_engine`：得到可提问的引擎  
4. `query`：检索相关片段并生成回答  

---

## 十二、与本仓库笔记场景的映射

| 你的资料 | 在 LlamaIndex 中怎么用 |
|----------|------------------------|
| `notes/*.md` | DirectoryReader 加载为 Document |
| 机器学习概念/算法/案例 | 建统一 VectorStoreIndex，按 metadata 区分来源 |
| 笔记助手问答 | Query Engine 或 Chat Engine |
| 只要检索不要生成 | `as_retriever()` 取 Node |
| 多主题路由 | RouterQueryEngine 分到不同索引 |

---

## 十三、易混概念

| 对比 | 区别 |
|------|------|
| Document vs Node | 原文整体 vs 切分后的检索单元 |
| Index vs VectorStore | Index 是查询抽象；VectorStore 是向量持久化后端 |
| Retriever vs Query Engine | 只检索 vs 检索 + 生成答案 |
| Query Engine vs Chat Engine | 单轮问答 vs 带历史多轮 |
| 切分太碎 vs 太粗 | 碎了上下文不全；粗了噪声多、检索不准 |
| LlamaIndex vs 微调 | 外挂知识可更新；微调改权重，成本更高 |

---

## 十四、术语速查

| 中文 | 英文 |
|------|------|
| 索引 | Index |
| 节点 | Node |
| 查询引擎 | Query Engine |
| 聊天引擎 | Chat Engine |
| 检索器 | Retriever |
| 响应合成 | Response Synthesis |
| 重排序 | Rerank |
| 引用 / 溯源 | Citation / Source Nodes |
| 数据连接器 | Data Connector / Reader |
| 工作流 | Workflow |

---

## 十五、落地检查清单

1. 文档是否成功加载（编码、路径、空文件）  
2. chunk 大小是否适合你的问题粒度  
3. Embedding 与索引是否同一模型产出  
4. Top-K 是否过小（召不回）或过大（噪声多）  
5. 回答是否要求基于检索上下文（减少幻觉）  
6. 是否返回 source nodes，便于核对引用  

---

## 十六、参考阅读顺序（自学）

1. Document / Node / 简单目录加载  
2. VectorStoreIndex + Query Engine  
3. Retriever 参数、metadata 过滤  
4. Chat Engine 多轮对话  
5. 重排、混合检索、Router  
6. Agent / Workflow（进阶）  

> 本文面向笔记检索与复习，强调 LlamaIndex「数据如何进入索引、问题如何变成答案」。具体类名与安装包可能随版本调整，以官方文档当前版本为准。
