/* ═══════════════════════════════════════════════════════
   小说管理App · 排行榜共享状态 (Pinia)
   抓取结果缓存于本 store：切换页面再回来不会重新抓取，
   只有用户主动点击「刷新列表 / 刷新榜单」才发起新请求
   （榜单刷新携带 refresh=true 同时跳过后端 15 分钟缓存）。
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getRankingSources, getRankingBoard } from '@/api/ranking'
import type { RankingSource, RankingBoardData } from '@/types'

export const useRankingStore = defineStore('ranking', () => {
  // ── 源站列表 ─────────────────────────────────────
  const sources = ref<RankingSource[]>([])
  const sourcesLoaded = ref(false)
  const loadingSources = ref(false)

  // ── 页面状态（切换页面后恢复） ────────────────────
  /** 当前选中的源站 id（null = 源站选择态） */
  const selectedSourceId = ref<number | null>(null)
  /** 当前浏览的榜单索引 */
  const activeBoard = ref(0)
  /** 榜单结果缓存：`${sourceId}:${boardIndex}` → 抓取结果 */
  const boardCache = ref<Record<string, RankingBoardData>>({})
  const loadingBoard = ref(false)
  const boardError = ref('')

  const selectedSource = computed<RankingSource | null>(
    () => sources.value.find((s) => s.id === selectedSourceId.value) ?? null
  )
  const currentBoard = computed<RankingBoardData | null>(() => {
    if (selectedSourceId.value === null) return null
    return boardCache.value[`${selectedSourceId.value}:${activeBoard.value}`] ?? null
  })

  /** 加载源站列表；已加载过则跳过，force=true（用户点击刷新）才重新请求 */
  async function loadSources(force = false) {
    if (sourcesLoaded.value && !force) return
    loadingSources.value = true
    try {
      const res = await getRankingSources()
      sources.value = res.data?.data ?? []
      sourcesLoaded.value = true
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.error || e?.message || '获取源站列表失败')
    } finally {
      loadingSources.value = false
    }
  }

  /** 选中源站进入榜单浏览态（若该源站榜单已缓存则不会重新抓取） */
  function selectSource(s: RankingSource) {
    selectedSourceId.value = s.id
    activeBoard.value = 0
    boardError.value = ''
  }

  /** 返回源站选择态（保留已抓取结果） */
  function backToSources() {
    selectedSourceId.value = null
    boardError.value = ''
  }

  /**
   * 加载指定榜单：已缓存直接复用（不发请求）；
   * force=true（用户点击刷新榜单）携带 refresh 跳过后端缓存重新抓取。
   */
  async function loadBoard(boardIndex: number, force = false) {
    if (selectedSourceId.value === null) return
    activeBoard.value = boardIndex
    const key = `${selectedSourceId.value}:${boardIndex}`
    if (!force && boardCache.value[key]) {
      boardError.value = ''
      return
    }
    loadingBoard.value = true
    boardError.value = ''
    try {
      const res = await getRankingBoard(selectedSourceId.value, boardIndex, force)
      if (res.data?.data) {
        boardCache.value[key] = res.data.data
      }
    } catch (e: any) {
      boardError.value = e?.response?.data?.error || e?.message || '榜单抓取失败，请稍后重试'
    } finally {
      loadingBoard.value = false
    }
  }

  return {
    sources,
    sourcesLoaded,
    loadingSources,
    selectedSourceId,
    activeBoard,
    boardCache,
    loadingBoard,
    boardError,
    selectedSource,
    currentBoard,
    loadSources,
    selectSource,
    backToSources,
    loadBoard
  }
})
