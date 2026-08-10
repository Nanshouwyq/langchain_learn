# AI 应用工程师面试题（问答版）

> 面向苏州地区常见 JD（Agent / RAG / Prompt / LangChain·LangGraph / Dify / 工程落地）  
> 答案结合本仓库已落地系统：`note_assistant`（笔记 Agent + RAG）、`ai_chatbot`（多专家客服）、FastAPI SSE、评测与 LangSmith。  
> 背景叙事建议：**前端 8 年转 AI 应用**，主线是「能交付的 Agent + 知识库应用」。

---

## 使用说明

- 先熟 **加粗题**（高频）  
- 口述控制在 **1～2 分钟**；细节等追问再展开  
- 不会的坦诚说「方案已设计 / 正在用 Dify 补齐」，不要编造线上规模数据  

---

## 一、自我介绍与动机

### Q1. 请做一下自我介绍。（高频）

**答：**  
我做了 8 年前端，熟悉工程化与用户体验；目前转向 AI 应用工程，方向是 Agent + RAG 落地。  
独立做过学习笔记智能助手：LangGraph Agent 负责笔记增删改查，问答走本地 Markdown 知识库 RAG；用 FastAPI + SSE 做流式，Vue 前端逐字展示；并用 LangSmith 定位延迟，做了关闭 thinking、上下文压缩、知识问答短路直连 RAG 等优化。  
另外做过多专家客服：按问题路由到订单/产品/售后/技术，支持人工审核与流式前后端。  
优势是懂交互交付，同时具备 Agent 编排、RAG 链路和联调排障能力，希望做知识库/智能助手类应用落地。

### Q2. 为什么从前端转 AI？会不会后端太弱？

**答：**  
AI 产品大量体验问题出在流式、状态、可理解的过程反馈上，这是我的长板。  
后端我按应用岗需要补齐了 Python、FastAPI、向量库与工具调用；分布式和高并发不是我当前主线。  
AI 应用更看重「编排、检索、效果、交付」，这条路径我已用完整项目跑通。

### Q3. 期望薪资？空窗怎么解释？（结合个人情况可改数字）

**答（示例）：**  
5 月优化后系统补齐 AI 应用能力，已有可演示的 Agent+RAG 项目。  
此前前端 base 大约 19k，转型后更看重方向，期望 20k 左右，可按岗位职责谈。

---

## 二、项目深挖（结合本仓库）

### Q4. 笔记助手整体架构是什么？（高频）

**答：**  
三层：  
1）**Agent 层**：LangGraph + 工具（创建/更新/删除/列表/基于笔记问答）；  
2）**RAG 层**：笔记加载 → 切分 → BGE Embedding → Chroma → Prompt → LLM；  
3）**服务层**：FastAPI 提供 `/chat/stream`、`/rag/stream`，前端 SSE 消费。  
知识问答可短路跳过首轮「选工具」模型，直接走 RAG，降低延迟。

### Q5. 为什么既要 Agent 又要 RAG 短路？

**答：**  
Agent 适合意图多样、需要调工具（写笔记、列表）。  
纯「什么是 RAG」这类问题不需要工具决策；LangSmith 显示首轮 model 常占数秒。  
短路直连检索生成，少一轮 LLM，体验更好；写操作与复杂意图仍走 Agent。

### Q6. `return_direct` 是什么？解决了什么问题？

**答：**  
工具设置 `return_direct=True` 后，工具结果直接作为最终回复，不再进模型复述。  
用于 `answer_from_notes`、`list_notes`，避免「RAG 已流式输出一遍，Agent 又总结一遍」的重复。  
写操作工具不 return_direct，让模型给一句短确认即可。

### Q7. 流式输出怎么做的？事件有哪些？

**答：**  
后端 SSE：`session` / `status` / `token` / `reset` / `done` / `error`（客服还有 `review_required`）。  
前端 fetch 读 `ReadableStream`，按 `\n\n` 拆 SSE，解析 `data:` JSON，增量更新助手气泡。  
代理需关闭缓冲，避免 token 攒在一起。

### Q8. 你怎么用 LangSmith 优化性能？

