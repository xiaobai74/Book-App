<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍详情页面
     v2.4 — 边爬边看：抓取进度改用 SSE 实时推送（失败回退轮询），
           章节目录随抓取实时增长，抓取中即可阅读已就绪章节
     v2.3 — 缓存优先加载：基础信息从书架缓存即时展示，详情/章节/
           AI 摘要按书缓存（books store），书架⇄详情⇄阅读器来回
           切换零等待零重复请求；章节与摘要改为并行加载；
           抓取完成/标记等变更本地同步缓存与书架列表
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-back-to-shelf="true" />

    <section class="section">
      <div class="container">
        <!-- 加载中（仅完全无缓存且正在拉取时展示） -->
        <div v-if="pageLoading && !book" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 不存在 -->
        <div v-else-if="!book && !pageLoading" class="empty-state">
          <p>该书籍不存在或已被删除</p>
          <el-button type="primary" style="margin-top:16px" @click="$router.push('/shelf')">返回书架</el-button>
        </div>

        <!-- 详情内容 -->
        <template v-if="book">
          <el-button text style="margin-bottom:16px" @click="$router.push('/shelf')">← 返回书架</el-button>

          <!-- 书籍信息卡片 -->
          <div class="card" style="margin-bottom:24px">
            <div class="detail-header">
              <div class="detail-info">
                <!-- v1.3 修复: PRD 要求详情页有星标标记按钮（原仅书架列表页可标记） -->
                <h1 style="font-size:clamp(28px,4vw,36px);font-weight:700;display:inline-flex;align-items:center;gap:10px">
                  {{ book.title }}
                  <button
                    class="mark-btn"
                    type="button"
                    :aria-pressed="book.is_marked"
                    :aria-label="book.is_marked ? '取消标记' : '标记此书'"
                    :title="book.is_marked ? '取消标记' : '标记此书'"
                    @click="toggleMark"
                  >
                    <span v-if="book.is_marked" class="star star-filled">★</span>
                    <span v-else class="star star-empty">☆</span>
                  </button>
                </h1>
                <p class="lead" style="margin-top:6px">作者：{{ book.author }}</p>
                <p v-if="book.source_url" style="font-size:12px;color:var(--muted);margin-top:2px">
                  来源：<a :href="book.source_url" target="_blank" rel="noopener">{{ book.source_url }}</a>
                </p>
                <div class="detail-meta" style="margin-top:12px">
                  <span class="meta">添加时间：{{ formatDate(book.added_at) }}</span>
                  <div style="display:flex;align-items:center;gap:8px">
                    <span class="meta">状态：</span>
                    <StatusBadge :status="book.status" />
                  </div>
                  <span class="meta">章节数：<span class="num">{{ book.chapter_count }}</span></span>
                </div>
                <div class="detail-actions">
                  <el-button
                    type="primary"
                    :disabled="book.status === 'crawling'"
                    :loading="crawling"
                    @click="handleCrawl"
                  >
                    {{ book.status === 'done' ? '重新抓取' : '抓取小说内容' }}
                  </el-button>
                  <!-- v1.2: 在线阅读按钮 -->
                  <el-button
                    type="success"
                    :disabled="!book.has_epub && book.chapter_count === 0"
                    @click="startReading"
                  >
                    在线阅读
                  </el-button>
                  <el-dropdown
                    v-if="book.has_epub || book.has_txt"
                    style="vertical-align:middle"
                    @command="handleDownload"
                  >
                    <el-button type="default" :disabled="!book.has_epub && !book.has_txt">
                      下载 <el-icon style="margin-left:4px"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="epub" :disabled="!book.has_epub">
                          .epub 格式
                        </el-dropdown-item>
                        <el-dropdown-item command="txt" :disabled="!book.has_txt">
                          .txt 格式
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <el-button
                    v-else
                    type="default"
                    :disabled="true"
                  >
                    下载
                  </el-button>
                  <el-button @click="$router.push('/shelf')">返回书架</el-button>
                </div>

                <!-- 抓取进度（aria-live：进度变化由读屏软件播报） -->
                <div v-if="crawlProgressVisible" style="margin-top:16px" aria-live="polite">
                  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:12px;color:var(--muted)">抓取进度：{{ crawlText }}</span>
                    <span class="num" style="font-size:12px;color:var(--muted)">{{ crawlPercent }}%</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: crawlPercent + '%' }"></div>
                  </div>
                  <!-- 边爬边看 v1.4：抓取中即可阅读已就绪章节 -->
                  <p v-if="book.status === 'crawling'" style="font-size:12px;color:var(--muted);margin-top:8px">
                    已抓取章节可立即阅读，无需等待全量完成
                    <el-button
                      type="primary"
                      text
                      size="small"
                      :disabled="book.chapter_count === 0"
                      @click="startReading"
                    >
                      立即阅读 →
                    </el-button>
                  </p>
                </div>
              </div>

              <BookCover :title="book.title" :author="book.author" />
            </div>
          </div>

          <!-- AI 摘要区块 v1.3 -->
          <div class="card ai-summary-card">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
              <h3 style="font-size:18px;font-weight:600;margin:0">🤖 AI 摘要</h3>
              <span v-if="aiSummaryAt" style="font-size:12px;color:var(--muted)">{{ formatDate(aiSummaryAt) }}</span>
            </div>

            <!-- 已生成摘要 -->
            <div v-if="aiSummary" class="ai-summary-content">
              <div v-for="(section, i) in aiSummarySections" :key="i" style="margin-bottom:12px">
                <div class="ai-section-title">{{ section.title }}</div>
                <div class="ai-section-body">{{ section.body }}</div>
              </div>
            </div>

            <!-- 生成中 -->
            <div v-else-if="aiSummaryStatus === 'generating' || aiSummaryStatus === 'queued'" style="padding:16px 0">
              <div class="loading-bar"></div>
              <p style="margin-top:8px;font-size:13px;color:var(--muted)">AI 正在分析章节内容，生成摘要中…</p>
            </div>

            <!-- 生成失败 -->
            <div v-else-if="aiSummaryStatus === 'failed'" style="padding:8px 0">
              <p style="font-size:13px;color:var(--danger)">AI 摘要生成失败{{ aiSummaryError ? `：${aiSummaryError}` : '' }}</p>
              <el-button size="small" type="primary" text style="margin-top:4px" @click="handleGenerateSummary" :loading="aiSummaryLoading">
                重试
              </el-button>
            </div>

            <!-- 未生成 - 显示生成按钮 -->
            <div v-else style="padding:8px 0;text-align:center">
              <p style="font-size:13px;color:var(--muted);margin-bottom:12px">让 AI 阅读章节样本，自动生成情节摘要和角色列表</p>
              <el-button type="primary" @click="handleGenerateSummary" :loading="aiSummaryLoading" :disabled="book.chapter_count === 0">
                🤖 生成 AI 摘要
              </el-button>
              <p v-if="book.chapter_count === 0" style="font-size:11px;color:var(--muted);margin-top:6px">需要先抓取章节内容</p>
            </div>
          </div>

          <!-- 章节目录 v1.2（边爬边看 v1.4：抓取中实时增长） -->
          <div v-if="chapters.length > 0" class="card">
            <h3 style="margin-bottom:16px;font-size:18px;font-weight:600">
              章节目录（{{ chapters.length }} 章）
              <span v-if="book.status === 'crawling'" style="font-size:12px;color:var(--muted);font-weight:400;margin-left:8px">抓取中，目录实时更新…</span>
            </h3>
            <div
              v-for="ch in chapters"
              :key="ch.index"
              class="chapter-row clickable"
              @click="openReader(ch.index)"
            >
              <span class="ch-num">第 {{ ch.index }} 章</span>
              <span class="ch-title">{{ ch.title }}</span>
              <span style="font-size:12px;color:var(--muted)">{{ ch.word_count || '—' }} 字</span>
            </div>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import { downloadEbook } from '@/utils/download'
