<template>
  <ul class="recent-list">
    <li v-for="s in sessions" :key="s.id" class="item" @click="open(s)">
      <span class="title">{{ s.title }}</span>
      <span class="meta">
        <span class="count">{{ s.message_count }} 条消息</span>
        <span class="time">{{ fmt(s.updated_at) }}</span>
      </span>
      <span class="arrow">›</span>
    </li>
  </ul>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  sessions: { type: Array, default: () => [] }
})

const router = useRouter()

function open(s) {
  router.push({ name: 'chat', query: { session: s.id } })
}

function fmt(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
</script>

<style scoped>
.recent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background .15s;
}
.item:hover { background: var(--bg-page); }
.item + .item { border-top: 1px solid var(--border); }
.title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: var(--text-main);
}
.meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.count {
  font-size: 12px;
  color: var(--accent);
  background: rgba(217, 105, 74, .09);
  padding: 2px 8px;
  border-radius: 999px;
}
.time { font-size: 12px; color: var(--text-sub); }
.arrow { color: var(--text-sub); font-size: 18px; line-height: 1; }
</style>