**答：**  
导出 trace 看 span：主耗时在 **RAG 的 ChatOpenAI 生成**（可达数十秒），其次是 Agent 首轮 model；检索约 1s。  
措施：kimi 关闭 thinking 并对齐 temperature；缩小检索 K 与上下文；限制 max_tokens；精简 Prompt；知识问答短路。  
优化后知识问答从近分钟级降到十几秒量级（视问题与模型而定）。

### Q9. 多专家客服怎么路由？人工审核怎么做？

**答：**  
路由节点用 LLM 把问题分到 order/product/service/tech，再进对应专家 Prompt。  
售后含退货/退款等敏感词时标记需审核：API 返回 `review_required`，前端弹窗；通过/拒绝后调 `/chat/review` 再流式生成最终答复。  
后续可接到 n8n + MySQL 工单（已有方案设计）。

---

## 三、RAG（苏州 JD 几乎必考）

### Q10. 解释一下 RAG，解决什么问题？（高频）

**答：**  
Retrieval-Augmented Generation：先检索外部知识，再基于检索结果生成。  
解决私有知识更新难、幻觉、无法引用资料等问题；改文档重建索引即可更新，不必微调模型。

### Q11. 离线流水线和在线流水线分别做什么？（高频）

**答：**  
**离线：** 文档加载 → 清洗解析 → Chunk → Embedding → 写入向量库。  
**在线：** Query → 预处理 → 检索召回 →（可选 Rerank）→ Prompt 组装 → LLM → 答案 + 溯源。  
我项目里离线在建库/笔记变更重建；在线在 `ask_notes` / `/rag`。

### Q12. Chunk 大小怎么选？你踩过什么坑？

**答：**  
要在「语义完整」和「Embedding 模型上限」之间平衡。  
我们用 BGE，上下文大约 512 token，中文过长会 SiliconFlow **20015**。  
曾把 CHUNK_SIZE 提到 900 导致建库失败；现约 450 字，并控制 embedding batch。

### Q13. 向量检索原理？用的什么库和模型？

**答：**  
文本经 Embedding 成向量，用相似度（如余弦）取 Top-K。  
Embedding：SiliconFlow `BAAI/bge-large-zh-v1.5`；向量库：Chroma 本地持久化。  
第三方 Embedding 需注意 `check_embedding_ctx_length` 等兼容问题。

### Q14. 什么是 Rerank？和初检有什么区别？

**答：**  
初检（召回）追求「多而粗」，如向量 Top-N；Rerank 对候选精排，取 Top-K 再进 Prompt。  
可用交叉编码器/bge-reranker 或 LLM 打分。  
我项目 P0 是向量 Top-K；完整方案里设计了 Recall-N → Rerank-K；study 里有混合检索与 RRF demo。

### Q15. RRF 是什么？

**答：**  
Reciprocal Rank Fusion：多路检索结果按**排名**融合，不直接比不同体系的分数。  
公式直觉：\(1/(k+rank)\)，多路都靠前的文档总分高。  
常用于「向量 + BM25」混合检索合并。

### Q16. 如何降低幻觉？如何做溯源？

**答：**  
Prompt 约束只依据笔记；无相关明确说没有；控制温度与胡编空间。  
溯源：context 带来源文件名；方案上应升级为 chunk 级 `citations`（S1/S2）与前端展示。  
评测用黄金集 `must_include` 做回归。

### Q17. 查询改写要不要上？

**答：**  
改写能缓解口语与文档措辞不一致，但多一次 LLM、更慢。  
我默认 `ENABLE_QUERY_REWRITE=False`；检索不准时再开。  
这是「准 vs 快」的配置化取舍。

---

## 四、Agent / Tool Calling（高频）

### Q18. 什么是 AI Agent？和普通 ChatBot 区别？

**答：**  
ChatBot 多是单轮/多轮生成；Agent 能**规划并调用工具**改变外部状态或获取信息，再组织回答。  
我的笔记助手：问知识→检索工具；说创建笔记→写文件并重建索引。

### Q19. Function Calling / Tool Calling 流程？

