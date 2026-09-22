<template>
  <div class="overview-grid">
    <div v-for="c in cards" :key="c.label" class="stat-card">
      <span class="icon">{{ c.icon }}</span>
      <strong>{{ c.value }}</strong>
      <span class="label">{{ c.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  totals: { type: Object, default: null }
})

const cards = computed(() => {
  const t = props.totals || {}
  return [
    { icon: '💬', label: '会话数', value: t.session_count ?? 0 },
    { icon: '❓', label: '提问数', value: t.question_count ?? 0 },
    { icon: '🤖', label: 'AI 回复', value: t.reply_count ?? 0 },
    { icon: '🔥', label: '活跃天数', value: t.active_days ?? 0 },
    { icon: '📅', label: '注册天数', value: t.days_since_register ?? 0 }
  ]
})
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 8px 14px;
  transition: transform .2s, box-shadow .2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(29, 33, 41, .07);
}
.icon { font-size: 20px; }
strong { font-size: 22px; color: var(--accent); line-height: 1.2; }
.label { font-size: 12px; color: var(--text-sub); }
@media (max-width: 720px) {
  .overview-grid { grid-template-columns: repeat(2, 1fr); }
  .overview-grid > :last-child { grid-column: span 2; }
}
</style>
