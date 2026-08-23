/* ═══════════════════════════════════════════════════
   小说管理App · 书架搜索共享状态 (Pinia)
   v1.9 — 书架内搜索框合并到主搜索框（TopNav）：
   AI 语义搜索状态（模式 / 结果 / 进行中）由本 store 统一持有，
   TopNav 主搜索框与 SearchView 书架内 tab 共享同一份状态，
   保证模式切换、加载态与结果展示跨组件一致。
   v2.0 — 新增 AI 搜索开关（aiEnabled，localStorage 持久化）：
   开关放在用户头像下拉菜单，开启后书架内搜索可搭配普通搜索
   使用（统一搜索页书架内 tab 显示普通 / AI 语义切换），
   未开启时书架内搜索默认普通搜索。
   v2.1 — 智能搜索模式路由：AI 开关开启后按查询意图自动选择
   搜索方式（自然语言描述 → AI 语义，书名/作者 → 普通），
   结果页可手动切换另一种方式（一次性覆盖，下次输入自动识别）。

   普通搜索不走本 store：TopNav 携带 q/mode/ai 参数跳转
   /search 页面，由 SearchView 负责执行（服务端搜索或客户端过滤）。
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { aiSearchBooks } from '@/api/books'
import type { AiSearchResult } from '@/types'
import { detectQueryIntent } from '@/lib/queryIntent'

/** AI 搜索开关的 localStorage 键 */
const AI_ENABLED_KEY = 'shelf_ai_search_enabled'

export const useShelfSearchStore = defineStore('shelfSearch', () => {
  // ── AI 搜索开关（v2.0，头像下拉菜单控制）────────────
  /** AI 搜索功能是否开启（localStorage 持久化，默认关闭） */
  const aiEnabled = ref(localStorage.getItem(AI_ENABLED_KEY) === '1')

  /** 切换 AI 搜索开关并持久化；关闭时同步清空 AI 结果与模式 */
  function setAiEnabled(enabled: boolean) {
    aiEnabled.value = enabled
    localStorage.setItem(AI_ENABLED_KEY, enabled ? '1' : '0')
    if (!enabled) {
      aiMode.value = false
      aiModeSource.value = 'auto'
      resetAiSearch()
    }
  }

  // ── AI 语义搜索状态 ────────────────────────────
  /** AI 搜索模式开关（普通 / AI 语义，TopNav 与 SearchView 共享） */
  const aiMode = ref(false)
  /**
   * 模式来源（v2.1）：'auto' = 按查询意图自动识别；
   * 'manual' = 用户在结果页手动切换（一次性覆盖，下次新查询恢复自动）。
   */
  const aiModeSource = ref<'auto' | 'manual'>('auto')
  /** AI 请求进行中 */
  const aiSearching = ref(false)
  /** AI 搜索结果 */
  const aiResults = ref<AiSearchResult[]>([])
  /** 已生效的 AI 搜索词（输入变更后立即失效旧结果，等待再次搜索） */
  const appliedAiQuery = ref('')
  // AI 请求序号：模式切换/连续搜索时丢弃过期响应，防止旧结果覆盖新结果
  let aiRequestSeq = 0

  /**
   * 按查询意图自动选择书架内搜索方式（v2.1）。
   * 本方法只由 TopNav 搜索入口在新查询提交前调用，故无条件恢复
   * 自动识别：自然语言描述 → AI 语义，书名 / 作者名 → 普通；
   * AI 开关关闭时强制普通搜索。
   */
  function applySearchMode(q: string) {
    aiModeSource.value = 'auto'
    aiMode.value = aiEnabled.value && detectQueryIntent(q) === 'ai'
  }

  /**
   * 手动切换搜索方式（v2.1，结果页「改用…搜索」调用）。
   * 切换同时清空旧结果，保证加载态与列表状态一致。
   */
  function overrideAiMode(enabled: boolean) {
    aiMode.value = enabled
    aiModeSource.value = 'manual'
    resetAiSearch()
  }

  /** 使在途 AI 请求失效（切换模式 / 清除搜索时调用） */
  function invalidateAiRequest() {
    aiRequestSeq++
    aiSearching.value = false
  }

  /** 清空 AI 搜索结果与已生效搜索词（切换模式 / 清空搜索时调用） */
  function resetAiSearch() {
    invalidateAiRequest()
    aiResults.value = []
    appliedAiQuery.value = ''
  }

  /** 执行 AI 自然语言搜索（TopNav 与 SearchView 共用入口） */
  async function performAiSearch(q: string): Promise<void> {
    const query = q.trim()
    if (!query || query.length < 2) {
      resetAiSearch()
      return
    }

    appliedAiQuery.value = query
    invalidateAiRequest()
    const seq = ++aiRequestSeq
    aiSearching.value = true
    try {
      const { data } = await aiSearchBooks(query)
      if (seq !== aiRequestSeq) return // 已有更新的 AI 搜索，丢弃过期响应
      if (data.success && data.data) {
        aiResults.value = data.data
      } else {
        aiResults.value = []
        ElMessage.warning('AI 搜索未找到匹配结果')
      }
    } catch (err: any) {
      if (seq !== aiRequestSeq) return
      aiResults.value = []
      const msg = err?.response?.data?.error || err?.message || 'AI 搜索请求失败'
      ElMessage.error(msg)
    } finally {
      if (seq === aiRequestSeq) {
        aiSearching.value = false
      }
    }
  }

  return {
    aiEnabled,
    setAiEnabled,
    aiMode,
    aiModeSource,
    applySearchMode,
    overrideAiMode,
    aiSearching,
    aiResults,
    appliedAiQuery,
    invalidateAiRequest,
    resetAiSearch,
    performAiSearch
  }
})