**答：**  
模型输出 structured tool_calls → 执行工具 → ToolMessage 回填 → 模型继续或 return_direct 结束。  
要注意：历史里不能留下「有 tool_calls 无 ToolMessage」的半截状态，否则下次请求易 400；我用 middleware 补齐空洞。

### Q20. 什么时候不该用 Agent？

**答：**  
路径固定、只要检索生成、对延迟敏感、工具副作用大且需强管控时，用固定链路或 Workflow 更合适。  
所以我把纯知识问答做成短路 RAG。

### Q21. Multi-Agent 你怎么理解？你项目里如何体现？

**答：**  
按职责拆多个专家，由路由决定交给谁，避免一个巨 Prompt 包打天下。  
`ai_chatbot`：route → order/product/service/tech；售后敏感再进人工审核。  
协作方式还可以是分工并行、评审等，我当前是**路由式**。

### Q22. LangGraph 相对纯 LangChain Chain 的价值？

**答：**  
Graph 适合有状态、分支、循环、中断（如审核前 interrupt）。  
Chain 适合线性 RAG。  
复杂 Agent 与人机环更适合 Graph。

---

## 五、模型、Prompt 与参数

### Q23. Prompt Engineering 你怎么做？

**答：**  
角色 + 约束 + 输入槽位 + 输出格式；工具场景写清「何时调用、是否复述」。  
RAG Prompt 从「完整覆盖长文」改为「300～500 字要点」，显著降生成耗时。  
靠评测集和线上 badcase 迭代，而不是一次写完美。

### Q24. temperature 等参数怎么设？kimi 有什么坑？

**答：**  
一般任务可低温度更稳；但 **kimi-k2.6** 的 temperature 必须与 thinking 模式对齐（开≈1，关≈0.6），乱设易 20015。  
ChatOpenAI 默认 0.7 也可能踩坑，必须显式对齐。  
关闭 thinking 可明显加快首轮 tool 决策。

### Q25. 微调 vs RAG 怎么选？

**答：**  
知识常变、要可引用、成本敏感 → **优先 RAG**。  
要固化风格/格式/领域表述且知识相对稳定 → 再考虑微调/LoRA。  
企业助手多数先 RAG + Prompt，我项目即此路线。

---

## 六、Dify / 平台与编排（苏州 JD 常写）

### Q26. Dify 是什么？和自研怎么选？（高频）

**答：**  
Dify 是 LLM 应用平台，内置知识库、Agent、Workflow、发布 API。  
**快交付、标准知识库助手**用 Dify；**强定制流式、特殊工具协议、极致优化与复杂状态**用自研 LangGraph。  
也可以 Dify Workflow 里 HTTP 调我的 FastAPI，平台做壳、核心逻辑自研。

### Q27. Dify 里 Agent 和 Workflow 区别？

**答：**  
Agent：模型自主选工具，灵活但不稳定。  
Workflow：节点编排，路径可控，适合审核、固定步骤。  
对应我项目：工具选择≈Agent；短路 RAG、审核分支≈Workflow 思维。

### Q28. Dify / Coze / n8n 怎么区分？

**答：**  
Dify/Coze：偏对话与 LLM 应用。  
n8n：通用自动化（企微、MySQL、定时）。  
企微接入用 n8n 接通道，智能用 Dify 或自研 Agent/RAG。

---

## 七、工程、前端与交付

### Q29. 如何把 AI 能力接到业务系统？

**答：**  
封装 HTTP API（同步 `/chat`、流式 `/chat/stream`）；鉴权；超时与重试；会话 ID 贯穿。  
企业微信等渠道：Webhook 先快速 ACK，异步调 Agent，再主动推送（因模型耗时往往超过被动回复窗口）。  
会话与工单落 MySQL（设计：sessions/messages/tickets）。

### Q30. 前端 8 年经验如何用在 AI 产品？

**答：**  
流式首字体验、status 过程可见、审核弹窗、错误可恢复、防重复渲染。  
很多 AI 项目能答但难用，体验与状态机是交付关键。

### Q31. 如何评测 AI 应用好不好？

**答：**  
离线黄金集（关键词/必含/必不含）；改 Prompt/TopK 后对比 pass_rate。  
同步 LangSmith Dataset 做实验对比。  
进阶：引用是否命中正确文档、人工满意度、延迟分位、成本。