import type { Book, ChapterSummary } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getChapters, getReadingProgress, generateAiSummary, getAiSummary, toggleMarkBook, subscribeCrawlStream } from '@/api/books'
import type { CrawlStreamEvent } from '@/types'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

const book = ref<Book | null>(null)
const chapters = ref<ChapterSummary[]>([])
/** 首次加载且无任何缓存可展示时为 true（v2.3） */
const pageLoading = ref(false)
const crawling = ref(false)
const crawlProgressVisible = ref(false)
const crawlText = ref('')
const crawlPercent = ref(0)

let crawlTimer: ReturnType<typeof setInterval> | null = null
let summaryPollTimer: ReturnType<typeof setInterval> | null = null
/** 边爬边看 v1.4：SSE 订阅取消函数与章节列表防抖重载定时器 */
let stopCrawlStream: (() => void) | null = null
let chapterReloadTimer: ReturnType<typeof setTimeout> | null = null

// ── AI 摘要状态 v1.3 ────────────────────────────────
const aiSummary = ref<string | null>(null)
const aiSummaryAt = ref<string | null>(null)
const aiSummaryStatus = ref<string | null>(null)
const aiSummaryError = ref<string | null>(null)
const aiSummaryLoading = ref(false)

/** 将摘要文本解析为段落（按【xxx】分割） */
const aiSummarySections = computed(() => {
  if (!aiSummary.value) return []
  const raw = aiSummary.value
  // 匹配所有【标题】模式
  const matches = [...raw.matchAll(/【([^】]+)】/g)]
  if (matches.length === 0) {
    // 无【】标记 — 将全部文本作为单一段落
    return raw.trim() ? [{ title: '摘要', body: raw.trim() }] : []
  }

  return matches.map((match, i) => {
    const title = match[1]
    const bodyStart = (match.index ?? 0) + match[0].length
    const bodyEnd = i + 1 < matches.length ? (matches[i + 1].index ?? raw.length) : raw.length
    const body = raw.substring(bodyStart, bodyEnd).trim()
    return { title, body }
  }).filter(s => s.body || s.title)
})

