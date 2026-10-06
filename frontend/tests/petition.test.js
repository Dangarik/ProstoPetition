import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createSSRApp, ssrContextKey } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createRouter, createMemoryHistory } from 'vue-router'

test('expired petition renders its status and completion message without a vote button', async () => {
  const server = await createServer({
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    appType: 'custom',
  })
  try {
    const { api } = await server.ssrLoadModule('/src/api.js')
    const { session } = await server.ssrLoadModule('/src/session.js')
    session.user = { id: 1, username: 'reader', is_staff: false }
    api.petition = async () => ({
      id: 4, title: 'Expired petition', text: 'Text', status: 'expired', is_active: false,
      author: 'author', category_name: 'Test', vote_count: 1, vote_threshold: 5,
      deadline: '2020-01-01T00:00:00Z', created_at: '2019-12-01T00:00:00Z',
    })
    const { default: Petition } = await server.ssrLoadModule('/src/views/PetitionView.vue')
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: {} }, { path: '/petitions/:id', component: {} }],
    })
    const context = createSSRApp({})
    context.use(router)
    context.provide(ssrContextKey, {})
    await router.push('/petitions/4')
    const state = context.runWithContext(() => Petition.setup({}, { expose() {} }))
    await new Promise(setImmediate)
    assert.equal(state.petition.value.status, 'expired')
    const app = createSSRApp({ ...Petition, setup: () => state })
    app.use(router)
    const html = await renderToString(app)
    assert.ok(html.includes('Термін дії минув'))
    assert.ok(html.includes('Термін збору голосів завершено'))
    assert.ok(!html.includes('Підтримати петицію'))
    assert.ok(!html.includes('Увійти, щоб підтримати'))
  } finally {
    await server.close()
  }
})
