<template>
  <div v-loading="loading" class="stats-panel">
    <StatsOverview :totals="stats?.totals" />

    <template v-if="hasData">
      <div class="charts-grid">
        <section class="block">
          <h3>Agent 使用分布</h3>
          <AgentUsageChart :data="stats.agent_usage" />
        </section>
        <section class="block">
          <h3>近 14 天活跃趋势</h3>
          <ActivityTrendChart :data="stats.daily" />
        </section>
      </div>
      <section class="block">
        <h3>最近会话</h3>
        <RecentSessions :sessions="stats.recent_sessions" />
      </section>
    </template>

    <div v-else-if="!loading" class="empty">
      <p class="emoji">🌱</p>
      <p>还没有使用记录，去和 Agent 聊聊吧</p>
      <el-button type="primary" @click="$router.push('/chat')">开始对话</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { myStats } from '../../api/auth'
import StatsOverview from './StatsOverview.vue'
import AgentUsageChart from './AgentUsageChart.vue'
import ActivityTrendChart from './ActivityTrendChart.vue'
import RecentSessions from './RecentSessions.vue'

const loading = ref(false)
const stats = ref(null)

const hasData = computed(
  () =>
    (stats.value?.totals?.session_count || 0) > 0 ||
    (stats.value?.totals?.question_count || 0) > 0
)

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await myStats()
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '统计数据加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stats-panel {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 18px;
}
.block h3 {
  margin: 0 0 10px;
  font-size: 14.5px;
  color: var(--text-main);
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 36px 0 24px;
  color: var(--text-sub);
  font-size: 13.5px;
}
.empty .emoji { font-size: 38px; margin: 0; }
.empty p { margin: 0; }
@media (max-width: 720px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
