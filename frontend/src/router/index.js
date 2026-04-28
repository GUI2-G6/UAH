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

// File-based route generation keeps the view directory honest: if a routed page
// exists in `views/`, it is mounted here unless we explicitly special-case it.
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

const landingRoute = viewRoutes.find((route) => route.path === '/landing')

const routes = [
  {
    path: '/',
    name: 'public-home',
    component: landingRoute?.component || modules['../views/Landing.vue'],
  },
  ...viewRoutes.filter((route) => route.path !== '/landing'),
  {
    path: '/landing',
    redirect: '/',
  },
  {
    path: '/our-commitment',
    redirect: '/privacy-policy',
  },
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
  // These routes stay reachable without an existing session, but they may still
  // redirect signed-in users away from auth pages once identity is resolved.
  const publicPaths = new Set([
    '/landing',
    '/login',
    '/register',
    '/signup',
    '/status',
    '/forgot-password',
    '/reset-password',
    '/oauth-callback',
    '/verify-email',
    '/privacy-policy',
    '/our-commitment',
    '/contributors',
  ])
  const isOAuthCallback = to.path === '/oauth-callback'

  if (isOAuthCallback) {
    return true
  }

  if (publicPaths.has(to.path)) {
    const authedUser = await resolveAuthenticatedUser(to.path === '/login' || to.path === '/register' || to.path === '/signup')
    if (authedUser && (to.path === '/login' || to.path === '/register' || to.path === '/signup')) {
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

  // Keep the dev surface routed for contributors without making it a public UI
  // entrypoint in normal browser sessions.
  if (to.meta?.debugOnly && !shouldShowDebugTools()) {
    return '/home'
  }

  return true
})

export default router
