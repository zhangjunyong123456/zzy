<template>
  <div v-if="store.pendingAttachments.length" class="pa-row">
    <div v-for="a in store.pendingAttachments" :key="a.id" class="pa-item">
      <img v-if="a.kind === 'image' && a.previewURL" :src="a.previewURL" class="pa-thumb" alt="" />
      <span v-else class="pa-icon">{{ a.kind === 'image' ? '🖼️' : '📄' }}</span>
      <span class="pa-name" :title="a.filename">{{ a.filename }}</span>
      <button class="pa-del" title="移除附件" @click="store.removePending(a.id)">×</button>
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../../stores/chat'

const store = useChatStore()
</script>

<style scoped>
.pa-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.pa-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--bg-page, #faf7f2);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  max-width: 240px;
}
.pa-thumb {
  width: 30px;
  height: 30px;
  object-fit: cover;
  border-radius: 6px;
}
.pa-icon { font-size: 16px; }
.pa-name {
  font-size: 12px;
  color: var(--text-main, #1d2129);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pa-del {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-sub, #878e99);
  padding: 0 2px;
  line-height: 1;
}
.pa-del:hover { color: var(--accent, #d9694a); }
</style>
