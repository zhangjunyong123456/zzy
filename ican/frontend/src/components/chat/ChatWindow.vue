<template>
  <div class="chat-window" ref="win">
    <div class="chat-inner">
      <div v-if="store.messages.length === 0 && !store.sceneTheme" class="empty-hero">
        <p class="e-kicker">UNIGROW AGENT</p>
        <h2>今天，想往哪个方向<em>成长</em>？</h2>
        <p class="e-sub">一句话，五位专业 Agent 同时为你出发</p>
        <div class="scene-grid" :class="{ launching }">
          <button
            v-for="(s, i) in scenes"
            :key="s.key"
            v-prox="{ pull: 6, radius: 120 }"
            class="scene-card"
            :class="{ chosen: launching && s.key === chosenKey }"
            :style="{ '--c': s.color, '--i': i }"
            @click="ask(s)"
          >
            <span class="s-chip">{{ s.icon }}</span>
            <span class="s-name">{{ s.name }}</span>
            <span class="s-q">{{ s.q }}</span>
          </button>
        </div>
      </div>
      <div
        v-if="store.sceneTheme"
        class="scene-banner"
        :style="{ '--scene-c': store.sceneTheme.color }"
      >
        {{ store.sceneTheme.icon }} 已进入「{{ store.sceneTheme.name }}」方向 · 专业 Agent 就位
        <button class="sb-close" title="退出该方向" @click="store.sceneTheme = null">×</button>
      </div>
      <p v-if="store.sceneTheme && !store.messages.length" class="sb-hint">
        从下方建议问题开始，或直接输入你的问题
      </p>
      <template v-for="(m, i) in store.messages" :key="i">
        <UserMessage v-if="m.kind === 'user'" :item="m" />
        <RouteTimeline v-else-if="m.kind === 'route'" :item="m" />
        <AgentMessage v-else-if="m.kind === 'agent'" :item="m" />
        <SummaryCard v-else-if="m.kind === 'summary'" :item="m" />
        <div v-else-if="m.kind === 'notice'" class="notice-box">
          <span class="n-text">💡 {{ m.text }}</span>
          <button class="n-btn" @click="openKeyDialog">立即配置</button>
        </div>
        <div v-else-if="m.kind === 'error'" class="err-box" style="margin-bottom: 14px">
          ⚠️ {{ m.text }}
        </div>
      </template>
      <div v-if="store.selectedMessageIds.length" class="sel-bar">
        <span class="sb-info">🧠 已选 {{ store.selectedMessageIds.length }} 条对话</span>
        <el-button size="small" round @click="store.clearSelection()">取消</el-button>
        <el-button size="small" type="warning" round @click="saveVisible = true">存为记忆</el-button>
      </div>
    </div>
    <MemorySaveDialog
      v-model:visible="saveVisible"
      :session-id="store.currentSessionId || ''"
      :preselect="store.selectedMessageIds"
      @saved="store.clearSelection()"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '../../stores/chat'
import UserMessage from './UserMessage.vue'
import AgentMessage from './AgentMessage.vue'
import SummaryCard from './SummaryCard.vue'
import RouteTimeline from './RouteTimeline.vue'
import MemorySaveDialog from './MemorySaveDialog.vue'

const store = useChatStore()
const win = ref(null)
const saveVisible = ref(false)

const scenes = [
  { key: 'study', icon: '📚', name: '学习', color: '#E8896B', q: '帮我总结这份课件的考点' },
  { key: 'research', icon: '🔬', name: '科研', color: '#93AB84', q: '帮我分析一篇论文的创新点与研究方法' },
  { key: 'competition', icon: '🏆', name: '竞赛', color: '#DFA453', q: '我要参加iCAN比赛，帮我全面规划一下' },
  { key: 'career', icon: '💼', name: '求职', color: '#86AD72', q: '帮我优化简历并模拟一场面试' },
  { key: 'campus', icon: '🏫', name: '校园', color: '#7FB39C', q: '图书馆几点开门？怎么预约自习室？' }
]

const launching = ref(false)
const chosenKey = ref('')

/** 点击场景卡：只进入该方向（换主题/建议问题），不自动发问，等用户自己提问 */
function ask(s) {
  if (launching.value || store.streaming) return
  chosenKey.value = s.key
  launching.value = true
  setTimeout(() => {
    launching.value = false
    store.sceneTheme = s
  }, 430)
}

/** 打开 HeaderBar 的 API Key 配置弹窗（跨组件约定事件，与 ug:unauthorized 同模式） */
function openKeyDialog() {
  window.dispatchEvent(new CustomEvent('ug:open-key-dialog'))
}

watch(
  () => store.messages.map((m) => (m.content || '').length + m.kind).join('|'),
  async () => {
    await nextTick()
    if (win.value) win.value.scrollTop = win.value.scrollHeight
  }
)
</script>

<style scoped>
.sel-bar {
  position: sticky;
  bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
  padding: 8px 14px;
  background: var(--bg-card, #fff);
  border: 1px solid rgba(217, 105, 74, 0.35);
  border-radius: 999px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
}
.sb-info {
  font-size: 13px;
  color: var(--accent, #d9694a);
  font-weight: 600;
}
</style>
