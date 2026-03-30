// 认证相关 API
import api from './request'

export const authApi = {
  // 登录 - 使用 OAuth2 密码流，需要 form-urlencoded 格式
  login: (username, password) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return api.get('/auth/me')
  },

  // 注册
  register: (username, email, password) => {
    return api.post('/auth/register', { username, email, password })
  }
}