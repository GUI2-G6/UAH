import { createRouter, createWebHistory } from 'vue-router'
import { getAccessToken } from '@/lib/auth'
import { shouldShowDebugTools } from '@/lib/debugTools'

const modules = import.meta.glob('../views/*.vue')

function isAuthenticated() {
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
    component: modules[path],
    meta: {
      debugOnly: lower === 'dev',
    },
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
  const publicPaths = new Set(['/login', '/register', '/status', '/forgot-password', '/reset-password', '/oauth-callback'])
  const authed = isAuthenticated()

  if (publicPaths.has(to.path)) {
    if (authed && to.path === '/login') {
      return '/home'
    }
    return true
  }

  if (!authed) {
    return {
      path: '/login',
      query: to.fullPath && to.fullPath !== '/' ? { next: to.fullPath } : undefined,
    }
  }

  if (to.meta?.debugOnly && !shouldShowDebugTools()) {
    return '/home'
  }

  return true
})

export default router
