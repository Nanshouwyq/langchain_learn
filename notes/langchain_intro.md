# LangChain 入门导览（langchain_intro）

**标签**: LangChain, LLM, RAG

LangChain 是用于构建 **LLM 应用** 的框架，把提示词、模型、检索、工具、记忆等能力用统一的 **Runnable 接口** 串成链路。本文按「概念—组件—模式—落地」整理，便于笔记检索与复习。

---

## 一、它是什么、解决什么问题

| 概念 | 英文 | 说明 |
|------|------|------|
| LangChain | LangChain | 面向 LLM 应用的编排框架（链、检索、Agent、记忆等） |
| LCEL | LangChain Expression Language | 用 `\|` 组合 Runnable 的表达方式 |
| Runnable | Runnable | 可 `invoke` / `stream` / `batch` 的统一执行单元 |
| LangGraph | LangGraph | 更适合复杂状态机 / 多 Agent 工作流的图编排（常与 LangChain 搭配） |
| LangSmith | LangSmith | 链路追踪、调试、评估与监控平台 |

**典型要解决的问题：**

1. 把 Prompt、模型、解析器、检索器拼成可维护流水线  
2. 对接 OpenAI 兼容 API（含 Moonshot、硅基流动等）  
3. 做 RAG：文档 → 向量库 → 检索 → 生成回答  
4. 做 Agent：模型按需调用工具  
5. 保留多轮对话上下文  

---

## 二、核心组件一览

| 组件 | 英文 / 模块方向 | 作用 |
|------|-----------------|------|
| 提示词模板 | PromptTemplate / ChatPromptTemplate | 把变量填进提示，支持 system/user/history |
| 聊天模型 | ChatModel（如 ChatOpenAI） | 对话式 LLM 调用 |
| 嵌入模型 | Embeddings（如 OpenAIEmbeddings） | 文本转向量 |
| 输出解析器 | OutputParser | 把模型输出转成 str/JSON/结构化对象 |
| 文档加载与切分 | Document Loaders / Text Splitters | 读文件并切成适合检索的块 |
| 向量库 | VectorStore（如 Chroma） | 存向量、相似度搜索 |
| 检索器 | Retriever | 对查询返回相关 Document |
| 工具 | Tool | 给 Agent 调用的外部能力（搜索、计算、API） |
| 记忆 | Memory / Checkpoint | 保存对话或状态 |
| 回调 / 追踪 | Callbacks / LangSmith | 观测中间步骤与耗时 |

---

## 三、LCEL 与 Runnable（必会）

LCEL 的核心是：`runnable1 | runnable2 | runnable3`，上一步输出作为下一步输入。

| Runnable | 作用 | 常见用法 |
|----------|------|----------|
| 模型 / Prompt / Parser | 基础积木 | `prompt \| llm \| StrOutputParser()` |
| RunnablePassthrough | 原样传递输入 | RAG 里保留 `question` |
| RunnableParallel | 并行执行多条链 | 同时生成笑话与诗、或多路检索 |
| RunnableLambda | 把普通函数包成 Runnable | 清洗文本、格式化文档 |
| RunnableBranch | 按条件走不同分支 | 技术问题走技术专家链 |

**三种常用执行方式：**

| 方法 | 含义 |
|------|------|
| `invoke` | 单次输入 → 单次输出 |
| `batch` | 一批输入并行/批量处理 |
| `stream` | 流式输出 token / 中间事件 |

---

## 四、Prompt 基础

| 类型 | 说明 |
|------|------|
| PromptTemplate | 字符串模板，适合补全式提示 |
| ChatPromptTemplate | 多角色消息模板（system / human / ai） |
| MessagesPlaceholder | 占位插入历史消息列表 |
| 变量填充 | 用 `{question}`、`{context}` 等占位，invoke 时传入字典 |

**示例形态：**

```text
system: 你是助手，仅依据上下文回答
user: 上下文：{context}
      问题：{question}
```

---

## 五、模型接入（Chat / Embedding）

| 概念 | 说明 |
|------|------|
| ChatOpenAI | 兼容 OpenAI Chat Completions 协议的聊天封装 |
| OpenAIEmbeddings | 兼容 OpenAI Embeddings 协议的向量封装 |
| `base_url` + `api_key` | 可指向 Moonshot、SiliconFlow 等兼容服务 |
| `model` | 具体模型名（聊天与向量模型不要混用） |

**实践注意：**

1. **聊天模型**与 **Embedding 模型** 职责不同，参数不要串用  
2. 接第三方 Embedding 时，常需 `check_embedding_ctx_length=False`（避免按 OpenAI token 数组方式请求）  
3. 部分模型对 `temperature` 有限制（如部分 Kimi 仅允许特定值）  
4. 密钥放 `.env`，用 `python-dotenv` 加载  

---

## 六、RAG（检索增强生成）

RAG = **Retrieval-Augmented Generation**：先检索相关知识，再让模型基于检索结果生成，降低幻觉、可引用资料。

### 标准流水线

```text
文档 → 切分 → Embedding → 写入向量库
                ↑
用户问题 → 向量检索 Top-K → 拼进 Prompt → LLM → 答案
```

| 步骤 | 关键点 |
|------|--------|
| 切分 | `chunk_size` / `chunk_overlap` 影响召回粒度 |
| 入库 | Document 含 `page_content` + `metadata` |
| 检索 | `as_retriever(search_kwargs={"k": n})` |
| 组装 | `context` 与 `question` 并行准备后进 Prompt |
| 生成 | Chat 模型回答；可用引用 metadata 溯源 |

