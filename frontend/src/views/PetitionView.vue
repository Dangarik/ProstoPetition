<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { confirmedVoteKey, dateLabel, statusLabel } from '../format.js'
import { session } from '../session.js'

const route = useRoute()
const router = useRouter()
const petition = ref(null)
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const actionMessage = ref('')
const pending = ref(false)
const confirmedVote = ref(false)
const copied = ref(false)

const canDelete = computed(() => petition.value && session.user &&
  petition.value.author === session.user.username &&
  petition.value.vote_count === 0 &&
  !['in_review', 'answered', 'closed'].includes(petition.value.status))
const voteUnavailableMessage = computed(() => {
  if (petition.value?.status === 'expired') return 'Термін збору голосів завершено'
  if (petition.value?.status === 'in_review') return 'Петицію передано на розгляд.'
  if (petition.value?.status === 'active' && !petition.value.vote_threshold) {
    return 'Адміністратор має налаштувати поріг категорії.'
  }
  return 'Голосування завершено або ще не розпочалося.'
})

function readConfirmedVote() {
  if (!session.user || !petition.value) return false
  try { return sessionStorage.getItem(confirmedVoteKey(session.user.id, petition.value.id)) === '1' }
  catch { return false }
}

async function load() {
  loading.value = true
  error.value = ''
  actionError.value = ''
  try {
    petition.value = await api.petition(route.params.id)
    confirmedVote.value = readConfirmedVote()
  } catch (err) {
    petition.value = null
    error.value = err.status === 404 ? 'Петицію не знайдено або вона недоступна для перегляду.' : err.message
  } finally {
    loading.value = false
  }
}

async function vote() {
  if (!session.user) {
    router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  if (!petition.value?.is_active || confirmedVote.value || pending.value) return
  pending.value = true
  actionError.value = ''
  actionMessage.value = ''
  try {
    const result = await api.vote(petition.value.id)
    petition.value.vote_count = result.vote_count
    petition.value.status = result.status
    petition.value.is_active = result.is_active
    confirmedVote.value = true
    try { sessionStorage.setItem(confirmedVoteKey(session.user.id, petition.value.id), '1') } catch {}
    actionMessage.value = result.status === 'in_review'
      ? 'Ваш голос зараховано. Петицію передано на розгляд.'
      : 'Ваш голос зараховано.'
  } catch (err) {
    actionError.value = err.message
    if (err.status === 409) {
      try { petition.value = await api.petition(petition.value.id) } catch {}
    }
  } finally {
    pending.value = false
  }
}

async function copyLink() {
  actionError.value = ''
  copied.value = false
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
  } catch {
    actionError.value = 'Не вдалося скопіювати посилання. Скопіюйте адресу сторінки вручну.'
  }
}

async function remove() {
  if (!petition.value || !window.confirm('Видалити цю петицію без можливості відновлення?')) return
  pending.value = true
  actionError.value = ''
  try {
    await api.deletePetition(petition.value.id)
    router.push({ name: 'profile' })
  } catch (err) {
    actionError.value = err.message
  } finally {
    pending.value = false
  }
}

watch(() => [route.params.id, session.user?.id], load, { immediate: true })
</script>

<template>
  <div class="container py-5">
    <RouterLink to="/" class="back-link">← До всіх петицій</RouterLink>
    <div v-if="loading" class="state-panel mt-4" role="status">Завантажуємо петицію…</div>
    <div v-else-if="error" class="state-panel error-panel mt-4" role="alert"><p>{{ error }}</p><button class="btn btn-outline-primary" type="button" @click="load">Повторити</button></div>
    <article v-else-if="petition" class="detail-card mt-4">
      <div class="d-flex flex-wrap gap-2 mb-4">
        <span class="category-pill">{{ petition.category_name }}</span>
        <span class="status-pill" :class="'status-' + petition.status">{{ statusLabel(petition.status) }}</span>
      </div>
      <h1>{{ petition.title }}</h1>
      <div class="detail-meta d-flex flex-wrap gap-3 mt-3 mb-4 text-secondary">
        <span>Автор: <strong>{{ petition.author }}</strong></span>
        <span>Створено: {{ dateLabel(petition.created_at) }}</span>
        <span>Завершення: {{ dateLabel(petition.deadline) }}</span>
      </div>
      <p class="petition-text">{{ petition.text }}</p>
      <div v-if="petition.moderation_reason" class="alert alert-warning mt-4" role="note">
        <strong>Причина:</strong> {{ petition.moderation_reason }}
      </div>
      <section v-if="petition.official_response" class="official-response mt-5" aria-labelledby="response-title">
        <p class="eyebrow">Офіційна відповідь</p>
        <h2 id="response-title" class="h4">Рішення за петицією</h2>
        <p class="petition-text mb-3">{{ petition.official_response.text }}</p>
        <small class="text-secondary">{{ petition.official_response.author || 'Адміністратор' }} · {{ dateLabel(petition.official_response.published_at) }}</small>
      </section>
      <div class="detail-actions mt-5 pt-4">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <div class="vote-tally"><strong>{{ petition.vote_count }}</strong><span>голосів підтримки<span v-if="petition.vote_threshold"> із {{ petition.vote_threshold }} потрібних</span></span></div>
          <button v-if="petition.is_active && session.user" class="btn btn-primary" type="button"
            :disabled="confirmedVote || pending" @click="vote">
            {{ confirmedVote ? 'Голос зараховано' : pending ? 'Надсилаємо…' : 'Підтримати петицію' }}
          </button>
          <RouterLink v-else-if="petition.is_active && !session.user" class="btn btn-primary"
            :to="{ name: 'login', query: { next: route.fullPath } }">Увійти, щоб підтримати</RouterLink>
          <span v-else class="text-secondary">{{ voteUnavailableMessage }}</span>
          <button class="btn btn-outline-secondary" type="button" @click="copyLink">{{ copied ? 'Скопійовано' : 'Копіювати посилання' }}</button>
          <button v-if="canDelete" class="btn btn-outline-danger ms-auto" type="button" :disabled="pending" @click="remove">Видалити власну петицію</button>
        </div>
        <p v-if="actionMessage" class="text-success mt-3 mb-0" role="status">{{ actionMessage }}</p>
        <div v-if="actionError" class="alert alert-danger mt-3 mb-0" role="alert">{{ actionError }} <button class="link-button" type="button" @click="load">Оновити</button></div>
      </div>
    </article>
  </div>
</template>

