export type ChatMode = 'agent' | 'rag'

export interface ChatResponse {
  session_id: string
  reply: string
}

export interface RagResponse {
  answer: string
}

export interface HealthResponse {
  status: string
}

/** SSE 事件：与后端 note_assistant.service 约定一致 */
export type StreamEvent =
  | { type: 'session'; session_id: string }
  | { type: 'status'; content: string }
  | { type: 'token'; content: string }
  | { type: 'reset' }
  | { type: 'done' }
  | { type: 'error'; message: string }

async function readSseStream(
  response: Response,
  onEvent: (event: StreamEvent) => void,
) {
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `请求失败 (${response.status})`)
  }
  if (!response.body) {
    throw new Error('浏览器不支持流式响应')
  }

  // 从 Response.body（ReadableStream）拿到默认 reader，按块读取 SSE 字节流
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const line = part
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l.startsWith('data:'))
      if (!line) continue
      const payload = line.replace(/^data:\s*/, '')
      if (!payload || payload === '[DONE]') continue
      try {
        onEvent(JSON.parse(payload) as StreamEvent)
      } catch {
        // 忽略无法解析的片段
      }
    }
  }
}

export async function checkHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`health ${res.status}`)
  return (await res.json()) as HealthResponse
}

/** Agent 流式对话 */
export async function streamChat(
  message: string,
  sessionId: string | null | undefined,
  onEvent: (event: StreamEvent) => void,
) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
    }),
  })
  await readSseStream(res, onEvent)
}

/** RAG 流式问答 */
export async function streamRag(
  question: string,
  onEvent: (event: StreamEvent) => void,
) {
  const res = await fetch('/api/rag/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ question }),
  })
  // 流式组装过程：
  // 1. 后端以 SSE 推送事件（session / status / token / reset / done / error）
  // 2. readSseStream 按行读取 Response.body，剥离 "data: " 前缀并 JSON.parse
  // 3. 每个事件回调 onEvent；前端 store 将 type=token 的 content 累加到助手消息
  // 4. type=reset 时清空缓冲（工具调用后只展示最终回答）；done 表示结束
  await readSseStream(res, onEvent)
}
