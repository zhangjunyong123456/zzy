<template>
  <div class="input-bar">
    <div class="input-inner">
      <div class="chips" :key="store.sceneTheme ? store.sceneTheme.key : 'default'">
        <span
          v-for="(c, i) in suggestions"
          :key="c"
          v-prox="{ pull: 3, radius: 90 }"
          class="chip"
          :style="{ animationDelay: i * 60 + 'ms' }"
          @click="quick(c)"
        >
          {{ c }}
        </span>
      </div>
      <PendingAttachments />
      <div v-if="activeMemories.length" class="mem-chips">
        <span class="mc-label">🧠 记忆</span>
        <span v-for="m in activeMemories" :key="m.id" class="mem-chip" :title="m.content">
          {{ m.title }}
          <button class="mc-x" title="停用该记忆（不影响记忆库）" @click="store.toggleMemory(m.id)">×</button>
          <button class="mc-del" title="从记忆库删除" @click="delMemory(m)">🗑</button>
        </span>
      </div>
      <div class="input-row">
        <button
          class="tool-btn"
          title="上传图片或文件（png / jpg / webp / pdf / docx / txt / md）"
          :disabled="store.streaming || uploading"
          @click="fileInput.click()"
        >
          📎
        </button>
        <input
          ref="fileInput"
          type="file"
          multiple
          hidden
          :accept="ACCEPT"
          @change="onFiles"
        />
        <el-popover placement="top-start" :width="320" trigger="click">
          <template #reference>
            <button
              class="tool-btn"
              :class="{ lit: store.activeMemoryIds.length }"
              title="记忆库：勾选要注入对话的历史记忆"
            >
              🧠
            </button>
          </template>
          <MemoryPanel />
        </el-popover>
        <textarea
          v-model="text"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          :disabled="store.streaming"
          @keydown.enter.exact.prevent="doSend"
        ></textarea>
        <el-dropdown trigger="click" @command="onPick">
          <button class="model-pick" v-prox="{ pull: 3, radius: 90 }" :disabled="store.streaming" title="切换模型">
            <span class="mp-text">{{ curLabel }}</span>
            <span class="mp-arrow">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="p in providerItems" :key="p.value" :command="p.value">
                <span class="mi-check">{{ p.active ? '✓' : '' }}</span>
                <span class="mi-label">{{ p.label }}</span>
                <span class="mi-model" :class="{ none: !p.configured }">
                  {{ p.configured ? p.model : '未配置' }}
                </span>
              </el-dropdown-item>
              <el-dropdown-item divided command="__manage">
                <span class="mi-manage">⚙ 模型配置中心</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button
          v-if="store.streaming"
          type="danger"
          size="large"
          round
          v-prox="{ pull: 6, radius: 110 }"
          title="停止生成（已生成内容会保留）"
          @click="store.stopStreaming()"
        >
          ■ 停止
        </el-button>
        <el-button
          v-else
          type="warning"
          size="large"
          round
          v-prox="{ pull: 6, radius: 110 }"
          @click="doSend"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../../stores/chat'
import PendingAttachments from './PendingAttachments.vue'
import MemoryPanel from './MemoryPanel.vue'

const router = useRouter()
const store = useChatStore()
const text = ref('')
const fileInput = ref(null)
const uploading = ref(false)

/* 附件类型白名单（与后端 attachment_service 一致） */
const ACCEPT =
  '.png,.jpg,.jpeg,.webp,.pdf,.docx,.pptx,.txt,.md,image/png,image/jpeg,image/webp'

const activeMemories = computed(() =>
  store.memories.filter((m) => store.activeMemoryIds.includes(m.id))
)

