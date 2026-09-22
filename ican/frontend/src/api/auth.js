import { api } from './client'

export function register({ username, password, nickname = '' }) {
  return api.post('/auth/register', { username, password, nickname }).then((r) => r.data)
}

export function login({ username, password }) {
  return api.post('/auth/login', { username, password }).then((r) => r.data)
}

export function me() {
  return api.get('/auth/me').then((r) => r.data)
}

export function updateProfile(payload) {
  return api.patch('/auth/profile', payload).then((r) => r.data)
}

export function myStats() {
  return api.get('/auth/me/stats').then((r) => r.data)
}
