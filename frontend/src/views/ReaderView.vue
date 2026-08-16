<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 在线阅读器页面 (v1.2 新增)
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div class="reader-root" :class="{ 'night-mode': isNightMode }">
    <!-- 顶部导航栏 -->
    <header class="reader-header">
      <div class="reader-header-left">
        <el-button text @click="goBack">← 返回详情</el-button>
      </div>
      <div class="reader-header-center">
        <span class="chapter-label">第 {{ currentIndex }} 章</span>
        <span class="chapter-title-text">{{ chapter?.title || '加载中…' }}</span>
      </div>
      <div class="reader-header-right">
        <el-button text @click="toggleToc">目录</el-button>
        <el-button text @click="toggleNightMode">
          {{ isNightMode ? '日间' : '夜间' }}
        </el-button>
        <el-dropdown trigger="click" @command="handleFontSize">
          <el-button text>字号</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="small">小</el-dropdown-item>
              <el-dropdown-item command="medium">中</el-dropdown-item>
              <el-dropdown-item command="large">大</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- 行间距调节（PRD READER-006 要求独立可调） -->
        <el-dropdown trigger="click" @command="handleLineHeight">
          <el-button text>行距</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="compact">紧凑</el-dropdown-item>
              <el-dropdown-item command="normal">标准</el-dropdown-item>
              <el-dropdown-item command="relaxed">宽松</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 正文区域 -->
    <main class="reader-body" :style="{ fontSize: fontSizePx + 'px', lineHeight: lineHeight }">
      <div v-if="loading" class="reader-loading">
        <div class="loading-bar"></div>
        <p style="margin-top:12px;color:var(--muted)">加载章节内容…</p>
      </div>

      <div v-else-if="errorMsg" class="reader-error">
        <p>{{ errorMsg }}</p>
        <el-button type="primary" style="margin-top:16px" @click="fetchChapter">重试</el-button>
      </div>

      <div v-else class="reader-content">
        <h2 class="reader-chapter-heading">{{ chapter?.title }}</h2>
        <div class="reader-text" v-html="renderedContent"></div>
      </div>
    </main>

    <!-- 底部导航栏 -->
    <footer class="reader-footer">
      <el-button
        :disabled="currentIndex <= 1"
        @click="prevChapter"
      >
        ← 上一章
      </el-button>
      <span class="reader-progress">
        {{ currentIndex }} / {{ totalChapters || '?' }}
      </span>
      <el-button
        :disabled="currentIndex >= totalChapters"
        @click="nextChapter"
      >
        下一章 →
      </el-button>
    </footer>

    <!-- 目录侧边抽屉 -->
    <el-drawer
      v-model="tocVisible"
      title="章节目录"
      direction="ltr"
      size="320px"
    >
      <div v-if="tocLoading" style="text-align:center;padding:24px">
        <div class="loading-bar"></div>
        <p style="margin-top:12px;color:var(--muted)">加载目录…</p>
      </div>
      <div v-else class="toc-list">
        <div
          v-for="ch in chapters"
          :key="ch.index"
          class="toc-item"
          :class="{ 'toc-active': ch.index === currentIndex }"
          @click="jumpToChapter(ch.index)"
        >
          <span class="toc-num">第 {{ ch.index }} 章</span>
          <span class="toc-title">{{ ch.title }}</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getChapterContent, getChapters, updateReadingProgress, getReadingProgress } from '@/api/books'
import { recordRecentBook } from '@/utils/recentBooks'
import type { ChapterSummary, ChapterDetail } from '@/types'

const route = useRoute()
const router = useRouter()

const bookId = computed(() => route.params.id as string)
const currentIndex = ref(Number(route.params.chapterIndex) || 1)
const totalChapters = ref(0)

