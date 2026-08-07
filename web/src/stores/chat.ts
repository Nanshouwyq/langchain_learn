import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  checkHealth,
  streamChat,
  streamRag,
  type ChatMode,
} from '@/api/noteAssistant'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  mode?: ChatMode
}

const QUICK_PROMPTS = [
  '列出所有笔记',
  'python 基础讲了什么',
  '帮我创建一篇机器学习笔记',
  '什么是RAG',
] as const

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export const useChatStore = defineStore('chat', () => {
  const mode = ref<ChatMode>('agent')
  const sessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([
    {
      id: uid(),
      role: 'system',
      content:
        '你好，我是学习笔记助手。可选 Agent（可管理笔记）或 RAG（只基于笔记问答）。',
    },
  ])
  const input = ref('')
  const loading = ref(false)
  const health = ref<'unknown' | 'ok' | 'down'>('unknown')
  const error = ref('')

  const quickPrompts = computed(() => [...QUICK_PROMPTS])

  async function refreshHealth() {
    try {
      const data = await checkHealth()
      health.value = data.status === 'ok' ? 'ok' : 'down'
    } catch {
      health.value = 'down'
    }
  }

  function clearChat() {
    sessionId.value = null
    error.value = ''
    messages.value = [
      {
        id: uid(),
        role: 'system',
        content: '对话已清空。可以继续提问或管理笔记。',
      },
    ]
  }

  async function send(text?: string) {

    const content = (text ?? input.value).trim()
    if (!content || loading.value) return

    error.value = ''
    input.value = ''
    messages.value.push({ id: uid(), role: 'user', content })
    loading.value = true

    const assistantId = uid()
    messages.value.push({
      id: assistantId,
      role: 'assistant',
      content: '',
      mode: mode.value,
    })

    const patchAssistant = (content: string) => {
      const idx = messages.value.findIndex((m) => m.id === assistantId)
      if (idx < 0) return
      const prev = messages.value[idx]
      // 替换整条消息，确保流式过程中 UI 及时刷新
      messages.value.splice(idx, 1, { ...prev, content })
    }

    let assistantText = ''

    try {
      const onEvent = (event: {
        type: string
        session_id?: string
        content?: string
        message?: string
      }) => {
        if (event.type === 'session' && event.session_id) {
          sessionId.value = event.session_id
        } else if (event.type === 'status' && event.content) {
          // 工具调用等中间状态（不覆盖最终回答缓冲）
          if (!assistantText) {
            patchAssistant(event.content)
          }
        } else if (event.type === 'reset') {
          assistantText = ''
          patchAssistant('')
        } else if (event.type === 'token' && event.content) {
          assistantText += event.content
          patchAssistant(assistantText)
        } else if (event.type === 'error') {
          throw new Error(event.message || '流式请求失败')
        }
      }

      if (mode.value === 'rag') {
        await streamRag(content, onEvent)
      } else {
        await streamChat(content, sessionId.value, onEvent)
      }

      if (!assistantText.trim()) {
        assistantText = '暂时没有得到有效回复'
        patchAssistant(assistantText)
      }
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message: string }).message)
          : '请求失败'
      error.value = msg
      if (!assistantText.trim()) {
        patchAssistant(
          '请求失败。请确认后端已启动：`uvicorn api.main:app --reload --host 127.0.0.1 --port 8000`',
        )
      }
    } finally {
      loading.value = false
    }
  }

  return {
    mode,
    sessionId,
    messages,
    input,
    loading,
    health,
    error,
    quickPrompts,
    refreshHealth,
    clearChat,
    send,
  }
})
