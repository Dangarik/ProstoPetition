<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { PUBLIC_STATUSES, STATUS } from '../format.js'
import PetitionCard from '../components/PetitionCard.vue'

const route = useRoute()
const router = useRouter()
const categories = ref([])
const petitions = ref([])
const count = ref(0)
const loading = ref(false)
const error = ref('')
const categoryError = ref('')
const filters = reactive({ search: '', category: '', status: '', ordering: '-created_at' })
const page = ref(1)
let controller = null

function syncFromRoute() {
  filters.search = String(route.query.search || '')
  filters.category = String(route.query.category || '')
  filters.status = PUBLIC_STATUSES.includes(route.query.status) ? route.query.status : ''
  filters.ordering = ['created_at', '-created_at', 'title', '-title', 'vote_count', '-vote_count'].includes(route.query.ordering)
    ? route.query.ordering : '-created_at'
  page.value = Math.max(1, Number(route.query.page) || 1)
}

async function loadCategories() {
  categoryError.value = ''
  try {
    categories.value = await api.categories()
  } catch (err) {
    categoryError.value = err.message
  }
}

async function loadPetitions() {
  controller?.abort()
  controller = new AbortController()
  const activeController = controller
  loading.value = true
  error.value = ''
  try {
    const result = await api.listPetitions({
      search: route.query.search || '',
      category: route.query.category || '',
      status: route.query.status || '',
      ordering: route.query.ordering || '-created_at',
      page: route.query.page || 1,
    }, { signal: activeController.signal })
    petitions.value = result.results || []
    count.value = result.count || 0
  } catch (err) {
    if (err.name !== 'AbortError') {
      petitions.value = []
      count.value = 0
      error.value = err.message
    }
  } finally {
    if (controller === activeController) loading.value = false
  }
}

function applyFilters() {
  router.push({
    name: 'home',
    query: {
      ...(filters.search.trim() ? { search: filters.search.trim() } : {}),
      ...(filters.category ? { category: filters.category } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.ordering !== '-created_at' ? { ordering: filters.ordering } : {}),
    },
  })
}

function changePage(nextPage) {
  router.push({ name: 'home', query: { ...route.query, page: nextPage } })
}

watch(() => route.fullPath, () => {
  syncFromRoute()
  loadPetitions()
}, { immediate: true })
loadCategories()
</script>

<template>
  <section class="hero">
    <div class="container py-5">
      <div class="hero-copy">
        <p class="eyebrow">Громадські ініціативи</p>
        <h1>Ваша ідея може змінити місто.</h1>
        <p class="lead mb-0">Читайте петиції, підтримуйте важливе та стежте за офіційними відповідями.</p>
      </div>
    </div>
  </section>
  <section class="container py-5">
    <div class="section-heading d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div><p class="eyebrow mb-2">Знайдіть важливе</p><h2 class="h3 mb-0">Петиції громади</h2></div>
      <span class="text-secondary">{{ count }} петицій</span>
    </div>
    <div class="row g-4">
      <aside class="col-lg-3">
        <form class="filter-panel" @submit.prevent="applyFilters">
          <h3 class="h5 mb-4">Пошук і фільтри</h3>
          <div class="mb-3">
            <label class="form-label" for="search">Пошук</label>
            <input id="search" v-model="filters.search" class="form-control" type="search" placeholder="Заголовок або текст" />
          </div>
          <div class="mb-3">
            <label class="form-label" for="category">Категорія</label>
            <select id="category" v-model="filters.category" class="form-select">
              <option value="">Усі категорії</option>
              <option v-for="category in categories" :key="category.id" :value="String(category.id)">{{ category.name }}</option>
            </select>
            <div v-if="categoryError" class="form-text text-danger">{{ categoryError }} <button type="button" class="link-button" @click="loadCategories">Повторити</button></div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="status">Статус</label>
            <select id="status" v-model="filters.status" class="form-select">
              <option value="">Усі публічні</option>
              <option v-for="status in PUBLIC_STATUSES" :key="status" :value="status">{{ STATUS[status] }}</option>
            </select>
          </div>
          <div class="mb-4">
            <label class="form-label" for="ordering">Сортування</label>
            <select id="ordering" v-model="filters.ordering" class="form-select">
              <option value="-created_at">Спочатку нові</option>
              <option value="created_at">Спочатку старі</option>
              <option value="-vote_count">Найпопулярніші</option>
              <option value="vote_count">Найменше голосів</option>
              <option value="title">За назвою А–Я</option>
              <option value="-title">За назвою Я–А</option>
            </select>
          </div>
          <button class="btn btn-primary w-100" type="submit">Застосувати</button>
        </form>
      </aside>
      <div class="col-lg-9">
        <div v-if="loading" class="state-panel" role="status">Завантажуємо петиції…</div>
        <div v-else-if="error" class="state-panel error-panel" role="alert">
          <p>{{ error }}</p><button class="btn btn-outline-primary" type="button" @click="loadPetitions">Повторити</button>
        </div>
        <div v-else-if="!petitions.length" class="state-panel">За цими умовами петицій немає. Спробуйте змінити фільтри.</div>
        <template v-else>
          <div class="row g-3">
            <div v-for="petition in petitions" :key="petition.id" class="col-md-6">
              <PetitionCard :petition="petition" />
            </div>
          </div>
          <nav v-if="count > 20" class="d-flex justify-content-between align-items-center mt-4" aria-label="Сторінки петицій">
            <button class="btn btn-outline-secondary" type="button" :disabled="page <= 1" @click="changePage(page - 1)">← Назад</button>
            <span>Сторінка {{ page }} з {{ Math.ceil(count / 20) }}</span>
            <button class="btn btn-outline-secondary" type="button" :disabled="page >= Math.ceil(count / 20)" @click="changePage(page + 1)">Далі →</button>
          </nav>
        </template>
      </div>
    </div>
  </section>
</template>