async function delMemory(m) {
  try {
    await ElMessageBox.confirm(`从记忆库删除「${m.title}」？删除后不可恢复。`, '删除记忆', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await store.removeMemory(m.id)
    ElMessage.success('记忆已删除')
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => store.loadMemories())

async function onFiles(e) {
  const files = [...(e.target.files || [])]
  e.target.value = ''
  if (!files.length || uploading.value) return
  uploading.value = true
  for (const f of files) {
    try {
      const att = await store.uploadPending(f)
      if (att.warning) ElMessage.warning(att.warning)
    } catch (err) {
      ElMessage.error(`${f.name}：${err.message || '上传失败'}`)
    }
  }
  uploading.value = false
}

/* 默认建议与上方场景卡提示语去重：只放场景卡没覆盖过的问题 */
const EXAMPLES = [
  '期末两周怎么同时兼顾复习和秋招',
  '分析一下挑战杯的赛题怎么入手',
  '大创项目选题有什么建议',
  '考研英语全年怎么规划',
  '小组作业分工不均怎么协调'
]

/* 每个方向的专属建议问题 */
const SUGGESTIONS = {
  study: ['帮我制定期末复习计划', '这份课件的重点考点有哪些', '用费曼学习法给我讲一个概念'],
  research: ['推荐3个值得深挖的研究方向', '文献综述应该怎么组织结构', '怎么看一篇论文的实验设计'],
  competition: ['iCAN比赛的时间线怎么规划', '挑战杯计划书从哪部分写起', '组队分工有什么建议'],
  career: ['帮我优化简历的项目描述', '模拟一场产品经理面试', '秋招时间线应该怎么安排'],
  campus: ['推荐几个高性价比的社团', '校园卡丢了怎么补办', '周末有什么校园活动']
}

const suggestions = computed(() =>
  store.sceneTheme ? SUGGESTIONS[store.sceneTheme.key] || EXAMPLES : EXAMPLES
)

/* ---------- 模型快速切换 ---------- */
const PROVIDER_LABEL = { deepseek: 'DeepSeek', siliconflow: '硅基流动', zhipu: '智谱' }

const providerItems = computed(() =>
  ['deepseek', 'siliconflow', 'zhipu'].map((v) => {
    const info = store.providerInfo[v] || {}
    return {
      value: v,
      label: PROVIDER_LABEL[v],
      configured: !!info.configured,
      active: v === store.activeProvider,
      model: info.model || ''
    }
  })
)

const curLabel = computed(() => {
  const info = store.providerInfo[store.activeProvider]
  return info?.model || (store.configOk ? '模型' : '演示模式')
})

async function onPick(cmd) {
  if (cmd === '__manage') {
    router.push('/profile?tab=models')
    return
  }
  const item = providerItems.value.find((p) => p.value === cmd)
  if (!item || item.active) return
  if (!item.configured) {
    ElMessage.info(`${item.label} 还未配置 Key，先去「模型服务」页配置`)
    router.push('/profile?tab=models')
    return
  }
  try {
    await store.switchProvider(cmd)
    await store.loadConfigStatus()
    ElMessage.success(`已切换到 ${item.label} · ${store.providerInfo[cmd]?.model || ''}`)
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '切换失败')
  }
}

function quick(q) {
  if (!store.streaming) {
    text.value = q
    doSend()
  }
}

function doSend() {
  const msg = text.value.trim()
  if (!msg || store.streaming) return
  text.value = ''
  store.send(msg)
}
</script>

<style scoped>
.tool-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  padding: 6px 6px;
  border-radius: 8px;
  line-height: 1;
  outline: none;
  transition: background .2s, transform .2s;
}
.tool-btn:hover:not(:disabled) { background: var(--bg-page, #faf7f2); transform: translateY(-1px); }
.tool-btn:disabled { cursor: not-allowed; opacity: .45; }
.tool-btn.lit {
  background: #fff3ec;
  box-shadow: inset 0 0 0 1px rgba(217, 105, 74, .35);
}

.mem-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.mc-label {
  font-size: 11.5px;
  color: var(--accent, #d9694a);
  font-weight: 600;
}
.mem-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 220px;
  padding: 3px 8px;
  background: #fff3ec;
  border-radius: 999px;
  font-size: 12px;
  color: var(--accent, #d9694a);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.mc-x {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--accent, #d9694a);
  font-size: 13px;
  padding: 0;
  line-height: 1;
}
.mc-x:hover { color: #b34a30; }
.mc-del {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--accent, #d9694a);
  font-size: 11px;
  padding: 0;
  line-height: 1;
  opacity: .75;
}
.mc-del:hover { opacity: 1; color: #d03050; }

.model-pick {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-sub, #878e99);
  font-size: 12.5px;
  padding: 6px 8px;
  border-radius: 8px;
  white-space: nowrap;
  outline: none;
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 1px * var(--prox, 0)), 0);
  transition: transform .25s cubic-bezier(.16, 1, .3, 1), background .2s, color .2s;
}
.model-pick:hover:not(:disabled) {
  background: var(--bg-page, #faf7f2);
  color: var(--text-main, #1d2129);
}
.model-pick:disabled { cursor: not-allowed; opacity: .55; }
.mp-text {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mp-arrow { font-size: 10px; transform: translateY(-1px); }

.mi-check {
  display: inline-block;
  width: 14px;
  color: var(--accent, #d9694a);
  font-size: 12px;
}
.mi-label { font-size: 13px; }
.mi-model {
  float: right;
  margin-left: 18px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: var(--text-sub, #878e99);
}
.mi-model.none { color: #e6a23c; }
.mi-manage { font-size: 12.5px; color: var(--text-sub, #878e99); }
</style>
