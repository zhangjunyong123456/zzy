<template>
  <div class="msg-user">
    <div v-if="imageItems.length" class="att-imgs">
      <el-image
        v-for="a in imageItems"
        :key="a.id"
        class="att-img"
        :src="urls[a.id]"
        :preview-src-list="[urls[a.id]]"
        :preview-teleported="true"
        fit="cover"
        hide-on-click-modal
        lazy
      >
        <template #placeholder>
          <div class="att-img loading">加载中…</div>
        </template>
        <template #error>
          <div class="att-img loading">图片加载失败</div>
        </template>
      </el-image>
    </div>
    <div v-if="fileItems.length" class="att-files">
      <button
        v-for="a in fileItems"
        :key="a.id"
        class="att-file"
        :title="`下载 ${a.filename}`"
        @click="download(a)"
      >
        <span class="af-icon">📄</span>
        <span class="af-name">{{ a.filename }}</span>
        <span class="af-down">⬇</span>
      </button>
    </div>
    <div class="bubble-row" :class="{ selected }">
      <button
        v-if="item.id"
        class="sel-btn"
        :class="{ on: selected }"
        :title="selected ? '取消选为记忆' : '选为记忆'"
        :aria-label="selected ? '取消选为记忆' : '选为记忆'"
        @click="store.toggleSelect(item.id)"
      >{{ selected ? '✓' : '＋' }}</button>
      <div v-if="item.text" class="bubble">{{ item.text }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { attachmentObjectURL, downloadAttachment } from '../../api/attachment'
import { useChatStore } from '../../stores/chat'

const props = defineProps({ item: { type: Object, required: true } })
const store = useChatStore()
const selected = computed(() => props.item.id && store.selectedMessageIds.includes(props.item.id))

const attachments = computed(() => props.item.attachments || [])
const imageItems = computed(() => attachments.value.filter((a) => a.kind === 'image'))
const fileItems = computed(() => attachments.value.filter((a) => a.kind !== 'image'))

/* 附件 id → objectURL（带鉴权 blob，按 id 全局缓存） */
const urls = reactive({})
watch(
  () => imageItems.value.map((a) => a.id).join('|'),
  async () => {
    for (const a of imageItems.value) {
      if (!urls[a.id]) {
        attachmentObjectURL(a.id)
          .then((u) => (urls[a.id] = u))
          .catch(() => {})
      }
    }
  },
  { immediate: true }
)

async function download(a) {
  try {
    await downloadAttachment(a.id, a.filename)
  } catch {
    /* 下载失败静默；raw 接口 404 已在鉴权层兜底 */
  }
}
</script>

<style scoped>
.msg-user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.att-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.att-img {
  width: 120px;
  height: 120px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.att-img.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page, #faf7f2);
  font-size: 11px;
  color: var(--text-sub, #878e99);
}
.att-files {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.att-file {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 260px;
  padding: 5px 10px;
  background: var(--bg-page, #faf7f2);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
}
.att-file:hover { border-color: var(--accent, #d9694a); }
.af-icon { font-size: 13px; }
.af-name {
  font-size: 12px;
  color: var(--text-main, #1d2129);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.af-down { font-size: 11px; color: var(--text-sub, #878e99); }
.bubble-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
  width: 100%;
}
.sel-btn {
  border: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  color: var(--text-sub, #878e99);
  background: var(--bg-page, #faf7f2);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  opacity: 0;
  transition: opacity .15s, background .15s, color .15s;
  flex-shrink: 0;
}
.bubble-row:hover .sel-btn { opacity: 1; }
.sel-btn.on {
  opacity: 1;
  background: var(--accent, #d9694a);
  color: #fff;
}
.bubble.selected {
  box-shadow: 0 0 0 2px var(--accent, #d9694a);
}
.bubble {
  background: #26272b;
  color: #fff;
  padding: 10px 16px;
  border-radius: 14px 14px 4px 14px;
  max-width: 70%;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}
</style>
