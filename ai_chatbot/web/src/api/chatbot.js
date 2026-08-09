async function readSseStream(response, onEvent) {
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `请求失败 (${response.status})`)
  }
  if (!response.body) {
    throw new Error('浏览器不支持流式响应')
  }

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
        onEvent(JSON.parse(payload))
      } catch {
        // ignore bad chunk
      }
    }
  }
}

export async function checkHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`health ${res.status}`)
  return res.json()
}

export async function streamChat(message, sessionId, onEvent) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
    }),
  })
  await readSseStream(res, onEvent)
}

export async function streamReview(sessionId, result, notes, onEvent) {
  const res = await fetch('/api/chat/review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      result,
      notes: notes || '',
    }),
  })
  await readSseStream(res, onEvent)
}
