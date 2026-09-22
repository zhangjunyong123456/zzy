<template>
  <div class="agent-card summary-card" :class="{ selected }" :style="{ '--card-color': '#C9744F' }">
    <div class="card-head">
      <div class="avatar">🧭</div>
      <span class="name">{{ item.label || '主Agent · 综合建议' }}</span>
      <span class="status">{{ item.streaming ? '汇总中…' : item.stopped ? '已停止' : '已完成' }}</span>
      <button
        v-if="item.id && !item.streaming"
        class="sc-sel"
        :class="{ on: selected }"
        :title="selected ? '取消选为记忆' : '选为记忆'"
        :aria-label="selected ? '取消选为记忆' : '选为记忆'"
        @click="store.toggleSelect(item.id)"
      >{{ selected ? '✓ 记忆' : '＋' }}</button>
    </div>
    <MarkdownRenderer v-if="item.content" :source="item.content" />
    <div v-else class="status" style="padding: 4px 0">正在整合各Agent结论…</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { useChatStore } from '../../stores/chat'

const props = defineProps({ item: { type: Object, required: true } })
const store = useChatStore()
const selected = computed(() => props.item.id && store.selectedMessageIds.includes(props.item.id))
</script>

<style scoped>
.sc-sel {
  margin-left: auto;
  border: none;
  background: var(--bg-page, #faf7f2);
  color: var(--text-sub, #878e99);
  font-size: 12px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 999px;
  cursor: pointer;
  opacity: 0;
  transition: opacity .15s, background .15s, color .15s;
  flex-shrink: 0;
}
.summary-card:hover .sc-sel { opacity: 1; }
.sc-sel.on {
  opacity: 1;
  background: #c9744f;
  color: #fff;
}
.summary-card.selected {
  box-shadow: 0 0 0 2px #c9744f;
}
</style>
