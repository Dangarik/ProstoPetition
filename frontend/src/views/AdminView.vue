<script setup>
import { reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { STATUS, dateLabel, excerpt, statusLabel } from '../format.js'

const route = useRoute()
const router = useRouter()
const stats = ref(null)
const petitions = ref([])
const categories = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')
const statsError = ref('')
const categoryError = ref('')
const newCategory = reactive({ name: '', vote_threshold: '', max_years: 1, max_months: 0, max_days: 0 })
const categoryDrafts = reactive({})
const categoryPending = ref(false)
const categoryPendingId = ref(null)
const pendingId = ref(null)
const actionErrors = reactive({})
const drafts = reactive({})
const currentStatus = ref('moderation')
const page = ref(1)

const choices = [
  { value: 'moderation', label: 'На модерації' },
  { value: 'active', label: 'Активна' },
  { value: 'rejected', label: 'Відхилена' },
  { value: 'hidden', label: 'Прихована' },
  { value: 'in_review', label: 'На розгляді' },
  { value: 'answered', label: 'З відповіддю' },
  { value: 'closed', label: 'Закрита' },
]

function transitions(status) {
  if (status === 'moderation') return ['active', 'rejected']
  if (status === 'active') return ['hidden', 'in_review', 'closed']
  return []
}

function categoryPayload(draft) {
  const values = ['max_years', 'max_months', 'max_days'].map((key) => Number(draft[key]))
  const threshold = Number(draft.vote_threshold)
  if (!Number.isInteger(threshold) || threshold < 1) {
    throw new Error('Вкажіть додатний цілий поріг голосів для категорії.')
  }
  if (values.some((value) => !Number.isInteger(value) || value < 0) ||
      values[0] > 100 || values[1] > 11 || values[2] > 366 || !values.some(Boolean)) {
    throw new Error('Вкажіть додатний ліміт: 0–100 років, 0–11 місяців і 0–366 днів.')
  }
  return { name: draft.name.trim(), vote_threshold: threshold,
    max_years: values[0], max_months: values[1], max_days: values[2] }
}

async function loadStats() {
  statsError.value = ''
  try { stats.value = await api.statistics() }
  catch (err) { statsError.value = err.message }
}

async function loadCategories() {
  categoryError.value = ''
  try {
    categories.value = await api.categories()
    for (const category of categories.value) categoryDrafts[category.id] = { ...category }
  }
  catch (err) { categoryError.value = err.message }
}

async function loadPetitions() {
  loading.value = true
  error.value = ''
  try {
    const data = currentStatus.value === 'all'
      ? await api.moderationList(page.value)
      : await api.listPetitions({ status: currentStatus.value, page: page.value })
    petitions.value = data.results || []
    count.value = data.count || 0
    for (const petition of petitions.value) {
      drafts[petition.id] = { status: transitions(petition.status)[0] || '', reason: '', text: '' }
      actionErrors[petition.id] = ''
    }
  } catch (err) {
    petitions.value = []
    count.value = 0
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function setFilter(value, newPage = 1) {
  router.push({ name: 'admin', query: { status: value, page: newPage } })
}

async function saveStatus(petition) {
  const draft = drafts[petition.id]
  actionErrors[petition.id] = ''
  if (!draft?.status) return
  if (['rejected', 'hidden'].includes(draft.status) && !draft.reason.trim()) {
    actionErrors[petition.id] = 'Вкажіть причину відхилення або приховування.'
    return
  }
  pendingId.value = petition.id
  try {
    await api.changeStatus(petition.id, { status: draft.status, reason: draft.reason.trim() })
    await Promise.all([loadPetitions(), loadStats()])
  } catch (err) {
    actionErrors[petition.id] = err.message
  } finally {
    pendingId.value = null
  }
}

async function publish(petition) {
  const draft = drafts[petition.id]
  actionErrors[petition.id] = ''
  if (!draft?.text.trim()) {
    actionErrors[petition.id] = 'Введіть текст офіційної відповіді.'
    return
  }
  pendingId.value = petition.id
  try {
    await api.publishResponse(petition.id, { text: draft.text.trim() })
    await Promise.all([loadPetitions(), loadStats()])
  } catch (err) {
    actionErrors[petition.id] = err.message
  } finally {
    pendingId.value = null
  }
}

async function addCategory() {
  categoryError.value = ''
  if (!newCategory.name.trim()) return
  categoryPending.value = true
  try {
    await api.createCategory(categoryPayload(newCategory))
    Object.assign(newCategory, { name: '', vote_threshold: '', max_years: 1, max_months: 0, max_days: 0 })
    await loadCategories()
  } catch (err) {
    categoryError.value = err.message
  } finally {
    categoryPending.value = false
  }
}

async function saveCategory(category) {
  categoryError.value = ''
  categoryPendingId.value = category.id
  try {
    await api.updateCategory(category.id, categoryPayload(categoryDrafts[category.id]))
    await loadCategories()
  } catch (err) {
    categoryError.value = err.message
  } finally {
    categoryPendingId.value = null
  }
}

watch(() => route.fullPath, () => {
  currentStatus.value = choices.some((item) => item.value === route.query.status) || route.query.status === 'all'
    ? route.query.status : 'moderation'
  page.value = Math.max(1, Number(route.query.page) || 1)
  loadPetitions()
}, { immediate: true })
loadStats()
loadCategories()
</script>

<template>
  <div class="container py-5">
    <div class="page-heading mb-4"><p class="eyebrow">Адміністрування</p><h1>Модерація петицій</h1>
      <p class="text-secondary">Перевіряйте звернення, керуйте статусами та публікуйте відповіді.</p>
    </div>
    <div v-if="statsError" class="alert alert-warning" role="alert">{{ statsError }} <button type="button" class="link-button" @click="loadStats">Повторити</button></div>
    <div v-if="stats" class="row g-3 mb-5">
      <div v-for="item in [{ label: 'Користувачі', value: stats.users }, { label: 'Петиції', value: stats.petitions }, { label: 'Голоси', value: stats.votes }, { label: 'На модерації', value: stats.by_status.moderation }]"
        :key="item.label" class="col-6 col-lg-3">
        <div class="stat-card"><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
      </div>
    </div>
    <div class="row g-4">
      <div class="col-lg-8">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
          <h2 class="h4 mb-0">Петиції <span class="text-secondary small">({{ count }})</span></h2>
          <div class="d-flex align-items-center gap-2"><label class="form-label mb-0" for="admin-filter">Статус</label>
            <select id="admin-filter" class="form-select" :value="currentStatus" @change="setFilter($event.target.value)">
              <option value="all">Усі</option>
              <option v-for="choice in choices" :key="choice.value" :value="choice.value">{{ choice.label }}</option>
            </select>
          </div>
        </div>
        <div v-if="loading" class="state-panel" role="status">Завантажуємо петиції…</div>
        <div v-else-if="error" class="state-panel error-panel" role="alert"><p>{{ error }}</p><button class="btn btn-outline-primary" type="button" @click="loadPetitions">Повторити</button></div>
        <div v-else-if="!petitions.length" class="state-panel">Петицій із таким статусом немає.</div>
        <div v-else class="d-grid gap-3">
          <article v-for="petition in petitions" :key="petition.id" class="moderation-card">
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-2">
              <div><span class="status-pill" :class="'status-' + petition.status">{{ statusLabel(petition.status) }}</span>
                <h3 class="h5 mt-3 mb-1"><RouterLink :to="{ name: 'petition', params: { id: petition.id } }">{{ petition.title }}</RouterLink></h3>
                <small class="text-secondary">{{ petition.author }} · {{ petition.category_name }} · {{ dateLabel(petition.created_at) }}</small>
              </div>
              <span class="vote-count"><strong>{{ petition.vote_count }}</strong><span v-if="petition.vote_threshold"> / {{ petition.vote_threshold }}</span> голосів</span>
            </div>
            <p class="text-secondary mt-3 mb-3">{{ excerpt(petition.text, 260) }}</p>
            <div v-if="petition.moderation_reason" class="alert alert-warning py-2">Причина: {{ petition.moderation_reason }}</div>
            <div v-if="transitions(petition.status).length" class="row g-2 align-items-end">
              <div class="col-md-4"><label class="form-label" :for="'action-' + petition.id">Новий статус</label>
                <select :id="'action-' + petition.id" v-model="drafts[petition.id].status" class="form-select">
                  <option v-for="value in transitions(petition.status)" :key="value" :value="value">{{ STATUS[value] }}</option>
                </select>
              </div>
              <div v-if="['rejected', 'hidden'].includes(drafts[petition.id].status)" class="col-md-5">
                <label class="form-label" :for="'reason-' + petition.id">Причина</label>
                <input :id="'reason-' + petition.id" v-model="drafts[petition.id].reason" class="form-control" maxlength="1000" />
              </div>
              <div class="col-md-auto"><button class="btn btn-primary" type="button" :disabled="pendingId !== null" @click="saveStatus(petition)">Зберегти</button></div>
            </div>
            <div v-if="petition.status === 'in_review'" class="mt-3">
              <label class="form-label" :for="'response-' + petition.id">Офіційна відповідь</label>
              <textarea :id="'response-' + petition.id" v-model="drafts[petition.id].text" class="form-control mb-2" rows="3"></textarea>
              <button class="btn btn-primary" type="button" :disabled="pendingId !== null" @click="publish(petition)">Опублікувати відповідь</button>
            </div>
            <div v-if="actionErrors[petition.id]" class="alert alert-danger mt-3 mb-0" role="alert">
              {{ actionErrors[petition.id] }} <button class="link-button" type="button" @click="loadPetitions">Оновити</button>
            </div>
          </article>
          <nav v-if="count > 20" class="d-flex justify-content-between align-items-center mt-2" aria-label="Сторінки модерації">
            <button class="btn btn-outline-secondary" type="button" :disabled="page <= 1" @click="setFilter(currentStatus, page - 1)">← Назад</button>
            <span>{{ page }} / {{ Math.ceil(count / 20) }}</span>
            <button class="btn btn-outline-secondary" type="button" :disabled="page >= Math.ceil(count / 20)" @click="setFilter(currentStatus, page + 1)">Далі →</button>
          </nav>
        </div>
      </div>
      <aside class="col-lg-4">
        <div class="filter-panel">
          <h2 class="h5 mb-3">Категорії</h2>
          <div v-if="categoryError" class="alert alert-warning" role="alert">{{ categoryError }} <button class="link-button" type="button" @click="loadCategories">Повторити</button></div>
          <div v-if="categories.length" class="d-grid gap-3 mb-4">
            <form v-for="category in categories" :key="category.id" class="border rounded p-3" @submit.prevent="saveCategory(category)">
              <strong class="d-block mb-2">{{ category.name }}</strong>
              <label class="form-label small" :for="'category-threshold-' + category.id">Поріг голосів</label>
              <input :id="'category-threshold-' + category.id" v-model.number="categoryDrafts[category.id].vote_threshold"
                class="form-control mb-2" type="number" min="1" step="1" required />
              <div class="row g-2 mb-2">
                <div v-for="field in [{ key: 'max_years', label: 'Років', max: 100 }, { key: 'max_months', label: 'Місяців', max: 11 }, { key: 'max_days', label: 'Днів', max: 366 }]"
                  :key="field.key" class="col-4">
                  <label class="form-label small" :for="'category-' + category.id + '-' + field.key">{{ field.label }}</label>
                  <input :id="'category-' + category.id + '-' + field.key" v-model.number="categoryDrafts[category.id][field.key]"
                    class="form-control" type="number" min="0" :max="field.max" step="1" required />
                </div>
              </div>
              <button class="btn btn-outline-primary btn-sm" type="submit" :disabled="categoryPendingId !== null">{{ categoryPendingId === category.id ? 'Зберігаємо…' : 'Зберегти ліміт' }}</button>
            </form>
          </div>
          <p v-else class="text-secondary">Категорій ще немає.</p>
          <form @submit.prevent="addCategory">
            <label class="form-label" for="new-category">Нова категорія</label>
            <input id="new-category" v-model="newCategory.name" class="form-control mb-2" maxlength="100" required />
            <label class="form-label" for="new-category-threshold">Поріг голосів</label>
            <input id="new-category-threshold" v-model.number="newCategory.vote_threshold" class="form-control mb-2"
              type="number" min="1" step="1" required />
            <div class="row g-2 mb-3">
              <div v-for="field in [{ key: 'max_years', label: 'Років', max: 100 }, { key: 'max_months', label: 'Місяців', max: 11 }, { key: 'max_days', label: 'Днів', max: 366 }]"
                :key="field.key" class="col-4">
                <label class="form-label small" :for="'new-' + field.key">{{ field.label }}</label>
                <input :id="'new-' + field.key" v-model.number="newCategory[field.key]" class="form-control"
                  type="number" min="0" :max="field.max" step="1" required />
              </div>
            </div>
            <button class="btn btn-outline-primary w-100" type="submit" :disabled="categoryPending">{{ categoryPending ? 'Додаємо…' : 'Додати категорію' }}</button>
          </form>
        </div>
      </aside>
    </div>
  </div>
</template>

