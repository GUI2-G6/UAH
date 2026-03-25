import { createRouter, createWebHistory } from 'vue-router'
import { getAccessToken } from '@/lib/auth'

const modules = import.meta.glob('../views/*.vue')

function isLocalDev() {
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1'
}

function isAuthenticated() {
  if (isLocalDev()) return true
  return Boolean(getAccessToken())
}

/* This grabs everything from and generates routes for everything in the views folder */
const viewRoutes = Object.keys(modules).map((path) => {
  const name = path
    .split('/')
    .pop()
    .replace('.vue', '')

  const lower = name.toLowerCase()

  let routePath
  if (lower === 'home') routePath = '/home'
  else if (lower === 'login') routePath = '/login'
  else if (lower === 'register') routePath = '/register'
  else routePath = `/${lower}`

  return {
    path: routePath,
    name: lower,
    component: modules[path]
  }
})

const routes = [
  {
    path: '/',
    redirect: () => (isAuthenticated() ? '/home' : '/login')
  },
  ...viewRoutes,
]


const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (isLocalDev()) return true

  const publicPaths = new Set(['/login', '/register', '/status', '/forgot-password', '/reset-password'])
  const authed = isAuthenticated()

  if (publicPaths.has(to.path)) {
    if (authed && to.path === '/login') {
      return '/home'
    }
    return true
  }

  if (authed) return true

  return {
    path: '/login',
    query: to.fullPath && to.fullPath !== '/' ? { next: to.fullPath } : undefined,
  }
})

export default router
