import { api } from './client'

/** 上传对话附件；返回 {id, filename, mime, kind, size, extracted_text, warning, url} */
export function uploadAttachment(file, sessionId = null) {
  const form = new FormData()
  form.append('file', file)
  if (sessionId) form.append('session_id', sessionId)
  return api.post('/chat/upload', form).then((r) => r.data)
}

/* <img> 带不了 Bearer 头，图片预览统一走 axios blob → objectURL，并按附件 id 缓存 */
const urlCache = new Map()

export async function attachmentObjectURL(id) {
  if (urlCache.has(id)) return urlCache.get(id)
  const resp = await api.get(`/attachments/${id}/raw`, { responseType: 'blob' })
  const url = URL.createObjectURL(resp.data)
  urlCache.set(id, url)
  return url
}

/** 下载附件原文件（带鉴权取 blob 后触发保存） */
export async function downloadAttachment(id, filename) {
  const resp = await api.get(`/attachments/${id}/raw`, { responseType: 'blob' })
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || '附件'
  a.click()
  URL.revokeObjectURL(url)
}
