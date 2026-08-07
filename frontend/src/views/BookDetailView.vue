<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍详情页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-settings-btn="false" :show-back-to-shelf="true" />

    <section class="section">
      <div class="container">
        <!-- 加载中 -->
        <div v-if="booksStore.loading && !book" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 不存在 -->
        <div v-else-if="!book && !booksStore.loading" class="empty-state">
          <p>该书籍不存在或已被删除</p>
          <el-button type="primary" style="margin-top:16px" @click="$router.push('/shelf')">返回书架</el-button>
        </div>

        <!-- 详情内容 -->
        <template v-if="book">
          <el-button text style="margin-bottom:16px" @click="$router.push('/shelf')">← 返回书架</el-button>

          <!-- 书籍信息卡片 -->
          <div class="card" style="margin-bottom:24px">
            <div class="detail-header">
              <div style="flex:1">
                <h1 style="font-size:clamp(28px,4vw,36px);font-weight:700">{{ book.title }}</h1>
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

                <!-- 抓取进度 -->
                <div v-if="crawlProgressVisible" style="margin-top:16px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:12px;color:var(--muted)">抓取进度：{{ crawlText }}</span>
                    <span class="num" style="font-size:12px;color:var(--muted)">{{ crawlPercent }}%</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: crawlPercent + '%' }"></div>
                  </div>
                </div>
              </div>

              <BookCover :title="book.title" :author="book.author" />
            </div>
          </div>

          <!-- AI 摘要区块 v1.3 -->
          <div v-if="book" class="card ai-summary-card">
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
              <el-button type="primary" @click="handleGenerateSummary" :loading="aiSummaryLoading" :disabled="!book || book.chapter_count === 0">
                🤖 生成 AI 摘要
              </el-button>
              <p v-if="book && book.chapter_count === 0" style="font-size:11px;color:var(--muted);margin-top:6px">需要先抓取章节内容</p>
            </div>
          </div>

          <!-- 章节目录 v1.2 -->
          <div v-if="chapters.length > 0" class="card">
            <h3 style="margin-bottom:16px;font-size:18px;font-weight:600">章节目录（{{ chapters.length }} 章）</h3>
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
import type { Book, ChapterSummary } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getDownloadUrl, getChapters, getReadingProgress, generateAiSummary, getAiSummary } from '@/api/books'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

const book = ref<Book | null>(null)
const chapters = ref<ChapterSummary[]>([])
const crawling = ref(false)
const crawlProgressVisible = ref(false)
const crawlText = ref('')
const crawlPercent = ref(0)

let crawlTimer: ReturnType<typeof setInterval> | null = null
let summaryPollTimer: ReturnType<typeof setInterval> | null = null

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
  try {
    const result = await booksStore.fetchBookDetail(id)
    book.value = result
    // 加载章节列表 v1.2
    await loadChapters()
    // 检查 AI 摘要 v1.3
    await checkAiSummary(id)
    if (result?.status === 'crawling') {
      startCrawlPolling(id)
    }
  } catch {
    book.value = null
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
        aiSummaryLoading.value = false
        return
      }
      if (data.data.status === 'queued' || data.data.status === 'generating') {
        aiSummaryStatus.value = data.data.status
        startSummaryPolling(book.value.id)
      }
      if (data.data.error) {
        aiSummaryError.value = data.data.error
      }
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
  if (book.value.chapter_count === 0) return
  try {
    const { data } = await getChapters(book.value.id)
    if (data.success && data.data) {
      chapters.value = data.data
    }
  } catch {
    // 章节加载失败不阻塞详情展示
  }
}

onUnmounted(() => {
  stopCrawlPolling()
  stopSummaryPolling()
})

function stopCrawlPolling() {
  if (crawlTimer) {
    clearInterval(crawlTimer)
    crawlTimer = null
  }
}

function startCrawlPolling(bookId: string) {
  crawlProgressVisible.value = true
  stopCrawlPolling()
  crawlTimer = setInterval(async () => {
    try {
      const status = await booksStore.fetchCrawlStatus(bookId)
      if (status) {
        crawlText.value = `${status.chapter_count}/${status.total_chapters ?? '?'} 章`
        crawlPercent.value = Math.round(status.percentage)
        if (book.value) {
          book.value.status = status.status
          book.value.chapter_count = status.chapter_count
        }
        if (status.status === 'done' || status.status === 'failed') {
          stopCrawlPolling()
          if (status.status === 'done') {
            // 重新获取完整的书籍信息（包含 epub/txt 状态和章节数据）
            try {
              const updated = await booksStore.fetchBookDetail(book.value.id)
              if (updated && book.value) {
                book.value = updated
              }
            } catch { /* 刷新失败不阻塞 */ }
            // 刷新章节列表
            loadChapters()
            crawlProgressVisible.value = false
            ElMessage.success('抓取完成！.epub 和 .txt 文件已生成')
          } else {
            // 抓取失败：重新获取书籍信息以恢复正确状态
            try {
              const updated = await booksStore.fetchBookDetail(book.value.id)
              if (updated && book.value) {
                book.value = updated
              }
            } catch { /* 刷新失败不阻塞 */ }
            const errMsg = status.error || '抓取失败，请检查网络后重试'
            ElMessage.error(errMsg)
          }
        }
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
    if (book.value) {
      book.value.status = result.status
    }
    crawlProgressVisible.value = true
    crawlText.value = `0/? 章`
    crawlPercent.value = 0
    startCrawlPolling(book.value.id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || err.message || '触发抓取失败')
  } finally {
    crawling.value = false
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

async function handleDownload(format: 'epub' | 'txt') {
  if (!book.value) return
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const url = getDownloadUrl(book.value.id, format)
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.error || '下载失败')
    }
    const blob = await response.blob()
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `${book.value.title}-${book.value.author}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
    ElMessage.success(`《${book.value.title}》开始下载`)
  } catch (err: any) {
    ElMessage.error(err.message || '下载失败')
  }
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

.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.meta {
  font-size: 12px;
  color: var(--muted);
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
</style>
