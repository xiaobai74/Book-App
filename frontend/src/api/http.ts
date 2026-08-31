/* ═══════════════════════════════════════════════════════
   小说管理App · Axios 实例 & 拦截器
   ═══════════════════════════════════════════════════════ */
import axios from 'axios'
import type { ApiResponse } from '@/types'
import { MOBILE_API_BASE } from '@/config'

// 检测运行环境：Electron 桌面 / Capacitor 移动 / Web
// 注意：Capacitor 8 起全局对象无 isNative 布尔属性，只有 isNativePlatform() 方法
const electronAPI = (window as any).electronAPI
const isCapacitor =
  !!(window as any).Capacitor?.isNativePlatform?.() ||
  window.location.origin === 'http://localhost' ||
  window.location.origin === 'https://localhost'

const baseURL = electronAPI?.isElectron
  ? `${electronAPI.apiBaseUrl}/api/v1`  // 桌面：本地后端动态端口
  : isCapacitor
    ? `${MOBILE_API_BASE}/api/v1`       // 移动：云端部署的后端
    : '/api/v1'                         // Web 开发模式：走 Vite proxy

/** 跳转到登录页（兼容原生容器 hash 路由和 Web history 路由） */
function redirectToLogin() {
  if (electronAPI?.isElectron || isCapacitor) {
    window.location.hash = '#/login'
  } else {
    window.location.href = '/login'
  }
}

const http = axios.create({
  baseURL,
  timeout: 60000,  // 60 秒，匹配后端外部搜索源站超时（30s 单源站 + 重试）
  headers: { 'Content-Type': 'application/json' }
})

/** 当前环境的 API 根地址（桌面=动态端口，移动=云端，Web=相对路径走 Vite proxy） */
export const API_BASE_URL = baseURL

/** 请求拦截：自动附加 Access Token */
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 响应拦截：401 时自动尝试刷新 Token */
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  failedQueue = []
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 401 且非刷新请求本身，尝试刷新 Token
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/')) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        // 无 refresh_token，直接跳转登录
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        redirectToLogin()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return http(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post<ApiResponse<{
          access_token: string
          refresh_token: string
          token_type: string
        }>>(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })

        if (data.success && data.data) {
          localStorage.setItem('access_token', data.data.access_token)
          localStorage.setItem('refresh_token', data.data.refresh_token)
          processQueue(null, data.data.access_token)
          originalRequest.headers.Authorization = `Bearer ${data.data.access_token}`
          return http(originalRequest)
        }
      } catch (refreshError) {
        processQueue(refreshError, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        redirectToLogin()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 已用新 token 重试过仍返回 401：token 确实失效，清理并跳转登录
    if (error.response?.status === 401 && originalRequest._retry) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      redirectToLogin()
    }

    return Promise.reject(error)
  }
)

export default http
