import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { TOKEN_KEY, getToken } from '../api/client'
import * as authApi from '../api/auth'

function loadSavedUser() {
  try {
    return JSON.parse(localStorage.getItem('ug_user') || 'null')
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    user: loadSavedUser()
  }),

  getters: {
    isLoggedIn: (s) => !!s.token && !!s.user,
    displayName: (s) => s.user?.nickname || s.user?.username || ''
  },

  actions: {
    _setAuth({ token, user }) {
      this.token = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem('ug_user', JSON.stringify(user))
    },

    async login(payload) {
      const data = await authApi.login(payload)
      this._setAuth(data)
      return data.user
    },

    async register(payload) {
      const data = await authApi.register(payload)
      this._setAuth(data)
      return data.user
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('ug_user')
    },

    async updateProfile(patch) {
      const user = await authApi.updateProfile(patch)
      this.user = user
      localStorage.setItem('ug_user', JSON.stringify(user))
      return user
    },

    /** 兜底：本地有 token 但缺用户信息时拉取一次 */
    async hydrate() {
      if (!this.token || this.user) return
      try {
        this.user = await authApi.me()
        localStorage.setItem('ug_user', JSON.stringify(this.user))
      } catch {
        /* 401 已由拦截器统一清理 */
      }
    },

    /** 注册全局 401 监听：登录过期 → 提示并降级游客态（不强制跳登录页） */
    init(router) {
      if (this._inited) return
      this._inited = true
      window.addEventListener('ug:unauthorized', () => {
        this.logout()
        ElMessage.warning('登录已过期，已切换为游客模式')
        if (router?.currentRoute?.value?.meta?.requiresAuth) {
          router.push({ path: '/' })
        }
      })
      this.hydrate()
    }
  }
})