**最小 LCEL 形态（示意）：**

```text
{"context": retriever | format_docs, "question": RunnablePassthrough()}
| prompt | llm | StrOutputParser()
```

---

## 七、Document 与向量库

| 概念 | 定义 |
|------|------|
| Document | 一条知识单元：`page_content`（正文）+ `metadata`（标签） |
| metadata | 每条文档自己的属性，如 `{"category": "编程", "source": "notes/xxx.md"}` |
| 相似度搜索 | 按向量距离找最相近文档 |
| 元数据过滤 | `filter={"category": "编程"}` 缩小检索范围 |
| 持久化目录 | 如 Chroma 的 `persist_directory`，重启后可继续读 |

---

## 八、工具与 Agent

| 概念 | 说明 |
|------|------|
| Tool | 带名称、描述、参数模式的可调用函数 |
| Tool Calling | 模型输出「要调哪个工具、参数是什么」 |
| Agent | 循环：思考 → 调工具 → 观察 → 再思考，直到给出最终答案 |
| 强制工具调用 | 约束模型必须/只能调用某些工具 |

**何时用 Agent：** 需要查实时信息、算数、读写外部系统；纯知识问答优先 RAG，不必上 Agent。

---

## 九、记忆（Memory）

| 概念 | 说明 |
|------|------|
| 无记忆 | 每轮独立，模型看不到历史 |
| 对话缓冲 | 保存近期消息列表，塞进 MessagesPlaceholder |
| 摘要记忆 | 长对话压缩成摘要，控制 token |
| Checkpoint / Thread | 按会话 ID 持久化状态，支持多用户多线程 |

---

## 十、输出解析与结构化

| 解析器 | 用途 |
|--------|------|
| StrOutputParser | 只要纯文本 |
| JsonOutputParser | 解析 JSON |
| 结构化输出（Pydantic 等） | 强制字段类型，便于下游程序使用 |

---

## 十一、可观测性（LangSmith）

| 环境变量 | 作用 |
|----------|------|
| `LANGSMITH_TRACING` | 是否开启追踪（如 `true`） |
| `LANGSMITH_API_KEY` | LangSmith API 密钥 |
| `LANGSMITH_PROJECT` | 项目名称，便于在控制台过滤 |
| `LANGSMITH_ENDPOINT` | 服务地址（默认官方云） |

开启后，`invoke` 链路的 Prompt、检索结果、耗时可在 LangSmith 中回放，便于排错。

---

## 十二、与本仓库学习路径对照

| 主题 | 建议关注点 |
|------|------------|
| Prompt / ChatModel | 模板变量、消息角色、流式输出 |
| Runnable | Passthrough、Lambda、Parallel、Branch |
| 向量库 | 创建、读取、相似度搜索、metadata 过滤 |
| RAG 链 | retriever + format_docs + prompt + llm |
| Tools | 定义工具、自动/强制工具调用 |
| Memory | 有无历史对多轮问答的影响 |
| note_assistant | 笔记入库 + RAG 问答综合练习 |

---

## 十三、最小心智模型（一张图）

```text
输入
  │
  ├─(可选) 检索 / 工具 / 记忆
  │
  ▼
Prompt 组装
  │
  ▼
ChatModel
  │
  ▼
OutputParser / 结构化结果
  │
  ▼
输出（并可被 LangSmith 追踪）
```

---

## 十四、易混概念

| 对比 | 区别 |
|------|------|
| LangChain vs 直接调 OpenAI SDK | 框架侧重编排、检索、Agent；SDK 侧重单次 API 调用 |
| ChatModel vs Embeddings | 一个生成文本，一个生成向量 |
| Chain vs Agent | Chain 路径相对固定；Agent 动态决定是否调工具 |
| RAG vs 微调 | RAG 外挂知识可更新；微调改模型权重，成本更高 |
| metadata vs page_content | 标签用于过滤/溯源；正文才是主要向量化内容 |
| invoke vs stream | 一次性拿全量 vs 边生成边返回 |

---

## 十五、术语速查

| 中文 | 英文 |
|------|------|
| 链式表达式语言 | LCEL |
| 可运行组件 | Runnable |
| 检索增强生成 | RAG |
| 提示词 | Prompt |
| 嵌入 | Embedding |
| 向量存储 | Vector Store |
| 检索器 | Retriever |
| 工具调用 | Tool Calling |
| 智能体 | Agent |
| 幻觉 | Hallucination |
| 回调 | Callback |

---

## 十六、落地检查清单

1. `.env` 中聊天与 Embedding 的 key、base_url、model 是否分别正确  
2. 相对导入 / 包结构是否导致脚本无法直接运行  
3. RAG 是否真的把检索结果放进了 Prompt 的 `{context}`  
4. 向量库 `collection_name` 与 `persist_directory` 读写是否一致  
5. 需要排错时是否打开 LangSmith tracing  

---

## 参考阅读顺序（自学）

1. ChatPromptTemplate + ChatOpenAI + StrOutputParser  
2. LCEL：`|`、Passthrough、Lambda、Branch  
3. Document + Embeddings + Chroma 检索  
4. 组装最小 RAG 链  
5. Tool / Memory / LangSmith  

> 本文面向笔记检索与复习，强调 LangChain「组件怎么拼」，不展开某一版本的全部 API 细节。API 以你当前安装的 `langchain` / `langchain-openai` / `langchain-chroma` 文档为准。
