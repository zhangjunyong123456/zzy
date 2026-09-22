<template>
  <div class="ms-wrap">
    <!-- 总状态条 -->
    <div class="ms-status" :class="{ ok: !!status?.api_key_configured }">
      <span class="dot"></span>
      <span class="st-text">
        <template v-if="status?.api_key_configured">
          服务就绪 · 当前 {{ activeCard?.label }} / {{ status?.model }}
        </template>
        <template v-else>未配置 API Key · 当前为演示模式（规则回复）</template>
      </span>
      <span class="st-hint">Key 仅保存在本机 backend/.env，保存后立即生效、无需重启</span>
    </div>

    <!-- 三张供应商卡片 -->
    <div v-for="c in cards" :key="c.value" class="ms-card" :class="{ active: c.active }">
      <div class="ms-head">
        <span class="ms-name">{{ c.label }}</span>
        <span class="ms-model">{{ c.model }}</span>
        <el-tag v-if="c.active" type="success" effect="dark" size="small" round>✓ 当前使用</el-tag>
        <el-tag v-else-if="c.configured" type="info" effect="plain" size="small" round>已配置</el-tag>
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
          设为当前
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
              {{ c.configured ? '更新' : '保存' }}
            </el-button>
          </div>
          <p v-if="c.note" class="ms-note">{{ c.note }}</p>
        </div>
        <div class="ms-field">
          <label>默认模型</label>
          <div class="ms-inline">
            <el-input v-model="c.modelDraft" @keydown.enter="saveModel(c)" />
            <el-button
              :loading="c.savingModel"
              :disabled="!c.modelDraft.trim() || c.modelDraft.trim() === c.model"
              @click="saveModel(c)"
            >
              保存
            </el-button>
          </div>
        </div>
        <div class="ms-field">
          <label>API 地址</label>
          <span class="ms-url">{{ c.base_url }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { configStatus, saveApiKey } from '../../api/documents'
import { useChatStore } from '../../stores/chat'

const store = useChatStore()
const status = ref(null)
const switching = ref(false)

/** 供应商静态信息（链接/占位符等），动态字段由 /config/status 填充 */
const META = [
  {
    value: 'deepseek',
    label: 'DeepSeek',
    placeholder: 'sk-...',
    link: 'https://platform.deepseek.com',
    linkText: 'platform.deepseek.com',
    note: ''
  },
  {
    value: 'siliconflow',
    label: '硅基流动 SiliconFlow',
    placeholder: 'sk-...',
    link: 'https://cloud.siliconflow.cn/account/ak',
    linkText: 'cloud.siliconflow.cn',
    note: '价格见 siliconflow.com/pricing，另有 GLM / Kimi / Qwen 百余模型可选'
  },
  {
    value: 'zhipu',
    label: '智谱 GLM',
    placeholder: '形如 id.secret（中间有个点）',
    link: 'https://bigmodel.cn/usercenter/proj-mgmt/apikeys',
    linkText: 'bigmodel.cn',
    note: 'glm-4.5-flash 免费；旗舰 glm-5.3 直接改上方模型名即可'
  }
]

const cards = reactive([])
const activeCard = computed(() => cards.find((c) => c.active))

async function load() {
  const s = await configStatus().catch(() => null)
  if (!s) return
  status.value = s
  for (const meta of META) {
    const info = s.providers?.[meta.value] || {}
    let card = cards.find((c) => c.value === meta.value)
    if (!card) {
      card = reactive({ ...meta, keyDraft: '', modelDraft: '', saving: false, savingModel: false })
      cards.push(card)
    }
    card.configured = !!info.configured
    card.active = !!info.active
    card.model = info.model || ''
    card.base_url = info.base_url || ''
    card.modelDraft = card.model
  }
}

async function saveKey(c) {
  const k = c.keyDraft.trim()
  if (!k || c.saving) return
  c.saving = true
  try {
    await saveApiKey(c.value, k)
    c.keyDraft = ''
    ElMessage.success(`${c.label} API Key 已保存并生效`)
    await load()
    store.loadConfigStatus()
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '保存失败，请重试')
  } finally {
    c.saving = false
  }
}

async function saveModel(c) {
  const m = c.modelDraft.trim()
  if (!m || m === c.model || c.savingModel) return
  c.savingModel = true
  try {
    await store.saveModel(c.value, m)
    ElMessage.success(`模型已切换为 ${m}`)
    await load()
    store.loadConfigStatus()
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '保存失败，请重试')
  } finally {
    c.savingModel = false
  }
}

async function use(provider) {
  if (switching.value) return
  switching.value = true
  try {
    const s = await store.switchProvider(provider)
    ElMessage.success(`已切换到 ${s.provider === 'zhipu' ? '智谱' : s.provider === 'siliconflow' ? '硅基流动' : 'DeepSeek'} · ${s.model}`)
    await load()
    store.loadConfigStatus()
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '切换失败')
  } finally {
    switching.value = false
  }
}

onMounted(load)
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
