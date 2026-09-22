<template>
  <router-view v-slot="{ Component }">
    <transition :name="transitionName" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
  <CursorFx />
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CursorFx from './components/fx/CursorFx.vue'
import { useUserStore } from './stores/user'

const router = useRouter()
const route = useRoute()

// 起始页 ↔ 对话页用「书本翻页」转场，其余路由保持默认渐移
const transitionName = ref('page')
router.beforeEach((to, from) => {
  const pair = (a, b) =>
    (from.name === a && to.name === b) || (from.name === b && to.name === a)
  transitionName.value = pair('landing', 'chat') ? 'page-flip' : 'page'
})

onMounted(() => {
  // 注册全局 401 监听 + 兜底拉取用户信息
  useUserStore().init(router)
})
</script>
