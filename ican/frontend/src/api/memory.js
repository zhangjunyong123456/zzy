import { api } from './client'

export function listMemories() {
  return api.get('/memories').then((r) => r.data)
}

export function createMemory(payload) {
  return api.post('/memories', payload).then((r) => r.data)
}

export function renameMemory(id, title) {
  return api.put(`/memories/${id}`, { title }).then((r) => r.data)
}

export function deleteMemory(id) {
  return api.delete(`/memories/${id}`).then((r) => r.data)
}