onMounted(async () => {
  const id = route.params.id as string
  if (!id) {
    book.value = null
    return
  }

  // v2.3 缓存优先：基础信息从书架缓存恢复、章节从详情缓存恢复、
  // 已生成的摘要直接展示——命中即瞬间展示，零请求
  const cached = booksStore.getCachedDetail(id)
  book.value = cached?.book ?? booksStore.findShelfBook(id)
  if (cached) chapters.value = cached.chapters

  const cachedSummary = booksStore.getCachedSummary(id)
  if (cachedSummary) {
    aiSummary.value = cachedSummary.text
    aiSummaryAt.value = cachedSummary.at
    aiSummaryStatus.value = 'done'
  }

  if (cached) {
    // 详情缓存命中：不重复请求（抓取完成/标记等变更已本地同步缓存）
    if (cached.book.status === 'crawling') startCrawlWatch(id)
    if (!cachedSummary) checkAiSummary(id)  // 摘要未缓存时补一次
    return
  }

  // 无详情缓存：后台静默拉取（基础信息已展示时不显示骨架）
  pageLoading.value = true
  try {
    const result = await booksStore.fetchBookDetail(id, true)
    if (result) book.value = result
    if (result?.status === 'crawling') {
      startCrawlWatch(id)
    }
    // 章节列表与 AI 摘要并行加载（原为串行三连请求）
    await Promise.all([
      loadChapters(),
      cachedSummary ? Promise.resolve() : checkAiSummary(id)
    ])
  } catch {
    // 拉取失败时 book 保持 null，模板展示「不存在」状态
  } finally {
    pageLoading.value = false
  }
})

/** 检查是否已有 AI 摘要 */
async function checkAiSummary(bookId: string) {
  try {
    const { data } = await getAiSummary(bookId)
    if (data.success && data.data) {
      if (data.data.ai_summary) {
        aiSummary.value = data.data.ai_summary
        aiSummaryAt.value = data.data.ai_summary_at || null
        aiSummaryStatus.value = 'done'
        booksStore.cacheSummary(bookId, data.data.ai_summary, data.data.ai_summary_at || null)
      } else if (data.data.status === 'generating' || data.data.status === 'queued') {
        aiSummaryStatus.value = data.data.status
        startSummaryPolling(bookId)
      } else {
        aiSummaryStatus.value = data.data.status || 'none'
      }
    }
  } catch {
    aiSummaryStatus.value = 'none'
  }
}

