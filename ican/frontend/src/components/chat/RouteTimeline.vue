<template>
  <div class="route-timeline">
    <div class="r-title">🧭 主Agent 调度链路 — {{ item.plan.plan_summary }}</div>
    <div class="r-flow">
      <span class="r-node" style="background: #C9744F">主Agent · 路由</span>
      <template v-for="(a, i) in item.plan.agents" :key="a.name">
        <span class="r-arrow">{{ i === 0 && item.plan.complexity === 'multi' ? '⇒ 并行 ⇒' : '→' }}</span>
        <span
          class="r-node"
          :class="nodeClass(a.name)"
          :style="{ background: a.color }"
        >
          {{ a.icon }} {{ a.label }}{{ item.plan.complexity === 'multi' && item.plan.agents.length > 1 ? ' ∥' : '' }}
        </span>
      </template>
      <template v-if="item.plan.complexity === 'multi'">
        <span class="r-arrow">→</span>
        <span class="r-node" style="background: #C9744F">🧭 汇总</span>
      </template>
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../../stores/chat'

defineProps({ item: { type: Object, required: true } })
const store = useChatStore()

function nodeClass(name) {
  return store.activeAgents.includes(name) ? 'running' : 'done'
}
</script>
