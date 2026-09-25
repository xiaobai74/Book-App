/* ═══════════════════════════════════════════════════════
   小说管理App · 统一搜索页共享状态 (Pinia)
   搜索页的查询状态与「已搜索」标记缓存于本 store：
   切换页面再回来直接恢复上次结果，不会重新发起搜索；
   只有用户主动提交搜索 / 点击重新搜索才发起新请求。
   搜索结果本体分别存于 booksStore（普通 / 全网）与
   shelfSearch store（AI 语义），本 store 只持有页面级状态。
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiRecommendBooks } from '@/api/books'
import type { AiRecommendResult } from '@/types'

export const useSearchPageStore = defineStore('searchPage', () => {
  /** 当前搜索 tab：书架内 / 全网 */
  const mode = ref<'shelf' | 'web'>('web')
  /** 输入框内容 */
  const query = ref('')
  /** 是否已执行过搜索（控制空态 / 结果区渲染） */
  const hasSearched = ref(false)
  /** 最近一次实际执行搜索的关键词 */
  const currentQ = ref('')
  /** 书架内普通搜索当前页码 */
  const searchPage = ref(1)
  /** 最近一次普通搜索（书架内）成功的关键词——用于切 tab 时判断是否已有缓存结果 */
  const lastShelfQuery = ref('')
  /** 最近一次全网搜索成功的关键词——用于切 tab 时判断是否已有缓存结果 */
  const lastWebQuery = ref('')
  /** 全网结果中已加入书架的书：结果索引 → book id */
  const addedBookIds = ref<Record<number, string>>({})
  /** 书架 source_url 快照（判断「已在书架」），加载过一次后不再重复拉取 */
  const shelfUrls = ref<string[]>([])
  /** v2.7 阶段1b：书架快照轻拷贝（与 shelfUrls 同源同批加载），供全网搜索秒出「书架已有」提示 */
  const shelfBriefs = ref<{ id: string; title: string; author: string }[]>([])
  const shelfUrlsLoaded = ref(false)

  // ── 全网搜索 · AI 题材推荐状态（v2.6）────────────────
  /** AI 推荐请求进行中 */
  const webRecommending = ref(false)
  /** 当前推荐列表（2-3 本） */
  const webRecommendations = ref<AiRecommendResult[]>([])
  /** 产生当前推荐的题材输入（用于切 tab 缓存判断） */
  const webRecommendQuery = ref('')
  /** 用户是否已选中某本推荐 → 决定显示推荐卡片还是全网结果 */
  const webRecommendSelected = ref(false)
  /** 本次是否因 Dify 不可用/无推荐而回退为直接全网搜索（用于提示） */
  const webAiFallback = ref(false)

  /**
   * 执行 AI 题材推荐（全网搜索 tab）。
   * 成功返回 2-3 本推荐并写入状态；失败或空推荐返回 []（由调用方回退）。
   */
  async function performWebRecommend(q: string): Promise<AiRecommendResult[]> {
    const query = q.trim()
    if (!query) return []
    webRecommending.value = true
    try {
      const { data } = await aiRecommendBooks(query)
      if (data.success && data.data && data.data.length) {
        webRecommendations.value = data.data
        webRecommendQuery.value = query
        return data.data
      }
      webRecommendations.value = []
      return []
    } catch {
      webRecommendations.value = []
      return []
    } finally {
      webRecommending.value = false
    }
  }

  return {
    mode,
    query,
    hasSearched,
    currentQ,
    searchPage,
    lastShelfQuery,
    lastWebQuery,
    addedBookIds,
    shelfUrls,
    shelfBriefs,
    shelfUrlsLoaded,
    webRecommending,
    webRecommendations,
    webRecommendQuery,
    webRecommendSelected,
    webAiFallback,
    performWebRecommend
  }
})
