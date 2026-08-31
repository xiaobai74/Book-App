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
  const shelfUrlsLoaded = ref(false)

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
    shelfUrlsLoaded
  }
})
