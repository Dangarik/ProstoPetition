import test from 'node:test'
import assert from 'node:assert/strict'
import { api, ApiError, clearCsrfToken } from '../src/api.js'

const originalFetch = globalThis.fetch

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

test.afterEach(() => {
  globalThis.fetch = originalFetch
  clearCsrfToken()
})

test('mutation fetches CSRF and sends JSON with session cookies', async () => {
  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    if (url === '/api/auth/csrf/') return json({ csrfToken: 'test-token' })
    return json({ id: 10, petition: 4, vote_count: 2 }, 201)
  }
  const vote = await api.vote(4)
  assert.equal(vote.vote_count, 2)
  assert.equal(calls.length, 2)
  assert.equal(calls[0].url, '/api/auth/csrf/')
  assert.equal(calls[1].url, '/api/petitions/4/vote/')
  assert.equal(calls[1].options.method, 'POST')
  assert.equal(calls[1].options.credentials, 'same-origin')
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'test-token')
  assert.equal(calls[1].options.body, '{}')
})

test('filters use the actual list endpoint and encode search', async () => {
  let requested
  globalThis.fetch = async (url) => {
    requested = url
    return json({ count: 0, next: null, previous: null, results: [] })
  }
  await api.listPetitions({ search: 'вода школа', status: 'active', page: 2 })
  assert.match(requested, /^\/api\/petitions\/\?/)
  assert.match(requested, /search=%D0%B2%D0%BE%D0%B4%D0%B0\+%D1%88%D0%BA%D0%BE%D0%BB%D0%B0/)
  assert.match(requested, /status=active/)
  assert.match(requested, /page=2/)
})

test('conflict keeps HTTP status and server message', async () => {
  globalThis.fetch = async (url) => url.endsWith('/auth/csrf/')
    ? json({ csrfToken: 'test-token' })
    : json({ detail: 'Голос уже подано.' }, 409)
  await assert.rejects(api.vote(4), (error) =>
    error instanceof ApiError && error.status === 409 && error.message === 'Голос уже подано.')
})

test('network failures are available for retry UI', async () => {
  globalThis.fetch = async () => { throw new TypeError('offline') }
  await assert.rejects(api.categories(), (error) =>
    error instanceof ApiError && error.network === true)
})

test('403 clears CSRF token for the next explicit retry', async () => {
  let csrfFetches = 0
  globalThis.fetch = async (url) => {
    if (url.endsWith('/auth/csrf/')) {
      csrfFetches += 1
      return json({ csrfToken: 'new-token-' + csrfFetches })
    }
    return json({ detail: 'CSRF failed' }, 403)
  }
  await assert.rejects(api.vote(4), (error) => error.status === 403)
  await assert.rejects(api.vote(4), (error) => error.status === 403)
  assert.equal(csrfFetches, 2)
})

