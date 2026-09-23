/**
 * BYOK：用户自带模型 API Key 的本地存储（仅存浏览器 localStorage，不经服务端持久化）。
 * 后端通过 X-LLM-Provider / X-LLM-Key / X-LLM-Model 请求头读取，优先于服务端全局 Key。
 */

export const PROVIDER_META = {
  deepseek: {
    label: 'DeepSeek',
    model: 'deepseek-flash',
    base: 'https://api.deepseek.com',
    placeholder: 'sk-...',
    link: 'https://platform.deepseek.com',
    linkText: 'platform.deepseek.com',
    note: ''
  },
  siliconflow: {
    label: '硅基流动 SiliconFlow',
    model: 'deepseek-ai/DeepSeek-V4-Flash',
    base: 'https://api.siliconflow.cn/v1',
    placeholder: 'sk-...',
    link: 'https://cloud.siliconflow.cn/account/ak',
    linkText: 'cloud.siliconflow.cn',
    note: '另有 GLM / Kimi / Qwen 百余模型可选，价格见 siliconflow.com/pricing'
  },
  zhipu: {
    label: '智谱 GLM',
    model: 'glm-4.5-flash',
    base: 'https://open.bigmodel.cn/api/paas/v4',
    placeholder: '形如 id.secret（中间有个点）',
    link: 'https://bigmodel.cn/usercenter/proj-mgmt/apikeys',
    linkText: 'bigmodel.cn',
    note: 'glm-4.5-flash 免费；旗舰 glm-5.3 直接改模型名即可'
  }
}

export const PROVIDER_ORDER = ['deepseek', 'siliconflow', 'zhipu']

const STORE_KEY = 'ug_llm_byok'

function load() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE_KEY) || '{}')
    return {
      active: PROVIDER_ORDER.includes(raw.active) ? raw.active : '',
      keys: typeof raw.keys === 'object' && raw.keys ? raw.keys : {},
      models: typeof raw.models === 'object' && raw.models ? raw.models : {}
    }
  } catch {
    return { active: '', keys: {}, models: {} }
  }
}

function save(state) {
  localStorage.setItem(STORE_KEY, JSON.stringify(state))
}

export function getActive() {
  return load().active
}

export function getKey(provider) {
  return (load().keys[provider] || '').trim()
}

export function getModel(provider) {
  const m = (load().models[provider] || '').trim()
  return m || PROVIDER_META[provider]?.model || ''
}

/** 是否已配置可用 Key（选中供应商且已填 Key） */
export function isConfigured() {
  const s = load()
  return !!s.active && !!getKey(s.active)
}

/** 保存某供应商 Key（空串 = 清除） */
export function saveKey(provider, key) {
  if (!PROVIDER_ORDER.includes(provider)) return
  const s = load()
  s.keys[provider] = key.trim()
  // 清掉 Key 的供应商若正是激活态，取消激活
  if (!s.keys[provider] && s.active === provider) s.active = ''
  save(s)
}

/** 设为当前使用的供应商（须已有 Key） */
export function setActive(provider) {
  if (!PROVIDER_ORDER.includes(provider)) return
  const s = load()
  if (!getKey(provider)) return
  s.active = provider
  save(s)
}

/** 覆盖某供应商默认模型名（空串 = 用默认） */
export function saveModel(provider, model) {
  if (!PROVIDER_ORDER.includes(provider)) return
  const s = load()
  s.models[provider] = model.trim()
  save(s)
}

/** 供请求注入的 BYOK 头；未配置时返回空对象 */
export function llmHeaders() {
  const s = load()
  if (!s.active) return {}
  const key = getKey(s.active)
  if (!key) return {}
  return {
    'X-LLM-Provider': s.active,
    'X-LLM-Key': key,
    'X-LLM-Model': getModel(s.active)
  }
}
