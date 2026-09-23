import { api } from './client'

export function listDocuments() {
  return api.get('/documents').then((r) => r.data)
}

export function uploadDocument(file, scene) {
  const form = new FormData()
  form.append('file', file)
  form.append('scene', scene)
  return api.post('/documents/upload', form).then((r) => r.data)
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`).then((r) => r.data)
}

export function listSessions() {
  return api.get('/sessions').then((r) => r.data)
}

export function createSession() {
  return api.post('/sessions').then((r) => r.data)
}

export function getSession(id) {
  return api.get(`/sessions/${id}`).then((r) => r.data)
}

export function deleteSession(id) {
  return api.delete(`/sessions/${id}`).then((r) => r.data)
}

/** 在线校验用户自带的模型 Key 是否可用 */
export function verifyKey(provider, apiKey, model = '') {
  return api.post('/config/verify-key', { provider, api_key: apiKey, model }).then((r) => r.data)
}
