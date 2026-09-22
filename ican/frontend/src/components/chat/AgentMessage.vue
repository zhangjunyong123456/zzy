<template>
  <div class="agent-card" :class="{ selected }" :style="{ '--card-color': item.color }">
    <div class="card-head">
      <div class="avatar">{{ item.icon }}</div>
      <span class="name">{{ item.label }}</span>
      <span class="status">
        {{ item.streaming ? '生成中…' : item.error ? '出错了' : item.stopped ? '已停止' : '已完成' }}
      </span>
      <button
        v-if="item.id && !item.streaming"
        class="am-sel"
        :class="{ on: selected }"
        :title="selected ? '取消选为记忆' : '选为记忆'"
        :aria-label="selected ? '取消选为记忆' : '选为记忆'"
        @click="store.toggleSelect(item.id)"
      >{{ selected ? '✓ 记忆' : '＋' }}</button>
    </div>
    <div v-if="item.error" class="err-box">⚠️ {{ item.error }}</div>
    <MarkdownRenderer v-else-if="item.content" :source="item.content" />
    <div v-else-if="item.streaming" class="status" style="padding: 4px 0">
      正在思考…
    </div>
    <span v-if="item.streaming && item.content" class="caret"></span>
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
.am-sel {
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
.agent-card:hover .am-sel { opacity: 1; }
.am-sel.on {
  opacity: 1;
  background: var(--accent, #d9694a);
  color: #fff;
}
.agent-card.selected {
  box-shadow: 0 0 0 2px var(--accent, #d9694a);
}
</style>
