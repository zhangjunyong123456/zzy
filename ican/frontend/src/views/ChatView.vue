<template>
  <div class="app-shell">
    <Sidebar />
    <div
      class="main-col"
      :style="store.sceneTheme ? { '--scene-color': store.sceneTheme.color } : {}"
    >
      <HeaderBar />
      <ChatWindow />
      <InputBar />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '../components/layout/Sidebar.vue'
import HeaderBar from '../components/layout/HeaderBar.vue'
import ChatWindow from '../components/chat/ChatWindow.vue'
import InputBar from '../components/chat/InputBar.vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const route = useRoute()

// 深链接：/chat?session=<id>（个人中心"最近会话"跳转）。会话不存在/越权(404)时静默降级为空会话
onMounted(async () => {
  const sid = route.query.session
  if (sid) {
    try {
      await store.selectSession(String(sid))
    } catch {
      /* 降级为新会话 */
    }
  }
})
</script>
