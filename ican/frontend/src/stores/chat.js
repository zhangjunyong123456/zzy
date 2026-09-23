import { defineStore } from 'pinia'
import { sendMessage } from '../api/chat'
import { uploadAttachment } from '../api/attachment'
import { listSessions, createSession, getSession, deleteSession } from '../api/documents'
import {
  PROVIDER_META,
  PROVIDER_ORDER,
  getActive,
  getKey,
  getModel,
  isConfigured,
  saveKey as persistKey,
  saveModel as persistModel,
  setActive as persistActive
} from '../utils/llmStorage'
import { listMemories, deleteMemory as deleteMemoryApi } from '../api/memory'
import { api, ApiError } from '../api/client'

/* 当前流式请求的中断器（非序列化状态，不放 Pinia state） */
let streamAbort = null

const AGENT_META = {
  study: { label: '学习Agent', icon: '📚', color: '#E8896B' },
  research: { label: '科研Agent', icon: '🔬', color: '#93AB84' },
  competition: { label: '竞赛Agent', icon: '🏆', color: '#DFA453' },
  career: { label: '求职Agent', icon: '💼', color: '#86AD72' },
  campus: { label: '校园Agent', icon: '🏫', color: '#7FB39C' },
  main: { label: '主Agent', icon: '🧭', color: '#D9694A' }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSessionId: null,
    /** @type {Array<object>} kind: user|route|agent|summary|notice|error */
    messages: [],
    streaming: false,
    activeAgents: [],
    configOk: null,
    /** 当前生效的模型供应商：deepseek | siliconflow | zhipu */
    activeProvider: null,
    /** 三家供应商配置矩阵 { [provider]: {configured, active, model, base_url} } */
    providerInfo: {},
    /** @type {null|{key:string,name:string,icon:string,color:string}} 当前场景方向主题 */
    sceneTheme: null,
    /** 演示模式 notice 只在当前会话提示一次 */
    noticeShown: false,
    /** @type {Array<object>} 待发送附件：{id, filename, kind, mime, size, previewURL} */
    pendingAttachments: [],
    /** @type {Array<object>} 已保存记忆：{id, title, content, created_at} */
    memories: [],
    /** @type {Array<string>} 当前启用的记忆 id（仅前端状态，随消息发送） */
    activeMemoryIds: [],
    /** @type {Array<string>} 点选待存记忆的消息 id（历史会话中点「＋」） */
    selectedMessageIds: [],
    /** 每日免费额度 {limit, used, remaining}；limit=null 表示不展示（自带 Key/功能关闭） */
    freeQuota: null
  }),

  actions: {
    /** 每日免费额度：未自带 Key 的用户每日可用服务器 Key 的真 AI 次数（游客共享池） */
    async loadFreeQuota() {
      try {
        const { data } = await api.get('/chat/quota')
        this.freeQuota = data
      } catch {
        this.freeQuota = null
      }
    },

    async loadSessions() {
      this.sessions = await listSessions()
    },
    async loadConfigStatus() {
      // BYOK：配置存于浏览器本地，无需请求服务端
      const active = getActive()
      this.configOk = isConfigured()
      this.activeProvider = this.configOk ? active : null
      this.providerInfo = Object.fromEntries(
        PROVIDER_ORDER.map((p) => [
          p,
          {
            configured: !!getKey(p),
            active: this.configOk && p === active,
            model: getModel(p),
            label: PROVIDER_META[p]?.label || p
          }
        ])
      )
    },
    /** 保存某供应商的 Key 到浏览器本地（不自动启用，由 ModelService 控制启用） */
    async saveApiKey(provider, key) {
      persistKey(provider, key)
      this.loadConfigStatus()
    },
    /** 切换当前使用的供应商（须已保存该家 Key） */
    async switchProvider(provider) {
      persistActive(provider)
      this.loadConfigStatus()
      return { provider, model: getModel(provider) }
    },
    /** 修改某供应商模型名 */
    async saveModel(provider, model) {
      persistModel(provider, model)
      this.loadConfigStatus()
    },

    /* ---------- 记忆 ---------- */
    async loadMemories() {
      try {
        this.memories = await listMemories()
        // 启用列表里已删除的记忆顺手清掉
        const ids = new Set(this.memories.map((m) => m.id))
        this.activeMemoryIds = this.activeMemoryIds.filter((id) => ids.has(id))
      } catch {
        this.memories = []
      }
    },
    toggleMemory(id) {
      const i = this.activeMemoryIds.indexOf(id)
      if (i >= 0) this.activeMemoryIds.splice(i, 1)
      else this.activeMemoryIds.push(id)
    },
    async removeMemory(id) {
      await deleteMemoryApi(id)
      this.activeMemoryIds = this.activeMemoryIds.filter((x) => x !== id)
      await this.loadMemories()
    },

    /* ---------- 附件 ---------- */
    async uploadPending(file) {
      const att = await uploadAttachment(file, this.currentSessionId)
      this.pendingAttachments.push({
        id: att.id,
        filename: att.filename,
        kind: att.kind,
        mime: att.mime,
        size: att.size,
        warning: att.warning,
        previewURL: att.kind === 'image' ? URL.createObjectURL(file) : ''
      })
      return att
    },
    removePending(id) {
      const i = this.pendingAttachments.findIndex((a) => a.id === id)
      if (i >= 0) {
        const [att] = this.pendingAttachments.splice(i, 1)
        if (att.previewURL) URL.revokeObjectURL(att.previewURL)
      }
    },

    /* ---------- 消息点选（存记忆） ---------- */
    toggleSelect(id) {
      if (!id || this.streaming) return
      const i = this.selectedMessageIds.indexOf(id)
      if (i >= 0) this.selectedMessageIds.splice(i, 1)
      else this.selectedMessageIds.push(id)
    },
    clearSelection() {
      this.selectedMessageIds = []
    },
    /** 流式结束后把后端消息 id 按角色顺序附到当前消息列表，使新消息也可点选 */
    async attachMessageIds() {
      if (!this.currentSessionId) return
      try {
        const data = await getSession(this.currentSessionId)
        const backend = data.messages || []
        let bi = 0
        for (const m of this.messages) {
          if (!['user', 'agent', 'summary'].includes(m.kind)) continue
          const role = m.kind === 'user' ? 'user' : m.kind === 'summary' ? 'summary' : 'agent'
          while (bi < backend.length && backend[bi].role !== role) bi++
          if (bi < backend.length) {
            m.id = backend[bi].id
            bi++
          }
        }
      } catch {
        /* 拿不到 id 时点选入口不出现，不影响使用 */
      }
    },

    async selectSession(id) {
      if (this.streaming) return
      const data = await getSession(id)
      this.currentSessionId = id
      this.activeAgents = []
      this.sceneTheme = null
      this.noticeShown = true // 历史会话里已含提示语境，不再重复弹
      this.selectedMessageIds = []
      this.messages = (data.messages || []).map((m) => {
        if (m.role === 'user')
          return { kind: 'user', id: m.id, text: m.content, attachments: m.attachments || [] }
        if (m.role === 'summary')
          return {
            kind: 'summary',
            id: m.id,
            content: m.content,
            streaming: false,
            label: AGENT_META.main.label,
            icon: AGENT_META.main.icon
          }
        const meta = AGENT_META[m.agent] || AGENT_META.main
        return { kind: 'agent', id: m.id, agent: m.agent, ...meta, content: m.content, streaming: false }
      })
    },
    async newSession() {
      if (this.streaming) return
      this.currentSessionId = null
      this.messages = []
      this.activeAgents = []
      this.sceneTheme = null
      this.noticeShown = false
      this.selectedMessageIds = []
    },
    async removeSession(id) {
      await deleteSession(id)
      if (this.currentSessionId === id) await this.newSession()
      await this.loadSessions()
    },
    _ensureAgentCard(agent) {
      const meta = AGENT_META[agent] || AGENT_META.main
      let card = this.messages.find(
        (m) => m.kind === 'agent' && m.agent === agent && m.streaming
      )
      if (!card) {
        card = { kind: 'agent', agent, ...meta, content: '', streaming: true, error: '' }
        this.messages.push(card)
      }
      return card
    },

    /** 停止生成：中断 SSE 流；空内容卡片移除，已生成内容保留并标记「已停止」 */
    stopStreaming() {
      if (!this.streaming || !streamAbort) return
      this.messages = this.messages.filter(
        (m) => !((m.kind === 'agent' || m.kind === 'summary') && m.streaming && !(m.content || '').trim())
      )
      // 后端会把部分内容落库，切会话回来仍可见
      this.messages.forEach((m) => {
        if ((m.kind === 'agent' || m.kind === 'summary') && m.streaming) m.stopped = true
      })
      streamAbort.abort()
    },

    async send(message) {
      if (this.streaming || !message.trim()) return
      // 未配置 Key 也发送：后端进入演示模式返回规则回复 + notice 引导接入

      // 附件随消息发送：先取走待发列表（含元数据），供气泡渲染
      const attachments = this.pendingAttachments.map((a) => ({
        id: a.id,
        filename: a.filename,
        kind: a.kind,
        mime: a.mime
      }))
      this.pendingAttachments.forEach((a) => a.previewURL && URL.revokeObjectURL(a.previewURL))
      this.pendingAttachments = []
      const memoryIds = [...this.activeMemoryIds]

      this.messages.push({ kind: 'user', text: message, attachments })
      this.streaming = true
      this.activeAgents = []

      const finish = () => {
        this.streaming = false
        this.messages.forEach((m) => (m.streaming = false))
        this.activeAgents = []
        this.loadSessions()
        this.attachMessageIds()
        this.loadFreeQuota() // 发送消耗了免费额度，刷新剩余次数角标
      }

      streamAbort = new AbortController()
      try {
        await sendMessage({
          sessionId: this.currentSessionId,
          message,
          attachmentIds: attachments.map((a) => a.id),
          memoryIds,
          category: this.sceneTheme?.key || null,
          signal: streamAbort.signal,
          onEvent: (event, data) => {
            if (event === 'message' && data?.session_id) {
              const isNew = !this.currentSessionId
              this.currentSessionId = data.session_id
              if (isNew) this.loadSessions()
              return
            }
            switch (event) {
              case 'route_plan': {
                this.messages.push({ kind: 'route', plan: data })
                this.activeAgents = data.agents.map((a) => a.name)
                break
              }
              case 'agent_start':
                this._ensureAgentCard(data.agent)
                break
              case 'token': {
                const card = this._ensureAgentCard(data.agent)
                card.content += data.content
                break
              }
              case 'agent_end': {
                const card = this.messages.find(
                  (m) => m.kind === 'agent' && m.agent === data.agent && m.streaming
                )
                if (card) card.streaming = false
                this.activeAgents = this.activeAgents.filter((a) => a !== data.agent)
                break
              }
              case 'summary_start': {
                const s = {
                  kind: 'summary',
                  content: '',
                  streaming: true,
                  label: data.label || AGENT_META.main.label,
                  icon: data.icon || AGENT_META.main.icon
                }
                this.messages.push(s)
                this.activeAgents.push('main')
                break
              }
              case 'summary_token': {
                const s = [...this.messages].reverse().find((m) => m.kind === 'summary')
                if (s) s.content += data.content
                break
              }
              case 'summary_end': {
                const s = [...this.messages].reverse().find((m) => m.kind === 'summary')
                if (s) s.streaming = false
                this.activeAgents = this.activeAgents.filter((a) => a !== 'main')
                break
              }
              case 'notice': {
                // 未配置 Key 的提示每个会话只插一次，后续靠头部常驻 Key 标签承接
                if (!this.noticeShown) {
                  this.noticeShown = true
                  this.messages.push({ kind: 'notice', text: data.message })
                }
                break
              }
              case 'error': {
                if (data.agent) {
                  const card = this._ensureAgentCard(data.agent)
                  card.error = data.message
                  card.streaming = false
                  this.activeAgents = this.activeAgents.filter((a) => a !== data.agent)
                } else {
                  this.messages.push({ kind: 'error', text: data.message })
                }
                break
              }
              case 'done':
                finish()
                break
            }
          }
        })
      } catch (e) {
        if (e?.name === 'AbortError') {
          // 用户主动停止：已生成内容保留，不当作错误提示
        } else if (e instanceof ApiError && e.status === 503) {
          this.configOk = false
          this.messages.push({
            kind: 'error',
            text: '未检测到你的模型 API Key：请到 个人中心 → 模型服务 配置你自己的 Key 后再试。'
          })
        } else {
          this.messages.push({ kind: 'error', text: e.message || '连接中断' })
        }
      } finally {
        finish()
      }
    }
  }
})
