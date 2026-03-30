// 认证状态管理
import { create } from 'zustand'
import { authApi } from '../api/auth'

export const useAuthStore = create((set) => ({
  isAuthenticated: !!localStorage.getItem('token'),
  username: localStorage.getItem('username') || '',
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const response = await authApi.login(username, password)
      // 后端返回 { access_token, token_type }
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('username', username)
      set({
        isAuthenticated: true,
        username: username,
        loading: false
      })
      return true
    } catch (error) {
      set({
        loading: false,
        error: error.detail || '登录失败'
      })
      return false
    }
  },

  logout: () => {
    // 后端无 logout 接口，直接清除本地状态
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    set({
      isAuthenticated: false,
      username: ''
    })
  },

  verify: async () => {
    try {
      const response = await authApi.getCurrentUser()
      // 后端返回 { success: true, data: { id, username, email, ... } }
      if (response.success && response.data) {
        set({ isAuthenticated: true, username: response.data.username })
        return true
      }
    } catch (e) {
      // ignore
    }
    set({ isAuthenticated: false })
    return false
  }
}))