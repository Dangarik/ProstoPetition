<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { signUp } from '../session.js'

const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', email: '', password: '', repeatPassword: '' })
const pending = ref(false)
const error = ref('')
const fieldErrors = ref({})

async function submit() {
  error.value = ''
  fieldErrors.value = {}
  if (!form.username.trim() || !form.email.trim() || !form.password) {
    error.value = 'Заповніть усі обов’язкові поля.'
    return
  }
  if (form.password !== form.repeatPassword) {
    fieldErrors.value = { repeatPassword: 'Паролі не збігаються.' }
    return
  }
  pending.value = true
  try {
    await signUp({ username: form.username.trim(), email: form.email.trim(), password: form.password })
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//')
      ? route.query.next : '/profile'
    router.replace(next)
  } catch (err) {
    error.value = err.message
    fieldErrors.value = err.fields || {}
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="container py-5">
    <div class="auth-card mx-auto">
      <p class="eyebrow">Приєднуйтесь до громади</p>
      <h1 class="h2 mb-2">Створити обліковий запис</h1>
      <p class="text-secondary mb-4">Подавайте петиції та підтримуйте ініціативи.</p>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="mb-3"><label class="form-label" for="username">Ім’я користувача</label><input id="username" v-model="form.username" class="form-control" autocomplete="username" maxlength="150" required /><small v-if="fieldErrors.username" class="text-danger">{{ String(fieldErrors.username) }}</small></div>
        <div class="mb-3"><label class="form-label" for="email">Електронна пошта</label><input id="email" v-model="form.email" class="form-control" type="email" autocomplete="email" required /><small v-if="fieldErrors.email" class="text-danger">{{ String(fieldErrors.email) }}</small></div>
        <div class="mb-3"><label class="form-label" for="password">Пароль</label><input id="password" v-model="form.password" class="form-control" type="password" autocomplete="new-password" minlength="8" required /><small v-if="fieldErrors.password" class="text-danger">{{ String(fieldErrors.password) }}</small></div>
        <div class="mb-4"><label class="form-label" for="repeat-password">Повторіть пароль</label><input id="repeat-password" v-model="form.repeatPassword" class="form-control" type="password" autocomplete="new-password" required /><small v-if="fieldErrors.repeatPassword" class="text-danger">{{ fieldErrors.repeatPassword }}</small></div>
        <button class="btn btn-primary w-100" type="submit" :disabled="pending">{{ pending ? 'Реєструємо…' : 'Зареєструватися' }}</button>
      </form>
      <p class="text-center text-secondary mt-4 mb-0">Вже маєте обліковий запис? <RouterLink :to="{ name: 'login', query: route.query.next ? { next: route.query.next } : {} }">Увійти</RouterLink></p>
    </div>
  </div>
</template>

