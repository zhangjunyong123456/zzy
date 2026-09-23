<template>
  <div class="ms-wrap">
    <!-- 总状态条 -->
    <div class="ms-status" :class="{ ok: !!activeCard }">
      <span class="dot"></span>
      <span class="st-text">
        <template v-if="activeCard">
          已使用你自己的 Key · {{ activeCard.meta.label }} / {{ activeCard.model }}
        </template>
        <template v-else>未配置 Key · 当前为演示模式（规则回复）</template>
      </span>
      <span class="st-hint">Key 仅保存在你的浏览器本地，不会上传服务器存储；对话时直接透传给模型厂商</span>
    </div>

    <!-- 三张供应商卡片 -->
    <div v-for="c in cards" :key="c.value" class="ms-card" :class="{ active: c.active }">
      <div class="ms-head">
        <span class="ms-name">{{ c.label }}</span>
        <span class="ms-model">{{ c.model }}</span>
        <el-tag v-if="c.active" type="success" effect="dark" size="small" round>✓ 使用中</el-tag>
        <el-tag v-else-if="c.configured" type="info" effect="plain" size="small" round>已保存</el-tag>
        <el-tag v-else type="warning" effect="plain" size="small" round>未配置</el-tag>
        <el-button
          v-if="!c.active"
          class="ms-use"
          size="small"
          type="primary"
          plain
          :disabled="!c.configured || switching"
          @click="use(c.value)"
        >
          启用
        </el-button>
      </div>

      <div class="ms-grid">
        <div class="ms-field">
          <label>官网 / Key 申请</label>
          <a :href="c.link" target="_blank" rel="noopener">{{ c.linkText }} ↗</a>
        </div>
        <div class="ms-field">
          <label>API Key</label>
          <div class="ms-inline">
            <el-input
              v-model="c.keyDraft"
              type="password"
              show-password
              :placeholder="c.configured ? '•••••• 已保存，输入新 Key 可覆盖' : c.placeholder"
              @keydown.enter="saveKey(c)"
            />
            <el-button type="primary" :loading="c.saving" :disabled="!c.keyDraft.trim()" @click="saveKey(c)">
              保存{{ c.configured ? '' : '并启用' }}
            </el-button>
          </div>
          <p v-if="c.note" class="ms-note">{{ c.note }}</p>
        </div>
        <div class="ms-field">
          <label>模型名（可选，留空用默认）</label>
          <div class="ms-inline">
            <el-input v-model="c.modelDraft" :placeholder="c.defaultModel" @keydown.enter="saveModel(c)" />
            <el-button
              :loading="c.savingModel"
              :disabled="c.savingModel || c.modelDraft.trim() === getModel(c.value)"
              @click="saveModel(c)"
            >
              保存
            </el-button>
          </div>
        </div>
        <div class="ms-field">
          <label>API 地址</label>
          <span class="ms-url">{{ c.base }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { verifyKey } from '../../api/documents'
import {
  PROVIDER_META,
  PROVIDER_ORDER,
  getActive,
  getModel,
  getKey,
  saveKey as persistKey,
  saveModel as persistModel,
  setActive
} from '../../utils/llmStorage'

const cards = reactive([])
const switching = ref(false)
const activeCard = computed(() => cards.find((c) => c.active))

for (const value of PROVIDER_ORDER) {
  const meta = PROVIDER_META[value]
  cards.push(
    reactive({
      value,
      ...meta,
      configured: !!getKey(value),
      active: getActive() === value && !!getKey(value),
      model: getModel(value),
      defaultModel: meta.model,
      keyDraft: '',
      modelDraft: getModel(value),
      saving: false,
      savingModel: false
    })
  )
}

/** 保存并在线校验 Key；校验通过自动启用 */
async function saveKey(c) {
  const k = c.keyDraft.trim()
  if (!k || c.saving) return
  c.saving = true
  try {
    await verifyKey(c.value, k, c.modelDraft.trim())
    persistKey(c.value, k)
    setActive(c.value)
    c.keyDraft = ''
    refresh()
    ElMessage.success(`${c.label} Key 校验通过，已保存并启用`)
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || 'Key 校验未通过，请检查后重试')
  } finally {
    c.saving = false
  }
}

async function saveModel(c) {
  const m = c.modelDraft.trim()
  if (c.savingModel || m === getModel(c.value)) return
  c.savingModel = true
  try {
    persistModel(c.value, m)
    refresh()
    ElMessage.success(m ? `模型已切换为 ${m}` : '已恢复默认模型')
  } finally {
    c.savingModel = false
  }
}

async function use(provider) {
  if (switching.value) return
  switching.value = true
  try {
    setActive(provider)
    refresh()
    const c = cards.find((x) => x.value === provider)
    ElMessage.success(`已启用 ${c?.label} · ${getModel(provider)}`)
  } finally {
    switching.value = false
  }
}

function refresh() {
  for (const c of cards) {
    c.configured = !!getKey(c.value)
    c.active = getActive() === c.value && !!getKey(c.value)
    c.model = getModel(c.value)
    c.modelDraft = getModel(c.value)
  }
}

onMounted(refresh)
</script>

<style scoped>
.ms-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ms-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-radius: 12px;
  background: #fdf6ec;
  border: 1px solid #f5dcb8;
  color: #92610e;
  font-size: 13px;
}
.ms-status.ok {
  background: #f0f9eb;
  border-color: #d1edc4;
  color: #529b2e;
}
.ms-status .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e6a23c;
}
.ms-status.ok .dot { background: #67c23a; }
.st-hint { font-size: 12px; opacity: .75; }

.ms-card {
  border: 1px solid var(--border, #e9ebee);
  border-radius: 14px;
  padding: 14px 18px 16px;
  transition: border-color .2s, box-shadow .2s;
}
.ms-card.active {
  border-color: var(--accent, #d9694a);
  box-shadow: 0 4px 18px rgba(217, 105, 74, .10);
}
.ms-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ms-name { font-weight: 600; font-size: 14.5px; }
.ms-model {
  font-family: Consolas, Monaco, monospace;
  font-size: 12.5px;
  color: var(--text-sub, #878e99);
  background: var(--bg-page, #faf7f2);
  border-radius: 6px;
  padding: 2px 8px;
}
.ms-use { margin-left: auto; }

.ms-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px 22px;
  margin-top: 12px;
}
.ms-field label {
  display: block;
  font-size: 12px;
  color: var(--text-sub, #878e99);
  margin-bottom: 5px;
}
.ms-field a { color: var(--accent, #d9694a); font-size: 13px; }
.ms-inline { display: flex; gap: 8px; }
.ms-note { margin: 5px 0 0; font-size: 12px; color: var(--text-sub, #878e99); }
.ms-url {
  font-family: Consolas, Monaco, monospace;
  font-size: 12.5px;
  color: var(--text-sub, #878e99);
  line-height: 32px;
}
@media (max-width: 640px) {
  .ms-grid { grid-template-columns: 1fr; }
}
</style>