/** 触发 AI 摘要生成 */
async function handleGenerateSummary() {
  if (!book.value) return
  aiSummaryLoading.value = true
  aiSummaryStatus.value = 'queued'
  aiSummaryError.value = null
  try {
    const { data } = await generateAiSummary(book.value.id)
    if (data.success && data.data) {
      if (data.data.status === 'done') {
        aiSummary.value = data.data.ai_summary || null
        aiSummaryAt.value = data.data.ai_summary_at || null
        aiSummaryStatus.value = 'done'
        if (data.data.ai_summary) {
          booksStore.cacheSummary(book.value.id, data.data.ai_summary, data.data.ai_summary_at || null)
        }
        return
      }
      if (data.data.status === 'queued' || data.data.status === 'generating') {
        aiSummaryStatus.value = data.data.status
        startSummaryPolling(book.value.id)
      }
      if (data.data.error) {
        aiSummaryError.value = data.data.error
      }
    } else {
      // 请求成功但业务失败：置为 failed，避免界面永久停留在"生成中"
      aiSummaryStatus.value = 'failed'
      aiSummaryError.value = data.error || '请求失败'
    }
  } catch (err: any) {
    aiSummaryStatus.value = 'failed'
    aiSummaryError.value = err?.response?.data?.error || err.message || '请求失败'
  } finally {
    aiSummaryLoading.value = false
  }
}

/** 轮询摘要生成进度 */
function startSummaryPolling(bookId: string) {
  stopSummaryPolling()
  let pollCount = 0
  const MAX_POLLS = 100  // 最多轮询 5 分钟（100 × 3s），防止无限轮询
  summaryPollTimer = setInterval(async () => {
    pollCount++
    try {
      const { data } = await getAiSummary(bookId)
      if (data.success && data.data) {
        if (data.data.status === 'done' && data.data.ai_summary) {
          aiSummary.value = data.data.ai_summary
          aiSummaryAt.value = data.data.ai_summary_at || null
          aiSummaryStatus.value = 'done'
          booksStore.cacheSummary(bookId, data.data.ai_summary, data.data.ai_summary_at || null)
          stopSummaryPolling()
        } else if (data.data.status === 'failed') {
          aiSummaryStatus.value = 'failed'
          aiSummaryError.value = data.data.error || '生成失败'
          stopSummaryPolling()
        } else if (data.data.status === 'none') {
          // 服务重启后内存状态丢失，任务已失效
          aiSummaryStatus.value = 'failed'
          aiSummaryError.value = '生成任务已失效（可能服务重启），请重新触发'
          stopSummaryPolling()
        } else if (pollCount >= MAX_POLLS) {
          // 超时保护：超过最大轮询次数仍未完成
          aiSummaryStatus.value = 'failed'
          aiSummaryError.value = 'AI 摘要生成超时，请稍后重试'
          stopSummaryPolling()
        } else {
          aiSummaryStatus.value = data.data.status
        }
      }
    } catch {
      // 轮询静默失败
    }
  }, 3000)
}

function stopSummaryPolling() {
  if (summaryPollTimer) {
    clearInterval(summaryPollTimer)
    summaryPollTimer = null
  }
}

async function loadChapters() {
  if (!book.value) return
  if (book.value.chapter_count === 0) {
    // 无章节也写缓存（避免下次进入重复判断/请求）
    booksStore.cacheDetail(book.value.id, book.value, [])
    return
  }
  try {
    const { data } = await getChapters(book.value.id)
    if (data.success && data.data) {
      chapters.value = data.data
      booksStore.cacheDetail(book.value.id, book.value, data.data)
    }
  } catch {
    // 章节加载失败不阻塞详情展示
  }
}

onUnmounted(() => {
  stopCrawlWatch()
  stopCrawlPolling()
  stopSummaryPolling()
})

function stopCrawlPolling() {
  if (crawlTimer) {
    clearInterval(crawlTimer)
    crawlTimer = null
  }
}

// ── 边爬边看 v1.4：SSE 实时推送（轮询仅作回退） ────────────

