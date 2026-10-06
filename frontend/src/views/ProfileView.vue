<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api.js'
import { dateLabel, statusLabel } from '../format.js'
import { session } from '../session.js'

const petitions = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.profile()
    session.user = result.user
    petitions.value = result.petitions || []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="container py-5">
    <div class="page-heading mb-4">
      <p class="eyebrow">Особистий кабінет</p>
      <h1>Ваш профіль</h1>
    </div>
    <div v-if="loading" class="state-panel" role="status">Завантажуємо профіль…</div>
    <div v-else-if="error" class="state-panel error-panel" role="alert">
      <p>{{ error }}</p><button class="btn btn-outline-primary" type="button" @click="load">Повторити</button>
    </div>
    <template v-else>
      <div class="profile-card mb-5">
        <div class="profile-avatar" aria-hidden="true">{{ session.user?.username?.slice(0, 1).toUpperCase() }}</div>
        <div><h2 class="h4 mb-1">{{ session.user?.username }}</h2><p class="text-secondary mb-0">{{ session.user?.email }}</p></div>
        <span v-if="session.user?.is_staff" class="status-pill status-in_review ms-auto">Адміністратор</span>
      </div>
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
        <h2 class="h3 mb-0">Ваші петиції</h2>
        <RouterLink class="btn btn-primary" to="/petitions/new">Створити петицію</RouterLink>
      </div>
      <div v-if="!petitions.length" class="state-panel">Ви ще не створили петицій.</div>
      <div v-else class="list-group petition-table">
        <RouterLink v-for="petition in petitions" :key="petition.id"
          class="list-group-item list-group-item-action d-flex flex-wrap align-items-center justify-content-between gap-3"
          :to="{ name: 'petition', params: { id: petition.id } }">
          <span><strong>{{ petition.title }}</strong><small class="d-block text-secondary mt-1">{{ dateLabel(petition.created_at) }}<span v-if="petition.is_hidden"> · Прихована із загального списку</span></small></span>
          <span class="status-pill" :class="'status-' + petition.status">{{ statusLabel(petition.status) }}</span>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

