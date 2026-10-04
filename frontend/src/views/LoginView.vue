<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { signIn } from '../session.js'

const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const pending = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = 'Введіть ім’я користувача та пароль.'
    return
  }
  pending.value = true
  try {
    await signIn({ username: form.username.trim(), password: form.password })
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//')
      ? route.query.next : '/profile'
    router.replace(next)
  } catch (err) {
    error.value = err.message
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="container py-5">
    <div class="auth-card mx-auto">
      <p class="eyebrow">Раді вас бачити</p>
      <h1 class="h2 mb-2">Увійти до ProstoPetition</h1>
      <p class="text-secondary mb-4">Ваші петиції та голоси починаються тут.</p>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="mb-3"><label class="form-label" for="username">Ім’я користувача</label><input id="username" v-model="form.username" class="form-control" autocomplete="username" required /></div>
        <div class="mb-4"><label class="form-label" for="password">Пароль</label><input id="password" v-model="form.password" class="form-control" type="password" autocomplete="current-password" required /></div>
        <button class="btn btn-primary w-100" type="submit" :disabled="pending">{{ pending ? 'Входимо…' : 'Увійти' }}</button>
      </form>
      <p class="text-center text-secondary mt-4 mb-0">Немає облікового запису? <RouterLink :to="{ name: 'register', query: route.query.next ? { next: route.query.next } : {} }">Зареєструватися</RouterLink></p>
    </div>
  </div>
</template>

