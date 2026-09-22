<template>
  <div class="memp-panel">
    <p class="memp-title">🧠 记忆库（{{ store.memories.length }}）</p>
    <p class="memp-sub">勾选的记忆会注入后续每条提问，帮助 AI 结合历史对话回答</p>

    <div v-if="!store.memories.length" class="memp-empty">
      还没有保存记忆。<br />
      在左侧历史会话上点「💾」即可把选中的对话存为记忆。
    </div>

    <div v-else class="memp-list">
      <div v-for="m in store.memories" :key="m.id" class="memp-item">
        <el-checkbox
          :model-value="store.activeMemoryIds.includes(m.id)"
          @change="store.toggleMemory(m.id)"
        />
        <div class="memp-main">
          <template v-if="editingId === m.id">
            <el-input
              v-model="editingTitle"
              size="small"
              maxlength="60"
              @keyup.enter="saveRename(m)"
            />
            <button class="memp-act" @click="saveRename(m)">保存</button>
          </template>
          <template v-else>
            <span class="memp-name" :title="m.content">{{ m.title }}</span>
            <span class="memp-time">{{ shortTime(m.created_at) }}</span>
          </template>
        </div>
        <button class="memp-act" title="重命名" @click="startRename(m)">✎</button>
        <button class="memp-act danger" title="删除" @click="del(m)">🗑</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../../stores/chat'
import { renameMemory } from '../../api/memory'

const store = useChatStore()
const editingId = ref('')
const editingTitle = ref('')

function shortTime(iso) {
  return (iso || '').slice(0, 10)
}

function startRename(m) {
  editingId.value = m.id
  editingTitle.value = m.title
}

async function saveRename(m) {
  const title = editingTitle.value.trim()
  if (!title) return
  try {
    const updated = await renameMemory(m.id, title)
    m.title = updated.title
    editingId.value = ''
    ElMessage.success('已重命名')
  } catch (e) {
    ElMessage.error(e.message || '重命名失败')
  }
}

async function del(m) {
  try {
    await ElMessageBox.confirm(`删除记忆「${m.title}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await store.removeMemory(m.id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}
</script>

<style scoped>
.memp-panel { width: 300px; }
.memp-title {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main, #1d2129);
}
.memp-sub {
  margin: 0 0 10px;
  font-size: 11.5px;
  color: var(--text-sub, #878e99);
}
.memp-empty {
  padding: 18px 0;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--text-sub, #878e99);
  text-align: center;
}
.memp-list {
  max-height: 320px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.memp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px;
  border-radius: 8px;
}
.memp-item:hover { background: var(--bg-page, #faf7f2); }
.memp-main { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; }
.memp-name {
  font-size: 12.5px;
  color: var(--text-main, #1d2129);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.memp-time { font-size: 10.5px; color: var(--text-sub, #878e99); flex-shrink: 0; }
.memp-act {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-sub, #878e99);
  padding: 2px;
  flex-shrink: 0;
}
.memp-act:hover { color: var(--accent, #d9694a); }
.memp-act.danger:hover { color: #d03050; }
</style>
