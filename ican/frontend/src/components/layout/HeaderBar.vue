<template>
  <header class="header-bar">
    <div class="left-zone">
      <router-link to="/" class="back-home" v-prox="{ pull: 3, radius: 90 }" title="返回首页">
        <el-icon :size="13"><ArrowLeft /></el-icon>首页
      </router-link>
      <div class="agent-dots">
      <div
        v-for="a in agents"
        :key="a.name"
        class="dot"
        :class="{ active: store.activeAgents.includes(a.name) }"
        :style="{ '--dot-color': a.color }"
      >
        <span class="led"></span>{{ a.icon }} {{ a.label }}
      </div>
      </div>
    </div>
    <div class="right-zone">
      <el-button v-if="!userStore.isLoggedIn" class="login-btn" v-prox="{ pull: 4, radius: 100 }" @click="$router.push('/login')">
        登录 / 注册
      </el-button>
      <el-dropdown v-else trigger="click" @command="onUserCommand">
        <div class="user-chip" v-prox="{ pull: 4, radius: 100 }">
          <el-avatar :size="30" class="avatar">{{ avatarChar }}</el-avatar>
          <span class="uname">{{ userStore.displayName }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">🏠 个人中心</el-dropdown-item>
            <el-dropdown-item divided command="logout">🚪 退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useChatStore } from '../../stores/chat'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const store = useChatStore()
const userStore = useUserStore()

const avatarChar = computed(() => (userStore.displayName || 'U').slice(0, 1).toUpperCase())

function onUserCommand(cmd) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'logout') {
    userStore.logout()
    store.newSession()
    store.loadSessions().catch(() => {})
    ElMessage.success('已退出登录，当前为游客模式')
  }
}
const agents = [
  { name: 'study', label: '学习', icon: '📚', color: '#E8896B' },
  { name: 'research', label: '科研', icon: '🔬', color: '#93AB84' },
  { name: 'competition', label: '竞赛', icon: '🏆', color: '#DFA453' },
  { name: 'career', label: '求职', icon: '💼', color: '#86AD72' },
  { name: 'campus', label: '校园', icon: '🏫', color: '#7FB39C' },
  { name: 'main', label: '主控', icon: '🧭', color: '#C9744F' }
]

/** API Key / 模型配置已移至个人中心「模型服务」Tab（游客也可访问） */
function goConfig() {
  router.push('/profile?tab=models')
}

onMounted(() => {
  store.loadConfigStatus()
  // 演示模式 notice 卡片「立即配置」→ 跳转模型服务页（ChatWindow 派发的约定事件）
  window.addEventListener('ug:open-key-dialog', goConfig)
})
onBeforeUnmount(() => window.removeEventListener('ug:open-key-dialog', goConfig))
</script>

<style scoped>
.left-zone {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}
.back-home {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-sub, #878e99);
  text-decoration: none;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--border, #e9ebee);
  background: var(--bg-card, #fff);
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 1px * var(--prox, 0)), 0);
  transition: color .2s, border-color .2s, transform .25s cubic-bezier(.16, 1, .3, 1);
}
.back-home:hover {
  color: var(--accent, #d9694a);
  border-color: var(--accent, #d9694a);
}
.right-zone {
  display: flex;
  align-items: center;
  gap: 12px;
}
.login-btn {
  padding: 6px 14px;
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 1px * var(--prox, 0)), 0);
  transition: transform .25s cubic-bezier(.16, 1, .3, 1), background-color .2s, border-color .2s;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 3px 10px 3px 3px;
  border-radius: 999px;
  border: 1px solid var(--border, #e9ebee);
  background: var(--bg-card, #fff);
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 1px * var(--prox, 0)), 0);
  transition: box-shadow .2s, transform .25s cubic-bezier(.16, 1, .3, 1);
}
.user-chip:hover { box-shadow: 0 2px 10px rgba(29, 33, 41, .08); }
.avatar {
  background: var(--accent, #d9694a);
  color: #fff;
  font-size: 14px;
}
.uname {
  font-size: 13px;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