function stopCrawlWatch() {
  if (stopCrawlStream) {
    stopCrawlStream()
    stopCrawlStream = null
  }
  if (chapterReloadTimer) {
    clearTimeout(chapterReloadTimer)
    chapterReloadTimer = null
  }
}

/** 防抖重载章节列表：chapter_ready 高频事件下避免频繁请求 */
function scheduleChapterReload() {
  if (chapterReloadTimer) return
  chapterReloadTimer = setTimeout(() => {
    chapterReloadTimer = null
    loadChapters()
  }, 1500)
}

/** 订阅抓取事件流；连接失败自动回退到 v1.3 轮询 */
function startCrawlWatch(bookId: string) {
  crawlProgressVisible.value = true
  stopCrawlWatch()
  stopCrawlPolling()
  let fellBack = false
  stopCrawlStream = subscribeCrawlStream(bookId, (ev) => {
    if (ev.type === 'stream_error') {
      if (!fellBack) {
        fellBack = true
        stopCrawlStream = null
        startCrawlPolling(bookId)
      }
      return
    }
    handleCrawlEvent(bookId, ev)
  })
}

function handleCrawlEvent(bookId: string, ev: CrawlStreamEvent) {
  // 缓存当前书籍引用：异步回调中 book.value 的窄化会失效（TS18047）
  const current = book.value
  switch (ev.type) {
    case 'snapshot':
      if (ev.status === 'none') {
        // 订阅时任务已结束：回退轮询从 DB 确认终态
        stopCrawlWatch()
        startCrawlPolling(bookId)
        return
      }
      if (current) current.status = 'crawling'
      crawlText.value = `${ev.current ?? 0}/${ev.total ?? '?'} 章`
      crawlPercent.value = Math.round(ev.percentage ?? 0)
      break
    case 'plan':
      // 用事件携带的实时进度，避免拼接本地过期的 chapter_count
      crawlText.value = `${ev.current ?? 0}/${ev.total ?? '?'} 章`
      break
    case 'chapter_ready':
      if (current) {
        current.status = 'crawling'
        current.chapter_count = ev.current ?? current.chapter_count
      }
      crawlText.value = `${ev.current ?? 0}/${ev.total ?? '?'} 章`
      crawlPercent.value = Math.round(ev.percentage ?? 0)
      scheduleChapterReload()  // 目录实时增长
      break
    case 'done':
      stopCrawlWatch()
      stopCrawlPolling()
      crawlProgressVisible.value = false
      if (current) {
        // 刷新书籍信息并重载章节列表（内部同步详情缓存与书架）
        refreshBook(current).then(() => loadChapters())
        ElMessage.success('抓取完成！.epub 和 .txt 文件已生成')
      }
      break
    case 'failed':
      stopCrawlWatch()
      stopCrawlPolling()
      if (current) refreshBook(current)
      ElMessage.error(ev.error || '抓取失败，请检查网络后重试')
      break
  }
}

/** 抓取结束后重新拉取完整书籍信息并同步书架列表（done/failed 共用） */
async function refreshBook(current: Book) {
  try {
    const updated = await booksStore.fetchBookDetail(current.id, true)
    if (updated && book.value) {
      book.value = updated
      // v2.3：同步回书架列表（章节数/epub 状态变更）
      booksStore.upsertShelfBook(updated)
    }
  } catch { /* 刷新失败不阻塞 */ }
}

function startCrawlPolling(bookId: string) {
  crawlProgressVisible.value = true
  stopCrawlPolling()
  crawlTimer = setInterval(async () => {
    try {
      const status = await booksStore.fetchCrawlStatus(bookId)
      if (!status) return
      crawlText.value = `${status.chapter_count}/${status.total_chapters ?? '?'} 章`
      crawlPercent.value = Math.round(status.percentage)
      // 缓存当前书籍引用：异步回调中 book.value 的窄化会失效（TS18047）
      const current = book.value
      if (current) {
        current.status = status.status
        current.chapter_count = status.chapter_count
      }
      if (status.status !== 'done' && status.status !== 'failed') return
      stopCrawlPolling()
      if (!current) return
      await refreshBook(current)
      if (status.status === 'done') {
        // 刷新章节列表（内部同步详情缓存）
        await loadChapters()
        crawlProgressVisible.value = false
        ElMessage.success('抓取完成！.epub 和 .txt 文件已生成')
      } else {
        // 抓取失败：refreshBook 已恢复正确状态，仅提示错误
        ElMessage.error(status.error || '抓取失败，请检查网络后重试')
      }
    } catch {
      // 轮询失败不中断
    }
  }, 2000)
}

