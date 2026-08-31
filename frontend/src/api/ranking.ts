/* ═══════════════════════════════════════════════════════
   小说管理App · 源站排行榜 API
   ═══════════════════════════════════════════════════════ */
import http from './http'
import type { ApiResponse, RankingSource, RankingBoardData } from '@/types'

/** 获取支持排行榜的源站列表 */
export function getRankingSources() {
  return http.get<ApiResponse<RankingSource[]>>('/ranking/sources')
}

/** 抓取指定源站的指定榜单；refresh=true 时跳过后端缓存强制重新抓取 */
export function getRankingBoard(sourceId: number, boardIndex: number, refresh = false) {
  return http.get<ApiResponse<RankingBoardData>>(
    `/ranking/${sourceId}/boards/${boardIndex}`,
    refresh ? { params: { refresh: true } } : undefined
  )
}
