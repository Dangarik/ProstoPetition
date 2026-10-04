import { reactive } from 'vue'
import { api, clearCsrfToken, setForbiddenHandler } from './api.js'

export const session = reactive({
  user: null,
  ready: false,
  error: '',
})

let pending = null

export async function ensureSession(force = false) {
  if (session.ready && !force) return session.user
  if (pending) return pending
  pending = (async () => {
    try {
      const data = await api.profile()
      session.user = data.user
      session.error = ''
    } catch (error) {
      if (!error.network) session.user = null
      session.error = error.network ? error.message : ''
    } finally {
      session.ready = true
      pending = null
    }
    return session.user
  })()
  return pending
}

export async function signIn(data) {
  const result = await api.login(data)
  clearCsrfToken()
  session.user = result.user
  session.error = ''
  return result.user
}

export async function signUp(data) {
  const result = await api.register(data)
  clearCsrfToken()
  session.user = result.user
  session.error = ''
  return result.user
}

export async function signOut() {
  try {
    await api.logout()
  } catch (error) {
    await ensureSession(true)
    if (session.user) throw error
  }
  clearCsrfToken()
  session.user = null
}

setForbiddenHandler((path) => {
  if (path === '/auth/profile/') {
    session.user = null
  } else {
    void ensureSession(true)
  }
})

