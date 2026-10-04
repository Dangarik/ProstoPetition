<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'

const router = useRouter()
const categories = ref([])
const categoryLoading = ref(true)
const categoryError = ref('')
const pending = ref(false)
const error = ref('')
const fieldErrors = ref({})
const form = reactive({ title: '', text: '', category: '' })
const selectedCategory = computed(() => categories.value.find((item) => item.id === Number(form.category)))

async function loadCategories() {
  categoryLoading.value = true
  categoryError.value = ''
  try {
    categories.value = await api.categories()
  } catch (err) {
    categoryError.value = err.message
  } finally {
    categoryLoading.value = false
  }
}

async function submit() {
  error.value = ''
  fieldErrors.value = {}
  if (!form.title.trim() || !form.text.trim() || !form.category) {
    error.value = 'Заповніть усі поля петиції.'
    return
  }
  pending.value = true
  try {
    const petition = await api.createPetition({
      title: form.title.trim(),
      text: form.text.trim(),
      category: Number(form.category),
    })
    router.push({ name: 'petition', params: { id: petition.id } })
  } catch (err) {
    error.value = err.message
    fieldErrors.value = err.fields || {}
  } finally {
    pending.value = false
  }
}
onMounted(loadCategories)
</script>

<template>
  <div class="container py-5">
    <div class="page-heading mb-4"><p class="eyebrow">Ваша ініціатива</p><h1>Створити петицію</h1>
      <p class="text-secondary">Після подання петиція потрапить на модерацію.</p>
    </div>
    <div class="form-card">
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <div v-if="categoryError" class="alert alert-warning" role="alert">{{ categoryError }} <button class="link-button" type="button" @click="loadCategories">Повторити</button></div>
      <form @submit.prevent="submit">
        <div class="mb-4">
          <label class="form-label" for="title">Заголовок</label>
          <input id="title" v-model="form.title" class="form-control" maxlength="255" required placeholder="Коротко опишіть вашу пропозицію" />
          <small v-if="fieldErrors.title" class="text-danger">{{ String(fieldErrors.title) }}</small>
        </div>
        <div class="mb-4">
          <label class="form-label" for="category">Категорія</label>
          <select id="category" v-model="form.category" class="form-select" required :disabled="categoryLoading">
            <option value="" disabled>Оберіть категорію</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
          </select>
          <small v-if="fieldErrors.category" class="text-danger">{{ String(fieldErrors.category) }}</small>
          <small v-if="selectedCategory" class="d-block text-secondary">Термін завершення автоматично визначається від сьогодні: {{ selectedCategory.max_years }} р., {{ selectedCategory.max_months }} міс., {{ selectedCategory.max_days }} дн. Поріг: {{ selectedCategory.vote_threshold ?? 'не задано' }} голосів.</small>
          <small v-if="selectedCategory && !selectedCategory.vote_threshold" class="d-block text-danger">Адміністратор має налаштувати поріг цієї категорії.</small>
          <small v-if="!categoryLoading && !categories.length && !categoryError" class="text-secondary">Категорій ще немає. Зверніться до адміністратора.</small>
        </div>
        <div class="mb-4">
          <label class="form-label" for="text">Повний текст</label>
          <textarea id="text" v-model="form.text" class="form-control" rows="8" required placeholder="Опишіть проблему й запропоноване рішення"></textarea>
          <small v-if="fieldErrors.text" class="text-danger">{{ String(fieldErrors.text) }}</small>
        </div>
        <button class="btn btn-primary px-4" type="submit" :disabled="pending || categoryLoading || !categories.length || (selectedCategory && !selectedCategory.vote_threshold)">{{ pending ? 'Публікуємо…' : 'Подати петицію' }}</button>
      </form>
    </div>
  </div>
</template>

