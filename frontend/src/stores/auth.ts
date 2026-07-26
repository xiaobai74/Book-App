/* ═══════════════════════════════════════════════════════
   小说管理App · 认证状态管理 (Pinia)
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, changePassword as changePasswordApi } from '@/api/auth'
import type { AuthRequest, ChangePasswordRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const userEmail = ref(localStorage.getItem('user_email') || '')

  const isLoggedIn = computed(() => !!accessToken.value)

  /** 注册 */
  async function register(payload: AuthRequest) {
    const { data } = await registerApi(payload)
    if (data.success && data.data) {
      userEmail.value = data.data.email
      return data.data
    }
    throw new Error(data.error || '注册失败')
  }

  /** 登录 */
  async function login(payload: AuthRequest) {
    const { data } = await loginApi(payload)
    if (data.success && data.data) {
      accessToken.value = data.data.access_token
      refreshToken.value = data.data.refresh_token
      userEmail.value = payload.email
      localStorage.setItem('access_token', data.data.access_token)
      localStorage.setItem('refresh_token', data.data.refresh_token)
      localStorage.setItem('user_email', payload.email)
      return data.data
    }
    throw new Error(data.error || '登录失败')
  }

  /** 修改密码 */
  async function changePassword(payload: ChangePasswordRequest) {
    const { data } = await changePasswordApi(payload)
    if (!data.success) {
      throw new Error(data.error || '密码修改失败')
    }
  }

  /** 退出登录 */
  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    userEmail.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_email')
  }

  /** 获取用户头像首字母 */
  const avatarLetter = computed(() => (userEmail.value || 'U').charAt(0).toUpperCase())

  return {
    accessToken,
    refreshToken,
    userEmail,
    isLoggedIn,
    avatarLetter,
    register,
    login,
    changePassword,
    logout
  }
})
