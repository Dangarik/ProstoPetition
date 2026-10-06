import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import Login from '../../src/views/LoginView.vue'
import Home from '../../src/views/HomeView.vue'
import Detail from '../../src/views/PetitionView.vue'
import Create from '../../src/views/CreatePetitionView.vue'
import Admin from '../../src/views/AdminView.vue'
import { api } from '../../src/api.js'
import { session } from '../../src/session.js'

vi.mock('../../src/api.js', () => ({
  api: Object.fromEntries([
    'login', 'profile', 'categories', 'listPetitions', 'petition', 'createPetition',
    'vote', 'statistics', 'deleteCategory', 'moderationList', 'setPetitionVisibility',
  ].map((name) => [name, vi.fn()])),
  clearCsrfToken: vi.fn(),
  setForbiddenHandler: vi.fn(),
}))

const category = { id: 1, name: 'Освіта', vote_threshold: 5, max_years: 0, max_months: 1, max_days: 0 }
const petition = {
  id: 4, title: 'Чиста вода', text: 'Текст петиції', author: 'author', category_name: 'Освіта',
  status: 'active', is_active: true, vote_count: 1, vote_threshold: 5,
  deadline: '2030-01-01T00:00:00Z', created_at: '2026-01-01T00:00:00Z',
}
const wrappers = []

async function view(component, path) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: {} },
      { path: '/login', name: 'login', component: {} },
      { path: '/register', name: 'register', component: {} },
      { path: '/profile', name: 'profile', component: {} },
      { path: '/petitions/new', name: 'create', component: {} },
      { path: '/petitions/:id', name: 'petition', component: {} },
      { path: '/admin', name: 'admin', component: {} },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, { global: { plugins: [router] } })
  wrappers.push(wrapper)
  return { wrapper, router }
}

function deleteButton(wrapper) {
  return wrapper.findAll('button').find((button) => button.text() === 'Видалити')
}

beforeEach(() => {
  vi.resetAllMocks()
  session.user = { id: 1, username: 'reader', is_staff: true }
  sessionStorage.clear()
  api.categories.mockResolvedValue([category])
  api.listPetitions.mockResolvedValue({ count: 0, results: [] })
  api.moderationList.mockResolvedValue({ count: 0, results: [] })
  api.statistics.mockResolvedValue({ users: 1, petitions: 0, votes: 0, by_status: { moderation: 0 } })
  api.petition.mockResolvedValue({ ...petition })
})

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
})

describe('Login', () => {
  it('submits credentials and navigates to profile', async () => {
    api.login.mockResolvedValue({ user: { id: 2, username: 'author' } })
    const { wrapper, router } = await view(Login, '/login')
    await wrapper.get('#username').setValue(' author ')
    await wrapper.get('#password').setValue('secret')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.login).toHaveBeenCalledWith({ username: 'author', password: 'secret' })
    expect(router.currentRoute.value.path).toBe('/profile')
  })

  it('shows the API error', async () => {
    api.login.mockRejectedValue(new Error('Неправильний пароль'))
    const { wrapper } = await view(Login, '/login')
    await wrapper.get('#username').setValue('author')
    await wrapper.get('#password').setValue('wrong')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role=alert]').text()).toBe('Неправильний пароль')
  })
})

describe('Petition list', () => {
  it('shows loading, fetches data and renders a petition', async () => {
    let resolve
    api.listPetitions.mockReturnValue(new Promise((done) => { resolve = done }))
    const { wrapper } = await view(Home, '/')
    expect(wrapper.text()).toContain('Завантажуємо петиції')
    resolve({ count: 1, results: [petition] })
    await flushPromises()
    expect(api.listPetitions).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Чиста вода')
    expect(wrapper.text()).not.toContain('Завантажуємо петиції')
  })

  it('shows API failure and supports retry', async () => {
    api.listPetitions.mockRejectedValueOnce(new Error('Немає з’єднання'))
    const { wrapper } = await view(Home, '/')
    await flushPromises()
    expect(wrapper.get('[role=alert]').text()).toContain('Немає з’єднання')
    await wrapper.get('[role=alert] button').trigger('click')
    await flushPromises()
    expect(api.listPetitions).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[role=alert]').exists()).toBe(false)
  })

  it('shows an empty result', async () => {
    const { wrapper } = await view(Home, '/')
    await flushPromises()
    expect(wrapper.text()).toContain('За цими умовами петицій немає.')
  })
})

