/* ═══════════════════════════════════════════════════════
   小说管理App · 认证 API
   ═══════════════════════════════════════════════════════ */
import http from './http'
import type { ApiResponse, AuthRequest, TokenData, RegisterData, ChangePasswordRequest } from '@/types'

/** 用户注册 */
export function register(data: AuthRequest) {
  return http.post<ApiResponse<RegisterData>>('/auth/register', data)
}

/** 用户登录 */
export function login(data: AuthRequest) {
  return http.post<ApiResponse<TokenData>>('/auth/login', data)
}

/** 刷新 Token */
export function refreshToken(refresh_token: string) {
  return http.post<ApiResponse<TokenData>>('/auth/refresh', { refresh_token })
}

/** 修改密码 */
export function changePassword(data: ChangePasswordRequest) {
  return http.put<ApiResponse<null>>('/auth/password', data)
}
