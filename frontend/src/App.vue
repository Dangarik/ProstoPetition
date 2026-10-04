<script setup>
import { ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ensureSession, session, signOut } from './session.js'

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const signingOut = ref(false)
const signOutError = ref('')
const checkingSession = ref(false)

watch(() => route.fullPath, () => { menuOpen.value = false })

async function retrySession() {
  checkingSession.value = true
  try { await ensureSession(true) }
  finally { checkingSession.value = false }
}

async function logout() {
  if (signingOut.value) return
  signingOut.value = true
  signOutError.value = ''
  try {
    await signOut()
    router.push({ name: 'home' })
  } catch (error) {
    signOutError.value = error.message
  } finally {
    signingOut.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <nav class="navbar navbar-expand-lg container py-3" aria-label="Головна навігація">
        <RouterLink class="navbar-brand d-flex align-items-center gap-2" to="/">
          <img src="/logo.svg" alt="" width="42" height="42" />
          <span>Prosto<span class="brand-accent">Petition</span></span>
        </RouterLink>
        <button class="navbar-toggler" type="button" aria-controls="site-nav" :aria-expanded="menuOpen"
          aria-label="Відкрити меню" @click="menuOpen = !menuOpen">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div id="site-nav" class="collapse navbar-collapse" :class="{ show: menuOpen }">
          <div class="navbar-nav ms-auto align-items-lg-center gap-lg-2">
            <RouterLink class="nav-link" to="/">Петиції</RouterLink>
            <RouterLink v-if="session.user" class="nav-link" to="/petitions/new">Створити</RouterLink>
            <RouterLink v-if="session.user?.is_staff" class="nav-link" to="/admin">Модерація</RouterLink>
            <RouterLink v-if="session.user" class="nav-link" to="/profile">Кабінет</RouterLink>
            <template v-if="!session.user">
              <RouterLink class="nav-link" to="/login">Увійти</RouterLink>
              <RouterLink class="btn btn-primary btn-sm px-3 ms-lg-2" to="/register">Реєстрація</RouterLink>
            </template>
            <button v-else class="btn btn-outline-secondary btn-sm px-3 ms-lg-2" type="button"
              :disabled="signingOut" @click="logout">Вийти</button>
          </div>
        </div>
      </nav>
    </header>
    <main id="main-content" class="flex-grow-1">
      <div v-if="session.error" class="container pt-3" role="alert">
        <div class="alert alert-warning d-flex justify-content-between align-items-center">
          <span>{{ session.error }}</span>
          <button class="btn btn-sm btn-outline-dark" type="button" :disabled="checkingSession" @click="retrySession">Повторити</button>
        </div>
      </div>
      <div v-if="signOutError" class="container pt-3" role="alert"><div class="alert alert-danger">{{ signOutError }}</div></div>
      <RouterView />
    </main>
    <footer class="site-footer py-4 mt-5">
      <div class="container d-flex flex-wrap justify-content-between gap-2">
        <span>© ProstoPetition</span>
        <span>Платформа громадських ініціатив</span>
      </div>
    </footer>
  </div>
</template>

