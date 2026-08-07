<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import {
  Button,
  Input,
  Segmented,
  Space,
  Tag,
  Typography,
  message,
} from 'ant-design-vue'
import {
  ClearOutlined,
  RobotOutlined,
  SendOutlined,
  ReadOutlined,
} from '@ant-design/icons-vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import MarkdownBody from '@/components/MarkdownBody.vue'

const { Title, Paragraph, Text } = Typography
const TextArea = Input.TextArea

const store = useChatStore()
const {
  mode,
  messages,
  input,
  loading,
  health,
  quickPrompts,
  sessionId,
} = storeToRefs(store)

const listRef = ref<HTMLElement | null>(null)

async function scrollBottom() {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

watch(
  messages,
  () => {
    void scrollBottom()
  },
  { deep: true },
)

onMounted(async () => {
  await store.refreshHealth()
  if (health.value === 'down') {
    message.warning('后端未连通，请先启动 FastAPI :8000')
  }
})

function onSend() {
  void store.send()
}

function onQuick(text: string) {
  void store.send(text)
}

function onPressEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    e.preventDefault()
    onSend()
  }
}
</script>

<template>
  <div class="min-h-screen px-4 py-6 md:px-8 md:py-10">
    <div class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col">
      <header class="mb-6">
        <p class="mb-2 text-sm tracking-[0.2em] text-teal-800/70 uppercase">
          Note Assistant
        </p>
        <Title
          :level="1"
          class="!mb-2 !text-[2.4rem] !leading-tight !text-slate-900"
        >
          学习笔记助手
        </Title>
        <Paragraph class="!mb-0 max-w-2xl !text-base !text-slate-600">
          对接 note_assistant：Agent 可管理笔记，RAG 基于笔记问答。请先启动后端
          <Text code>uvicorn api.main:app --reload --port 8000</Text>
        </Paragraph>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <Tag
            :color="
              health === 'ok' ? 'success' : health === 'down' ? 'error' : 'default'
            "
          >
            API
            {{
              health === 'ok' ? '正常' : health === 'down' ? '未连接' : '检测中'
            }}
          </Tag>
          <Tag v-if="sessionId" color="processing">
            session: {{ sessionId.slice(0, 8) }}…
          </Tag>
          <Button size="small" @click="store.refreshHealth()">刷新状态</Button>
        </div>
      </header>

      <section
        class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-[#d6d0c4] bg-[#fbf8f2]/95"
      >
        <div
          class="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5dfd3] px-4 py-3"
        >
          <Segmented
            v-model:value="mode"
            :options="[
              { label: 'Agent 模式', value: 'agent' },
              { label: 'RAG 模式', value: 'rag' },
            ]"
          />
          <Space>
            <Text type="secondary" class="hidden md:inline">
              {{
                mode === 'agent' ? '可增删改查笔记' : '仅笔记检索问答，更快'
              }}
            </Text>
            <Button class="!inline-flex !items-center" @click="store.clearChat()">
              <template #icon><ClearOutlined /></template>
              清空
            </Button>
          </Space>
        </div>

        <div
          ref="listRef"
          class="flex-1 space-y-4 overflow-y-auto px-4 py-5 md:px-6"
        >
          <div
            v-for="item in messages"
            :key="item.id"
            class="flex"
            :class="item.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-7"
              :class="{
                'bg-teal-800 text-teal-50': item.role === 'user',
                'border border-[#e2dccf] bg-white text-slate-800':
                  item.role === 'assistant',
                'border border-dashed border-[#cfc7b8] bg-transparent text-slate-500':
                  item.role === 'system',
              }"
            >
              <div class="mb-1 flex items-center gap-2 text-xs opacity-70">
                <RobotOutlined v-if="item.role === 'assistant'" />
                <ReadOutlined v-else-if="item.role === 'system'" />
                <span>
                  {{
                    item.role === 'user'
                      ? '我'
                      : item.role === 'system'
                        ? '系统'
                        : item.mode === 'rag'
                          ? 'RAG'
                          : 'Agent'
                  }}
                </span>
              </div>
              <MarkdownBody :content="item.content" :tone="item.role" />
            </div>
          </div>
          <div
            v-if="loading && messages[messages.length - 1]?.content === ''"
            class="text-sm text-slate-500"
          >
            助手思考中…
          </div>
        </div>

        <div class="border-t border-[#e5dfd3] px-4 py-4 md:px-6">
          <div class="mb-3 flex flex-wrap gap-2">
            <Button
              v-for="prompt in quickPrompts"
              :key="prompt"
              size="small"
              :disabled="loading"
              @click="onQuick(prompt)"
            >
              {{ prompt }}
            </Button>
          </div>
          <div class="flex items-end gap-3">
            <TextArea
              v-model:value="input"
              :rows="2"
              :disabled="loading"
              placeholder="输入问题，例如：什么是 RAG / 列出所有笔记"
              class="!rounded-xl"
              @pressEnter="(e) => onPressEnter(e as KeyboardEvent)"
            />
            <Button
              type="primary"
              size="large"
              class="!inline-flex !items-center !bg-teal-800 hover:!bg-teal-700"
              :loading="loading"
              @click="onSend"
            >
              <template #icon><SendOutlined /></template>
              发送
            </Button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
