import { createRouter, createWebHistory } from 'vue-router'
import { getCurrentUser, syncCurrentUser } from '@/lib/auth'
import { shouldShowDebugTools } from '@/lib/debugTools'

const modules = import.meta.glob('../views/*.vue')

function isAuthenticated() {
  return Boolean(getCurrentUser())
}

async function resolveAuthenticatedUser(force = false) {
  try {
    return await syncCurrentUser({ force })
  } catch {
    return getCurrentUser()
  }
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
  // Returns scroll bar to top when switching pages (except if you are using back/forward).
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition  // If you have a saved pos. from using back/forward on browser, keep it.
    else return { top: 0 }  // Else return to top.
  }
})

router.beforeEach(async (to) => {
  const publicPaths = new Set([
    '/login',
    '/register',
    '/status',
    '/forgot-password',
    '/reset-password',
    '/oauth-callback',
    '/our-commitment'
  ])
  const isOAuthCallback = to.path === '/oauth-callback'

  if (isOAuthCallback) {
    return true
  }

  if (publicPaths.has(to.path)) {
    const authedUser = await resolveAuthenticatedUser(to.path === '/login' || to.path === '/register')
    if (authedUser && (to.path === '/login' || to.path === '/register')) {
      return '/home'
    }
    return true
  }

  const authedUser = await resolveAuthenticatedUser(true)
  if (!authedUser) {
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
