<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
  tone?: 'user' | 'assistant' | 'system'
}>()

const html = computed(() => renderMarkdown(props.content))
</script>

<template>
  <div
    class="md-body"
    :class="{
      'md-body--user': tone === 'user',
      'md-body--assistant': tone === 'assistant' || !tone,
      'md-body--system': tone === 'system',
    }"
    v-html="html"
  />
</template>
