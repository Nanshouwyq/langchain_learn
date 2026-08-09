<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { checkHealth, streamChat, streamReview } from './api/chatbot.js'

const QUICK = [
  '我的订单到哪了？',
  '这个充电器支持多少瓦快充？',
  '保修政策是怎样的？',
  '设备开不了机怎么办？',
  '我想退货',
]

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const messages = ref([
  {
    id: uid(),
    role: 'system',
    content:
      '你好，我是多专家 AI 客服。支持订单 / 产品 / 售后 / 技术咨询，回复为流式输出。',
  },
])
const input = ref('')
const loading = ref(false)
const sessionId = ref(null)
const health = ref('unknown')
const error = ref('')
const statusText = ref('')
const listRef = ref(null)

const reviewOpen = ref(false)
const reviewNotes = ref('')
const pendingReviewSession = ref(null)

const canSend = computed(() => !!input.value.trim() && !loading.value)

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
  statusText.value = ''
  reviewOpen.value = false
  messages.value = [
    {
      id: uid(),
      role: 'system',
      content: '对话已清空，可以继续提问。',
    },
  ]
}

async function scrollBottom() {
  await nextTick()
  const el = listRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(messages, () => scrollBottom(), { deep: true })

function patchAssistant(id, content) {
  const idx = messages.value.findIndex((m) => m.id === id)
  if (idx < 0) return
  const prev = messages.value[idx]
  messages.value.splice(idx, 1, { ...prev, content })
}

async function send(text) {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return

  error.value = ''
  statusText.value = ''
  input.value = ''
  messages.value.push({ id: uid(), role: 'user', content })
  loading.value = true

  const assistantId = uid()
  messages.value.push({ id: assistantId, role: 'assistant', content: '' })
  let assistantText = ''

  try {
    await streamChat(content, sessionId.value, (event) => {
      if (event.type === 'session' && event.session_id) {
        sessionId.value = event.session_id
      } else if (event.type === 'status') {
        statusText.value = event.content || ''
      } else if (event.type === 'token') {
        assistantText += event.content || ''
        patchAssistant(assistantId, assistantText)
      } else if (event.type === 'review_required') {
        pendingReviewSession.value = event.session_id || sessionId.value
        assistantText = event.content || '需要人工审核'
        patchAssistant(assistantId, assistantText)
        reviewOpen.value = true
        reviewNotes.value = ''
      } else if (event.type === 'error') {
        error.value = event.message || '出错了'
      }
    })
    if (!assistantText && !error.value) {
      patchAssistant(assistantId, '暂时没有得到有效回复')
    }
  } catch (e) {
    error.value = e?.message || String(e)
    if (!assistantText) patchAssistant(assistantId, `错误：${error.value}`)
  } finally {
    loading.value = false
    statusText.value = ''
  }
}

async function submitReview(result) {
  const sid = pendingReviewSession.value || sessionId.value
  if (!sid || loading.value) return
  reviewOpen.value = false
  loading.value = true
  statusText.value = '正在根据审核结果生成回复…'
  error.value = ''

  const assistantId = uid()
  messages.value.push({ id: assistantId, role: 'assistant', content: '' })
  let assistantText = ''

  try {
    await streamReview(sid, result, reviewNotes.value, (event) => {
      if (event.type === 'token') {
        assistantText += event.content || ''
        patchAssistant(assistantId, assistantText)
      } else if (event.type === 'status') {
        statusText.value = event.content || ''
      } else if (event.type === 'error') {
        error.value = event.message || '审核失败'
      }
    })
    if (!assistantText && !error.value) {
      patchAssistant(assistantId, '审核流程已结束')
    }
  } catch (e) {
    error.value = e?.message || String(e)
    if (!assistantText) patchAssistant(assistantId, `错误：${error.value}`)
  } finally {
    loading.value = false
    statusText.value = ''
    pendingReviewSession.value = null
  }
}

onMounted(refreshHealth)
</script>

<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">AI Chatbot · Streaming</p>
        <h1>多专家客服</h1>
        <p class="sub">
          路由到订单 / 产品 / 售后 / 技术专家，答案以 SSE 逐字输出。
        </p>
      </div>
      <div class="meta">
        <span class="pill" :data-ok="health === 'ok'">
          API {{ health === 'ok' ? '在线' : health === 'down' ? '离线' : '检测中' }}
        </span>
        <button type="button" class="ghost" @click="clearChat">清空</button>
      </div>
    </header>

    <section class="panel">
      <div ref="listRef" class="messages">
        <div
          v-for="m in messages"
          :key="m.id"
          class="bubble"
          :data-role="m.role"
        >
          <div class="role">
            {{ m.role === 'user' ? '你' : m.role === 'system' ? '系统' : '客服' }}
          </div>
          <div class="body">{{ m.content || (loading ? '…' : '') }}</div>
        </div>
      </div>

      <div v-if="statusText" class="status">{{ statusText }}</div>
      <div v-if="error" class="error">{{ error }}</div>

      <div class="quick">
        <button
          v-for="q in QUICK"
          :key="q"
          type="button"
          :disabled="loading"
          @click="send(q)"
        >
          {{ q }}
        </button>
      </div>

      <form class="composer" @submit.prevent="send()">
        <textarea
          v-model="input"
          rows="2"
          placeholder="输入问题，例如：我想查物流 / 支持快充吗"
          :disabled="loading"
          @keydown.enter.exact.prevent="send()"
        />
        <button type="submit" class="send" :disabled="!canSend">
          {{ loading ? '生成中…' : '发送' }}
        </button>
      </form>
    </section>

    <div v-if="reviewOpen" class="modal-mask">
      <div class="modal">
        <h2>人工审核</h2>
        <p>售后敏感操作需要审核后才能继续回复用户。</p>
        <label>
          审核备注
          <input v-model="reviewNotes" placeholder="可选备注" />
        </label>
        <div class="modal-actions">
          <button type="button" class="ghost" @click="submitReview('拒绝')">
            拒绝
          </button>
          <button type="button" class="send" @click="submitReview('通过')">
            通过
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 40px 20px 64px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 12px;
  color: var(--accent);
  font-family: ui-sans-serif, system-ui, sans-serif;
}

