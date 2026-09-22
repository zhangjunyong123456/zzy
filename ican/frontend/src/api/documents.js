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

export function configStatus() {
  return api.get('/config/status').then((r) => r.data)
}

export function saveApiKey(provider, apiKey) {
  return api.post('/config/api-key', { provider, api_key: apiKey }).then((r) => r.data)
}

export function setProvider(provider) {
  return api.post('/config/provider', { provider }).then((r) => r.data)
}

export function setModel(provider, model) {
  return api.post('/config/model', { provider, model }).then((r) => r.data)
}