### Q32. Docker / 部署了解多少？

**答：**  
项目可用容器跑 API 与依赖；向量库与 notes 挂卷持久化。  
（按你实际补充：是否已写 Dockerfile。）  
生产还需配置、密钥、日志、健康检查——`/health` 已具备基础。

---

## 八、场景题（现场设计）

### Q33. 给制造厂做「工艺文档助手」，你怎么设计？

**答：**  
离线：工艺 PDF/Word → 清洗切分 → 向量库，metadata 含产线/型号。  
在线：问答 + 强制引用条款；权限按车间隔离知识库。  
入口：企微或 MES 内嵌；敏感变更走人工。  
先 Dify/自研快速试点，再按延迟与准确率迭代 Rerank 与分段。

### Q34. 用户说「答非所问」，排查顺序？

**答：**  
1）是否检索到错文档（看召回）→ 调 K/改写/补文档；  
2）检索对但生成跑偏 → 改 Prompt、加引用约束、降温度；  
3）Chunk 切碎/切错 → 调切分；  
4）需要精排 → 上 Rerank。  
用 LangSmith 看各 span 输入输出最快定位。

### Q35. 如何控制成本与延迟？

**答：**  
能固定链路不走 Agent；关不必要改写/thinking；限制检索条数与 max_tokens；缓存重复问；小模型做路由、大模型做难生成（可演进）。  
我已用短路 + 参数限制做过一轮。

---

## 九、算法基础（应用岗够用即可）

### Q36. Embedding 相似度？ANN 听过吗？

**答：**  
常用余弦相似度/点积。  
数据量大时用近似近邻（HNSW 等）换速度，Chroma/FAISS/Milvus 等会用到。  
当前笔记规模小，精确 Top-K 即可。

### Q37. BM25 和向量检索区别？

**答：**  
BM25 偏关键词字面匹配，专有词、报错码强；向量偏语义。  
难例用混合 + RRF。学习 demo 有实现，业务默认先向量。

---

## 十、行为与软技能

### Q38. 空窗期在做什么？

**答：**  
系统补 AI 应用：Agent、RAG、流式工程、评测与性能优化、方案设计（企微/n8n、完整 RAG 链路），并整理面试与可演示材料，而不是空白等待。

### Q39. 职业规划？

**答：**  
近 1～2 年定位 AI 应用工程师，把 Agent/知识库类需求稳定交付；发挥前端优势打磨体验；补齐评测与观测；中期可向复杂工作流/FDE 交付或 AI 全栈深化。

### Q40. 你的缺点？

**答：**  
缺少多年线上 AI 业务运营数据；大规模分布式与模型训练不是长板。  
用完整项目与可观测方法弥补落地能力，入职后会在真实流量与指标上快速补齐。

---

## 附录 A：苏州 JD 常见关键词 ↔ 你的证据

| JD 要求 | 你的证据 |
|---------|----------|
| Python + LLM API | Moonshot/SiliconFlow、`ChatOpenAI` |
| LangChain / LangGraph | Agent、工具、Graph 路由 |
| RAG / Embedding / 向量库 | Chroma + BGE + ask_notes |
| Function Calling | 笔记工具集 |
| Prompt | 系统提示与 RAG 模板迭代 |
| 工程落地 / API | FastAPI、SSE、Vue |
| 效果优化 | LangSmith、thinking、短路 |
| Dify/Coze/n8n | 概念准备；Dify 建议实操补齐；n8n 有接入设计 |
| 制造业/知识库场景 | 用「工艺/笔记文档助手」类比叙述 |

---

## 附录 B：建议口述顺序（项目题）

1. 场景与用户是谁（10 秒）  
2. 架构三层（20 秒）  
3. 一个难点 + 怎么验证（LangSmith/报错）（30 秒）  
4. 结果与取舍（20 秒）  
5. 下一步（Rerank/Dify/渠道）（10 秒）  

---

*文档版本：结合当前仓库能力整理，可随项目迭代更新「已落地 / 仅方案」标注。*