h1 {
  margin: 0;
  font-size: clamp(2.4rem, 6vw, 3.6rem);
  line-height: 0.95;
  font-weight: 600;
}

.sub {
  margin: 12px 0 0;
  max-width: 36rem;
  color: var(--muted);
  font-size: 1.05rem;
}

.meta {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pill {
  padding: 6px 12px;
  border-radius: 999px;
  background: #fee2e2;
  color: var(--danger);
  font-size: 13px;
  font-family: ui-sans-serif, system-ui, sans-serif;
}

.pill[data-ok='true'] {
  background: var(--accent-soft);
  color: var(--accent);
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.messages {
  height: min(58vh, 560px);
  overflow: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bubble {
  max-width: 85%;
  padding: 12px 14px;
  border-radius: 18px;
  background: #f5f1ea;
  border: 1px solid transparent;
}

.bubble[data-role='user'] {
  align-self: flex-end;
  background: var(--user);
  color: #f0fdfa;
}

.bubble[data-role='system'] {
  align-self: center;
  background: transparent;
  border-color: var(--line);
  color: var(--muted);
  font-size: 0.95rem;
}

.role {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 4px;
  font-family: ui-sans-serif, system-ui, sans-serif;
}

.body {
  white-space: pre-wrap;
  line-height: 1.55;
}

.status,
.error {
  padding: 0 24px 12px;
  font-size: 0.92rem;
  font-family: ui-sans-serif, system-ui, sans-serif;
}

.status {
  color: var(--accent);
}

.error {
  color: var(--danger);
}

.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 24px 16px;
}

.quick button,
.ghost,
.send {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-family: ui-sans-serif, system-ui, sans-serif;
}

.quick button:hover:not(:disabled),
.ghost:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.composer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid var(--line);
}

textarea {
  width: 100%;
  resize: none;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 16px;
  background: #fff;
  outline: none;
}

textarea:focus {
  border-color: var(--accent);
}

.send {
  align-self: end;
  background: var(--accent);
  color: white;
  border-color: var(--accent);
  min-width: 96px;
}

.send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(28, 25, 23, 0.35);
  display: grid;
  place-items: center;
  padding: 20px;
}

.modal {
  width: min(420px, 100%);
  background: var(--panel);
  border-radius: 24px;
  padding: 24px;
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.modal h2 {
  margin: 0 0 8px;
}

.modal p {
  margin: 0 0 16px;
  color: var(--muted);
}

.modal label {
  display: grid;
  gap: 8px;
  font-size: 0.92rem;
}

.modal input {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

@media (max-width: 640px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .composer {
    grid-template-columns: 1fr;
  }
}
</style>
