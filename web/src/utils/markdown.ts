import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true,
})

/** 将 Markdown 转为安全 HTML（流式过程中也可反复调用） */
export function renderMarkdown(source: string): string {
  if (!source) return ''
  const dirty = md.render(source)
  return DOMPurify.sanitize(dirty, {
    USE_PROFILES: { html: true },
  })
}
