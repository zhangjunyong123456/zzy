<template>
  <aside class="sidebar">
    <div class="logo">
      🎓 UniGrow Agent
      <small>智学成长 · 大学生多智能体平台</small>
    </div>
    <el-button class="new-btn" type="warning" round v-prox="{ pull: 5, radius: 110 }" @click="store.newSession()">
      ＋ 新建对话
    </el-button>
    <div class="session-list">
      <template v-for="g in groups" :key="g.key">
        <button v-if="g.items.length" class="sg-head" @click="toggleGroup(g.key)">
          <span class="sg-arrow" :class="{ closed: collapsed[g.key] }">▾</span>
          <span class="sg-label">{{ g.label }}</span>
          <span class="sg-count">{{ g.items.length }}</span>
        </button>
        <template v-if="g.items.length && !collapsed[g.key]">
          <div
            v-for="s in g.items"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === store.currentSessionId }"
            @click="store.selectSession(s.id)"
          >
            <span class="title">{{ s.title }}</span>
            <span class="ops">
              <span
                v-if="s.message_count > 0"
                class="mem-save"
                role="button"
                title="把选中的对话保存为记忆"
                aria-label="把选中的对话保存为记忆"
                @click.stop="openSaveDialog(s)"
              >💾</span>
              <el-icon
                class="del"
                role="button"
                aria-label="删除会话"
                @click.stop="store.removeSession(s.id)"
              ><Delete /></el-icon>
            </span>
          </div>
        </template>
      </template>
    </div>
    <div class="footer-link">
      <el-button size="small" round @click="$router.push('/docs')">📁 知识库管理</el-button>
      <el-button size="small" round @click="$router.push('/chat')">💬 对话</el-button>
    </div>
    <MemorySaveDialog v-model:visible="saveVisible" :session-id="saveSessionId" />
  </aside>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { useChatStore } from '../../stores/chat'
import MemorySaveDialog from '../chat/MemorySaveDialog.vue'

const store = useChatStore()

/* 会话按场景方向分组；category 由首次发消息时的方向写入，老会话归综合 */
const GROUPS = [
  { key: 'study', label: '📚 学习方向' },
  { key: 'research', label: '🔬 科研方向' },
  { key: 'competition', label: '🏆 竞赛方向' },
  { key: 'career', label: '💼 求职方向' },
  { key: 'campus', label: '🏫 校园方向' },
  { key: 'general', label: '🧭 综合闲聊' }
]
const collapsed = reactive({})
const groups = computed(() =>
  GROUPS.map((g) => ({ ...g, items: store.sessions.filter((s) => (s.category || 'general') === g.key) }))
)
function toggleGroup(key) {
  collapsed[key] = !collapsed[key]
}

/* 保存记忆弹窗 */
const saveVisible = ref(false)
const saveSessionId = ref('')
function openSaveDialog(s) {
  saveSessionId.value = s.id
  saveVisible.value = true
}

onMounted(() => store.loadSessions())
</script>

<style scoped>
.sg-head {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px 8px 4px;
  font-family: inherit;
  text-align: left;
}
.sg-head:hover .sg-label { color: var(--accent, #d9694a); }
.sg-arrow {
  font-size: 10px;
  color: var(--text-sub, #878e99);
  transition: transform .15s;
}
.sg-arrow.closed { transform: rotate(-90deg); }
.sg-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-sub, #878e99);
}
.sg-count {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--text-sub, #878e99);
  background: var(--bg-page, #faf7f2);
  padding: 1px 7px;
  border-radius: 999px;
}
.ops {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}
.mem-save {
  cursor: pointer;
  font-size: 13px;
  opacity: 0;
  transition: opacity .15s;
  line-height: 1;
}
.session-item:hover .mem-save { opacity: .75; }
.mem-save:hover { opacity: 1; }
</style>
