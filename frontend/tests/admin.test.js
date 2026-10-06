import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createSSRApp, ssrContextKey } from 'vue'
import { routerKey, routeLocationKey } from 'vue-router'

test('category removal handles cancellation, success and errors in the admin view', async () => {
  const server = await createServer({
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    appType: 'custom',
  })
  const originalWindow = globalThis.window
  try {
    const { api } = await server.ssrLoadModule('/src/api.js')
    const category = { id: 7, name: 'Test', vote_threshold: 2, max_years: 1, max_months: 0, max_days: 0 }
    api.categories = async () => [category]
    api.listPetitions = async () => ({ results: [], count: 0 })
    api.statistics = async () => ({ by_status: {} })
    let deletions = 0
    api.deleteCategory = async (id) => {
      assert.equal(id, 7)
      deletions += 1
    }
    const { default: Admin } = await server.ssrLoadModule('/src/views/AdminView.vue')
    const app = createSSRApp({})
    app.provide(routerKey, { push() {} })
    app.provide(routeLocationKey, { query: {}, fullPath: '/admin' })
    app.provide(ssrContextKey, {})
    const state = app.runWithContext(() => Admin.setup({}, { expose() {} }))
    assert.ok(!state.choices.some((choice) => choice.value === 'hidden'))
    assert.deepEqual(state.transitions('active'), ['in_review', 'closed'])
    await Promise.resolve()
    globalThis.window = { confirm: () => false }
    await state.deleteCategory(category)
    assert.equal(deletions, 0)
    assert.equal(state.categories.value.length, 1)
    globalThis.window.confirm = () => true
    await state.deleteCategory(category)
    assert.equal(deletions, 1)
    assert.equal(state.categories.value.length, 0)
    assert.equal(state.categoryDrafts[7], undefined)
    assert.equal(state.categoryMessage.value, 'Категорію успішно видалено.')
    state.categories.value = [category]
    api.deleteCategory = async () => { throw Object.assign(new Error('Conflict'), { status: 409 }) }
    await state.deleteCategory(category)
    assert.equal(state.categories.value.length, 1)
    assert.equal(state.categoryError.value, 'Неможливо видалити категорію, оскільки вона використовується петиціями')
    assert.equal(state.categoryMessage.value, '')
    assert.equal(state.categoryDeletingId.value, null)
    api.deleteCategory = async () => { throw new Error('Offline') }
    await state.deleteCategory(category)
    assert.equal(state.categoryError.value, 'Offline')
    assert.equal(state.categories.value.length, 1)
  } finally {
    globalThis.window = originalWindow
    await server.close()
  }
})