async function handleCrawl() {
  if (!book.value) return
  crawling.value = true
  try {
    const result = await booksStore.startCrawl(book.value.id)
    book.value.status = result.status
    crawlProgressVisible.value = true
    crawlText.value = `0/? 章`
    crawlPercent.value = 0
    startCrawlWatch(book.value.id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || err.message || '触发抓取失败')
  } finally {
    crawling.value = false
  }
}

// ── 星标标记 v1.3 修复（PRD 4 章信息架构要求详情页有标记按钮） ──
async function toggleMark() {
  if (!book.value) return
  try {
    const { data } = await toggleMarkBook(book.value.id)
    if (data.success && data.data) {
      book.value = data.data
      // v2.3：同步回书架列表并重排（标记置顶），同时更新详情缓存
      booksStore.upsertShelfBook(data.data)
      booksStore.resortLists()
      booksStore.cacheDetail(data.data.id, data.data, chapters.value)
      ElMessage.success(data.data.is_marked ? '已标记' : '已取消标记')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || err.message || '操作失败')
  }
}

// ─── v1.2: 在线阅读 ────────────────────────────────────

async function startReading() {
  if (!book.value) return
  // 尝试恢复上次阅读进度
  try {
    const { data } = await getReadingProgress(book.value.id)
    if (data.success && data.data && data.data.last_chapter_index) {
      router.push(`/reader/${book.value.id}/${data.data.last_chapter_index}`)
      return
    }
  } catch { /* 使用默认值 */ }
  router.push(`/reader/${book.value.id}/1`)
}

function openReader(chapterIndex: number) {
  if (!book.value) return
  router.push(`/reader/${book.value.id}/${chapterIndex}`)
}

function handleDownload(format: 'epub' | 'txt') {
  if (!book.value) return
  downloadEbook(book.value.id, format, `${book.value.title}-${book.value.author}`, `《${book.value.title}》开始下载`)
}
</script>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
}

.lead { font-size: 15px; color: var(--muted); max-width: 52ch; }

.detail-info { flex: 1; }

.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.meta {
  font-size: 12px;
  color: var(--muted);
}

/* ── 星标标记按钮（与书架页一致，v1.4：暖金 + WCAG 2.5.8 目标尺寸） ── */
.mark-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  min-width: 32px;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.mark-btn:hover .star-empty {
  color: var(--accent-warm);
}

.star {
  font-size: 26px;
  line-height: 1;
}

.star-empty {
  color: var(--muted);
}

.star-filled {
  color: var(--accent-warm);
}

/* ── AI 摘要 v1.3 ──────────────────────────────────── */
.ai-summary-card {
  border-left: 3px solid var(--accent-ice);
}

.ai-summary-content {
  line-height: 1.7;
}

.ai-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--fg);
  margin-bottom: 4px;
}

.ai-section-body {
  font-size: 14px;
  color: var(--fg-soft);
  white-space: pre-wrap;
}

/* ── v1.5 移动端适配 ────────────────────────────── */
@media (max-width: 640px) {
  .card {
    padding: 16px;
  }

  /* 封面在信息下方居中，避免与标题抢宽度 */
  .detail-header {
    flex-direction: column-reverse;
    align-items: center;
    gap: 20px;
  }
  .detail-info {
    width: 100%;
  }

  /* 操作按钮组收紧间距、允许换行 */
  .detail-actions {
    gap: 8px;
  }
  .detail-actions :deep(.el-button) {
    margin: 0;
  }

  /* 章节行：字数列换行到标题下，标题不折行 */
  .chapter-row {
    flex-wrap: wrap;
    gap: 4px 0;
  }
  .chapter-row .ch-title {
    flex: 0 1 100%;
    order: 3;
    padding: 0;
  }
  .chapter-row .ch-num {
    min-width: 0;
  }
}
</style>
