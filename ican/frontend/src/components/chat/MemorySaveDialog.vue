<template>
  <el-dialog
    :model-value="visible"
    title="保存为记忆"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
    @open="onOpen"
  >
    <div v-loading="loading" class="msd-body">
      <p class="msd-tip">勾选要保存进记忆的对话内容（含用户提问与 AI 回答）：</p>
      <el-input
        v-model="title"
        class="msd-title"
        maxlength="60"
        placeholder="记忆名称，如：秋招复盘"
      />
      <el-checkbox-group v-model="picked" class="msd-list">
        <el-checkbox
          v-for="(m, i) in messages"
          :key="m.id"
          :value="m.id"
          class="msd-item"
          :class="'is-' + m.role"
        >
          <span class="msd-role">{{ m.role === 'user' ? '我' : 'AI' }}</span>
          <span class="msd-text">{{ excerpt(m.content) }}</span>
        </el-checkbox>
      </el-checkbox-group>
      <p v-if="!messages.length && !loading" class="msd-empty">该会话暂无消息</p>
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="warning" :disabled="!picked.length" :loading="saving" @click="save">
        保存记忆（{{ picked.length }}）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getSession } from '../../api/documents'
import { createMemory } from '../../api/memory'
import { useChatStore } from '../../stores/chat'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sessionId: { type: String, default: '' },
  /** 预选的消息 id（对话流中点选后带进来） */
  preselect: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useChatStore()
const loading = ref(false)
const saving = ref(false)
const messages = ref([])
const picked = ref([])
const title = ref('')

const excerpt = (t) => (t || '').replace(/\s+/g, ' ').slice(0, 60)

async function onOpen() {
  messages.value = []
  picked.value = []
  title.value = ''
  if (!props.sessionId) return
  loading.value = true
  try {
    const data = await getSession(props.sessionId)
    messages.value = (data.messages || []).filter((m) => m.content)
    const validIds = new Set(messages.value.map((m) => m.id))
    picked.value = props.preselect.filter((id) => validIds.has(id))
    // 默认标题：优先取已选中的首条用户消息，否则首条用户消息
    const firstPicked = messages.value.find((m) => m.role === 'user' && picked.value.includes(m.id))
    const firstUser = firstPicked || messages.value.find((m) => m.role === 'user')
    title.value = firstUser ? excerpt(firstUser.content).slice(0, 20) : ''
  } catch (e) {
    ElMessage.error(e.message || '会话加载失败')
  } finally {
    loading.value = false
  }
}

watch(picked, (val) => {
  // 未命名时随首个勾选补默认标题
  if (!title.value && val.length) {
    const m = messages.value.find((x) => x.id === val[0])
    if (m) title.value = excerpt(m.content).slice(0, 20)
  }
})

async function save() {
  saving.value = true
  try {
    await createMemory({
      title: title.value.trim() || '未命名记忆',
      source_session_id: props.sessionId,
      message_ids: picked.value
    })
    await store.loadMemories()
    ElMessage.success('已保存为记忆，可在输入栏 🧠 中启用')
    emit('saved')
    emit('update:visible', false)
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.msd-body { min-height: 160px; }
.msd-tip {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: var(--text-sub, #878e99);
}
.msd-title { margin-bottom: 10px; }
.msd-list {
  max-height: 300px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
}
.msd-item { margin-right: 0; align-items: flex-start; }
.msd-item :deep(.el-checkbox__label) {
  display: inline-flex;
  gap: 6px;
  align-items: baseline;
  white-space: normal;
}
.msd-role {
  flex-shrink: 0;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--bg-page, #faf7f2);
  color: var(--text-sub, #878e99);
}
.is-agent .msd-role,
.is-summary .msd-role { background: #fff3ec; color: var(--accent, #d9694a); }
.msd-text { font-size: 12.5px; color: var(--text-main, #1d2129); }
.msd-empty {
  text-align: center;
  color: var(--text-sub, #878e99);
  font-size: 12.5px;
  padding: 20px 0;
}
</style>
