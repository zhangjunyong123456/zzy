<template>
  <div class="banner-card">
    <el-avatar :size="64" class="avatar">{{ avatarChar }}</el-avatar>
    <div class="info">
      <h2>{{ userStore.displayName || '未设置昵称' }}</h2>
      <p class="uname">@{{ userStore.user?.username }}</p>
    </div>
    <div class="since">🗓 注册于 {{ memberSince }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()

const avatarChar = computed(() => (userStore.displayName || 'U').slice(0, 1).toUpperCase())

const memberSince = computed(() => {
  const ts = userStore.user?.created_at
  if (!ts) return ''
  return new Date(ts).toLocaleDateString('zh-CN')
})
</script>

<style scoped>
.banner-card {
  display: flex;
  align-items: center;
  gap: 18px;
  background:
    radial-gradient(420px 160px at 12% 0%, rgba(217, 105, 74, .10), transparent 65%),
    radial-gradient(360px 160px at 95% 120%, rgba(147, 171, 132, .12), transparent 60%),
    var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: 0 18px 50px rgba(29, 33, 41, .08);
  padding: 24px 30px;
}
.avatar {
  background: var(--accent);
  color: #fff;
  font-size: 26px;
  flex-shrink: 0;
}
.info h2 { margin: 0; font-size: 20px; }
.uname { margin: 4px 0 0; font-size: 13px; color: var(--text-sub); }
.since {
  margin-left: auto;
  font-size: 12.5px;
  color: var(--text-sub);
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--bg-page);
  border: 1px solid var(--border);
  flex-shrink: 0;
}
@media (max-width: 560px) {
  .since { display: none; }
}
</style>