const chapter = ref<ChapterDetail | null>(null)
const chapters = ref<ChapterSummary[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

// ─── 阅读设置 ────────────────────────────────────
const FONT_SIZES = ['small', 'medium', 'large'] as const
type FontSize = typeof FONT_SIZES[number]

const isNightMode = ref(localStorage.getItem('reader_nightMode') === 'true')
const fontSize = ref<FontSize>(
  (FONT_SIZES as readonly string[]).includes(localStorage.getItem('reader_fontSize') ?? '')
    ? (localStorage.getItem('reader_fontSize') as FontSize)
    : 'medium'
)

// ── 行间距设置（独立调节，与字号解耦） ─────────────
const LINE_HEIGHTS = ['compact', 'normal', 'relaxed'] as const
type LineHeightOption = typeof LINE_HEIGHTS[number]
const lineHeightOption = ref<LineHeightOption>(
  (LINE_HEIGHTS as readonly string[]).includes(localStorage.getItem('reader_lineHeight') ?? '')
    ? (localStorage.getItem('reader_lineHeight') as LineHeightOption)
    : 'normal'
)

const fontSizeMap: Record<FontSize, number> = { small: 14, medium: 16, large: 20 }
const fontSizePx = computed(() => fontSizeMap[fontSize.value])
const lineHeightMap: Record<LineHeightOption, string> = {
  compact: '1.5',
  normal: '1.8',
  relaxed: '2.2'
}
const lineHeight = computed(() => lineHeightMap[lineHeightOption.value])

function handleFontSize(size: string) {
  if (!(FONT_SIZES as readonly string[]).includes(size)) return
  fontSize.value = size as FontSize
  localStorage.setItem('reader_fontSize', size)
}

function handleLineHeight(option: string) {
  if (!(LINE_HEIGHTS as readonly string[]).includes(option)) return
  lineHeightOption.value = option as LineHeightOption
  localStorage.setItem('reader_lineHeight', option)
}

function toggleNightMode() {
  isNightMode.value = !isNightMode.value
  localStorage.setItem('reader_nightMode', String(isNightMode.value))
}

// ─── 目录 ────────────────────────────────────
const tocVisible = ref(false)
const tocLoading = ref(false)

function toggleToc() {
  tocVisible.value = !tocVisible.value
  if (tocVisible.value && chapters.value.length === 0) {
    loadToc()
  }
}

async function loadToc() {
  tocLoading.value = true
  try {
    const { data } = await getChapters(bookId.value)
    if (data.success && data.data) {
      chapters.value = data.data
      totalChapters.value = data.data.length
    }
  } catch {
    ElMessage.error('加载目录失败')
  } finally {
    tocLoading.value = false
  }
}

function jumpToChapter(index: number) {
  tocVisible.value = false
  if (index === currentIndex.value) return
  currentIndex.value = index
  router.replace(`/reader/${bookId.value}/${index}`)
  fetchChapter()
}

// ─── 内容渲染 ────────────────────────────────────
const renderedContent = computed(() => {
  if (!chapter.value?.content) return ''
  return chapter.value.content
    .split('\n')
    .map(line => line.trim() ? `<p>${escapeHtml(line)}</p>` : '<br>')
    .join('')
})

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// 请求序号：快速翻章时丢弃过期响应，防止旧章节内容覆盖新章节
let fetchSeq = 0

async function fetchChapter() {
  const seq = ++fetchSeq
  const index = currentIndex.value
  loading.value = true
  errorMsg.value = null
  try {
    const { data } = await getChapterContent(bookId.value, index)
    if (seq !== fetchSeq) return  // 已有更新的请求，丢弃过期响应
    if (data.success && data.data) {
      chapter.value = data.data
      // 更新进度
      updateReadingProgress(bookId.value, index).catch(() => {})
      // 滚动到顶部
      window.scrollTo({ top: 0, behavior: 'auto' })
    } else {
      errorMsg.value = data.error || '章节加载失败'
    }
  } catch (err: any) {
    if (seq !== fetchSeq) return
    errorMsg.value = err?.response?.data?.error || err.message || '章节加载失败'
  } finally {
    if (seq === fetchSeq) {
      loading.value = false
    }
  }
}

function prevChapter() {
  if (currentIndex.value <= 1) return
  currentIndex.value--
  router.replace(`/reader/${bookId.value}/${currentIndex.value}`)
  fetchChapter()
}

function nextChapter() {
  if (currentIndex.value >= totalChapters.value) return
  currentIndex.value++
  router.replace(`/reader/${bookId.value}/${currentIndex.value}`)
  fetchChapter()
}

function goBack() {
  router.push(`/detail/${bookId.value}`)
}

// ─── 键盘导航 ────────────────────────────────────
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') prevChapter()
  else if (e.key === 'ArrowRight') nextChapter()
}

