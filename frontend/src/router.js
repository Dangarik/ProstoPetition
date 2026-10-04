import { createRouter, createWebHistory } from 'vue-router'
import { ensureSession, session } from './session.js'

const routes = [
  { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
  { path: '/petitions/new', name: 'create', component: () => import('./views/CreatePetitionView.vue'), meta: { auth: true } },
  { path: '/petitions/:id', name: 'petition', component: () => import('./views/PetitionView.vue') },
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue') },
  { path: '/register', name: 'register', component: () => import('./views/RegisterView.vue') },
  { path: '/profile', name: 'profile', component: () => import('./views/ProfileView.vue'), meta: { auth: true } },
  { path: '/admin', name: 'admin', component: () => import('./views/AdminView.vue'), meta: { auth: true, staff: true } },
  { path: '/forbidden', name: 'forbidden', component: () => import('./views/ForbiddenView.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('./views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (!to.meta.auth) return true
  await ensureSession(true)
  if (session.error) return true
  if (!session.user) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.staff && !session.user.is_staff) return { name: 'forbidden' }
  return true
})

export default router

