import axios from 'axios'

export const TOKEN_KEY = 'ug_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export const api = axios.create({ baseURL: '/api', timeout: 120000 })

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : detail?.message || `请求失败(${status})`)
    this.status = status
    this.detail = detail
  }
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    const url = err.config?.url || ''
    // 登录态失效：非登录/注册请求 401 → 清凭证并全局广播（降级游客态）
    if (status === 401 && !url.startsWith('/auth/login') && !url.startsWith('/auth/register')) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('ug_user')
      window.dispatchEvent(new CustomEvent('ug:unauthorized'))
    }
    return Promise.reject(new ApiError(status || 0, detail))
  }
)