onMounted(async () => {
  // 记录最近阅读（供 Ctrl+K 命令面板"最近阅读"入口使用）
  recordRecentBook(bookId.value)
  // 先获取章节列表以确定总数（修复：统一走 loadToc，避免两处重复请求）
  try {
    await loadToc()
  } catch { /* 不影响阅读 */ }

  // 若未指定章节号，尝试恢复上次进度
  if (!route.params.chapterIndex || Number(route.params.chapterIndex) < 1) {
    try {
      const { data: progData } = await getReadingProgress(bookId.value)
      if (progData.success && progData.data) {
        currentIndex.value = progData.data.last_chapter_index || 1
        router.replace(`/reader/${bookId.value}/${currentIndex.value}`)
      }
    } catch { /* 使用默认值 */ }
  }

  fetchChapter()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

// 监听路由参数变化（浏览器前进/后退、手动修改 URL 时）。
// 翻章函数内部已显式 fetch，此处 n === currentIndex 时跳过，避免重复请求。
watch(() => route.params.chapterIndex, (newVal) => {
  const n = Number(newVal)
  if (Number.isFinite(n) && n >= 1 && n !== currentIndex.value) {
    currentIndex.value = n
    fetchChapter()
  }
})
</script>

<style scoped>
/* ── 根容器 ──────────────────────────────────── */
.reader-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  transition: background 0.3s, color 0.3s;
}

/* ── 夜间模式 ──────────────────────────────────── */
.reader-root.night-mode {
  --reader-bg: #1a2332;
  --reader-text: #cbd5e1;
  --reader-heading: #e2e8f0;
  --reader-border: #2d3a4a;
  background: var(--reader-bg);
  color: var(--reader-text);
}

.night-mode .reader-header,
.night-mode .reader-footer {
  background: #141d2a;
  border-color: var(--reader-border);
}

.night-mode .reader-content {
  color: var(--reader-text);
}

.night-mode .reader-chapter-heading {
  color: var(--reader-heading);
}

/* ── 顶部导航栏 ──────────────────────────────────── */
.reader-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  gap: 12px;
  flex-wrap: wrap;
}

.reader-header-left,
.reader-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.reader-header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.chapter-label {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chapter-title-text {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}

/* ── 正文区域 ──────────────────────────────────── */
.reader-body {
  flex: 1;
  padding: 32px 24px 48px;
  max-width: 780px;
  width: 100%;
  margin: 0 auto;
}

.reader-loading,
.reader-error {
  text-align: center;
  padding: 80px 24px;
}

.reader-chapter-heading {
  font-size: 1.5em;
  font-weight: 700;
  margin-bottom: 32px;
  text-align: center;
  color: var(--text);
}

.reader-text {
  font-size: inherit;
  text-align: justify;
  word-break: break-word;
}

.reader-text :deep(p) {
  margin: 0 0 1.2em 0;
  text-indent: 2em;
}

/* ── 底部导航栏 ──────────────────────────────────── */
.reader-footer {
  position: sticky;
  bottom: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--surface);
  border-top: 1px solid var(--border);
}

.reader-progress {
  font-size: 13px;
  color: var(--muted);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ── 目录 ──────────────────────────────────── */
.toc-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.toc-item:hover {
  background: var(--hover);
}

.toc-active {
  background: var(--accent-ice);
  color: #fff;
}

.toc-active:hover {
  background: var(--accent-ice);
}

.toc-num {
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
  min-width: 48px;
}

.toc-active .toc-num {
  color: rgba(255,255,255,0.7);
}

.toc-title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 响应式 ──────────────────────────────────── */
@media (max-width: 640px) {
  .reader-body {
    padding: 20px 14px 36px;
  }
  .reader-header {
    padding: 8px 12px;
  }
  .reader-footer {
    padding: 10px 14px;
  }
}
</style>