describe('Petition detail', () => {
  it('offers voting and changes the count only after server confirmation', async () => {
    let resolve
    api.vote.mockReturnValue(new Promise((done) => { resolve = done }))
    const { wrapper } = await view(Detail, '/petitions/4')
    await flushPromises()
    const button = wrapper.findAll('button').find((item) => item.text() === 'Підтримати петицію')
    expect(button.exists()).toBe(true)
    await button.trigger('click')
    expect(api.vote).toHaveBeenCalledWith(4)
    expect(wrapper.get('.vote-tally strong').text()).toBe('1')
    resolve({ vote_count: 2, status: 'active', is_active: true })
    await flushPromises()
    expect(wrapper.get('.vote-tally strong').text()).toBe('2')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('shows the expired message without a voting button', async () => {
    api.petition.mockResolvedValue({ ...petition, status: 'expired', is_active: false })
    const { wrapper } = await view(Detail, '/petitions/4')
    await flushPromises()
    expect(wrapper.text()).toContain('Термін збору голосів завершено')
    expect(wrapper.text()).toContain('Термін дії минув')
    expect(wrapper.text()).not.toContain('Підтримати петицію')
    expect(api.vote).not.toHaveBeenCalled()
  })
})

describe('Create petition', () => {
  async function submit(wrapper) {
    await flushPromises()
    await wrapper.get('#title').setValue('Нова петиція')
    await wrapper.get('#text').setValue('Текст')
    await wrapper.get('#category').setValue('1')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
  }

  it('sends title, text and category and opens the created petition', async () => {
    api.createPetition.mockResolvedValue({ id: 8 })
    const { wrapper, router } = await view(Create, '/petitions/new')
    await submit(wrapper)
    expect(api.createPetition).toHaveBeenCalledWith({ title: 'Нова петиція', text: 'Текст', category: 1 })
    expect(router.currentRoute.value.path).toBe('/petitions/8')
  })

  it('shows field validation errors', async () => {
    api.createPetition.mockRejectedValue(Object.assign(new Error('Помилка перевірки'), {
      fields: { title: ['Заголовок надто довгий'] },
    }))
    const { wrapper } = await view(Create, '/petitions/new')
    await submit(wrapper)
    expect(wrapper.text()).toContain('Заголовок надто довгий')
    expect(wrapper.get('[role=alert]').text()).toBe('Помилка перевірки')
  })
})

describe('Admin category deletion', () => {
  it('shows the delete button and cancellation makes no DELETE request', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper } = await view(Admin, '/admin')
    await flushPromises()
    await deleteButton(wrapper).trigger('click')
    expect(confirm).toHaveBeenCalledWith('Ви впевнені, що хочете видалити цю категорію?')
    expect(api.deleteCategory).not.toHaveBeenCalled()
  })

  it('removes a category from the list after successful deletion', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    api.deleteCategory.mockResolvedValue(null)
    const { wrapper } = await view(Admin, '/admin')
    await flushPromises()
    await deleteButton(wrapper).trigger('click')
    await flushPromises()
    expect(api.deleteCategory).toHaveBeenCalledWith(1)
    expect(deleteButton(wrapper)).toBeUndefined()
    expect(wrapper.text()).toContain('Категорію успішно видалено')
  })

  it('keeps the category and shows the 409 conflict', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    api.deleteCategory.mockRejectedValue(Object.assign(new Error('Conflict'), { status: 409 }))
    const { wrapper } = await view(Admin, '/admin')
    await flushPromises()
    await deleteButton(wrapper).trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Неможливо видалити категорію, оскільки вона використовується петиціями')
    expect(deleteButton(wrapper)).toBeDefined()
  })
})

describe('Admin petition visibility', () => {
  it('hides and restores an expired petition after server confirmation', async () => {
    api.moderationList.mockResolvedValue({ count: 1, results: [{ ...petition, status: 'expired', is_hidden: false }] })
    let resolve
    api.setPetitionVisibility.mockReturnValueOnce(new Promise((done) => { resolve = done }))
    const { wrapper } = await view(Admin, '/admin?status=expired')
    await flushPromises()
    const button = () => wrapper.findAll('button').find((item) => ['Приховати', 'Повернути зі схованих'].includes(item.text()))
    await button().trigger('click')
    expect(api.setPetitionVisibility).toHaveBeenCalledWith(4, true)
    expect(button().text()).toBe('Приховати')
    resolve({ is_hidden: true })
    await flushPromises()
    expect(button().text()).toBe('Повернути зі схованих')
    api.setPetitionVisibility.mockResolvedValueOnce({ is_hidden: false })
    await button().trigger('click')
    await flushPromises()
    expect(api.setPetitionVisibility).toHaveBeenLastCalledWith(4, false)
    expect(button().text()).toBe('Приховати')
  })

  it('keeps visibility unchanged and shows a server error', async () => {
    api.moderationList.mockResolvedValue({ count: 1, results: [{ ...petition, status: 'rejected', is_hidden: false }] })
    api.setPetitionVisibility.mockRejectedValue(new Error('Недостатньо прав'))
    const { wrapper } = await view(Admin, '/admin?status=rejected')
    await flushPromises()
    const button = wrapper.findAll('button').find((item) => item.text() === 'Приховати')
    await button.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Недостатньо прав')
    expect(button.text()).toBe('Приховати')
  })
})
