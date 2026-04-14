import {
  addRuntimeMessageListener,
  addTabsRemovedListener,
  addTabsUpdatedListener,
  cookiesGet,
  cookiesRemove,
  storageGet,
  storageRemove,
  storageSet,
  tabsCreate,
  tabsRemove,
  removeTabsRemovedListener,
  removeTabsUpdatedListener,
} from '@/lib/extensionApi'
import { runtimeConfig } from '@/lib/runtimeConfig'

const LOCAL_AUTH_KEY = 'uah.extension.auth'
const SESSION_CACHE_PREFIX = 'uah.extension.cache.'

// Persist only the extension's auth token and its expiry across browser restarts.
// Everything else is cached in chrome.storage.session because it is non-sensitive
// display data that does not need long-term persistence.
const SESSION_CACHE_KEYS = {
  currentUser: `${SESSION_CACHE_PREFIX}current-user`,
  connectedAccounts: `${SESSION_CACHE_PREFIX}connected-accounts`,
  profiles: `${SESSION_CACHE_PREFIX}profiles`,
  resumes: `${SESSION_CACHE_PREFIX}resumes`,
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function decodeJwtClaims(token) {
  try {
    const payload = token.split('.')[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4 || 4)) % 4), '=')
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

function parseErrorMessage(payload, status) {
  if (typeof payload === 'string' && payload.trim()) {
    return payload.trim()
  }
  if (isObject(payload)) {
    if (typeof payload.detail === 'string' && payload.detail.trim()) return payload.detail.trim()
    if (isObject(payload.detail) && typeof payload.detail.message === 'string' && payload.detail.message.trim()) {
      return payload.detail.message.trim()
    }
    if (typeof payload.message === 'string' && payload.message.trim()) return payload.message.trim()
  }
  return `HTTP ${status}`
}

function buildError(message, code, status = 500) {
  const error = new Error(message)
  error.code = code
  error.status = status
  return error
}

async function readLocalAuthState() {
  const result = await storageGet('local', LOCAL_AUTH_KEY)
  return result?.[LOCAL_AUTH_KEY] || null
}

async function writeLocalAuthState(value) {
  await storageSet('local', { [LOCAL_AUTH_KEY]: value })
}

async function readSessionCache(key) {
  const result = await storageGet('session', key)
  return result?.[key]
}

async function writeSessionCache(key, value) {
  await storageSet('session', { [key]: value })
}

async function removeSessionCache(keys = Object.values(SESSION_CACHE_KEYS)) {
  const removals = new Set(Array.isArray(keys) ? keys : [keys])
  const sessionSnapshot = await storageGet('session', null)

  for (const cacheKey of Object.keys(sessionSnapshot || {})) {
    if (cacheKey.startsWith(SESSION_CACHE_PREFIX)) {
      removals.add(cacheKey)
    }
  }

  await storageRemove('session', [...removals])
}

async function clearAuthState() {
  await storageRemove('local', LOCAL_AUTH_KEY)
  await removeSessionCache()
}

async function persistToken(token) {
  const claims = decodeJwtClaims(token)
  if (!claims?.exp) {
    throw buildError('Received an invalid auth token from the backend.', 'INVALID_TOKEN', 401)
  }

  const authState = {
    accessToken: token,
    expiresAt: Number(claims.exp) * 1000,
    issuedAt: claims.iat ? Number(claims.iat) * 1000 : Date.now(),
    client: 'extension',
  }

  await writeLocalAuthState(authState)
  return authState
}

function isExpired(authState) {
  return !authState?.expiresAt || Date.now() >= Number(authState.expiresAt)
}

function buildApiUrl(pathname) {
  return new URL(pathname, runtimeConfig.apiOrigin).toString()
}

async function fetchJson(pathname, options = {}) {
  const {
    method = 'GET',
    body,
    requireAuth = true,
  } = options

  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  headers.set('X-UAH-Client', 'extension')

  if (body !== undefined && !(body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (requireAuth) {
    const authState = await readLocalAuthState()
    if (!authState?.accessToken || isExpired(authState)) {
      await clearAuthState()
      throw buildError('Your UAH session has expired. Please sign in again.', 'AUTH_REQUIRED', 401)
    }
    headers.set('Authorization', `Bearer ${authState.accessToken}`)
  }

  const response = await fetch(buildApiUrl(pathname), {
    method,
    headers,
    credentials: 'include',
    body: body === undefined ? undefined : (body instanceof FormData ? body : JSON.stringify(body)),
  })

  const responseText = await response.text()
  let payload = null

  if (responseText) {
    try {
      payload = JSON.parse(responseText)
    } catch {
      payload = responseText
    }
  }

  if (response.status === 401) {
    await clearAuthState()
    throw buildError('Your UAH session has expired. Please sign in again.', 'AUTH_REQUIRED', 401)
  }

  if (!response.ok) {
    throw buildError(parseErrorMessage(payload, response.status), 'API_ERROR', response.status)
  }

  return payload
}

async function bootstrapSession() {
  const authState = await readLocalAuthState()
  if (!authState?.accessToken) {
    return { authenticated: false, user: null, expiresAt: null }
  }

  if (isExpired(authState)) {
    await clearAuthState()
    return { authenticated: false, user: null, expiresAt: null, reason: 'expired' }
  }

  const user = await fetchJson('/api/auth/me')
  await writeSessionCache(SESSION_CACHE_KEYS.currentUser, user)

  return {
    authenticated: true,
    user,
    expiresAt: authState.expiresAt,
  }
}

async function loadCachedOrFetch(cacheKey, pathname, options = {}) {
  if (!options.force) {
    const cached = await readSessionCache(cacheKey)
    if (cached) return cached
  }

  const payload = await fetchJson(pathname, options)
  await writeSessionCache(cacheKey, payload)
  return payload
}

async function loginWithPassword(payload) {
  const data = await fetchJson('/api/auth/login', {
    method: 'POST',
    requireAuth: false,
    body: {
      email: payload.email,
      password: payload.password,
    },
  })

  const authState = await persistToken(data.access_token)
  await removeSessionCache()
  await writeSessionCache(SESSION_CACHE_KEYS.currentUser, data.user)

  return {
    user: data.user,
    expiresAt: authState.expiresAt,
  }
}

async function readAuthCookieToken() {
  const cookie = await cookiesGet({
    url: runtimeConfig.apiOrigin,
    name: runtimeConfig.authCookieName,
  }).catch(() => null)
  if (cookie?.value) {
    return cookie.value
  }

  return ''
}

async function removeAuthCookie() {
  await cookiesRemove({
    url: runtimeConfig.apiOrigin,
    name: runtimeConfig.authCookieName,
  }).catch(() => null)
}

async function finishGoogleLogin() {
  const token = await readAuthCookieToken()
  if (!token) {
    throw buildError(
      'Google sign-in completed, but the extension could not read the UAH auth cookie.',
      'COOKIE_NOT_FOUND',
      401,
    )
  }

  const authState = await persistToken(token)
  const user = await fetchJson('/api/auth/me')
  await writeSessionCache(SESSION_CACHE_KEYS.currentUser, user)

  return {
    user,
    expiresAt: authState.expiresAt,
  }
}

async function loginWithGoogle() {
  if (runtimeConfig.isLocalHarness) {
    throw buildError(
      'Google sign-in is disabled for the local extension harness. Use email and password against your local backend instead.',
      'GOOGLE_AUTH_UNAVAILABLE',
      400,
    )
  }

  const authUrl = new URL('/api/auth/google', runtimeConfig.apiOrigin)
  authUrl.searchParams.set('intent', 'login')
  authUrl.searchParams.set('client', 'extension')

  const authTab = await tabsCreate({ url: authUrl.toString(), active: true })
  const tabId = authTab?.id

  if (typeof tabId !== 'number') {
    throw buildError('Could not open a Google sign-in tab.', 'TAB_CREATE_FAILED')
  }

  return new Promise((resolve, reject) => {
    let settled = false

    const cleanup = () => {
      clearTimeout(timeoutId)
      removeTabsUpdatedListener(onUpdated)
      removeTabsRemovedListener(onRemoved)
    }

    const finish = async (callback) => {
      if (settled) return
      settled = true
      cleanup()
      try {
        await callback()
      } catch (error) {
        reject(error)
      }
    }

    const timeoutId = setTimeout(() => {
      finish(async () => {
        throw buildError('Google sign-in timed out. Please try again.', 'GOOGLE_AUTH_TIMEOUT')
      })
    }, 180000)

    const onRemoved = (removedTabId) => {
      if (removedTabId !== tabId) return
      finish(async () => {
        throw buildError('Google sign-in was cancelled before UAH completed the login flow.', 'GOOGLE_AUTH_CANCELLED')
      })
    }

    const onUpdated = (updatedTabId, changeInfo, tab) => {
      if (updatedTabId !== tabId) return
      const currentUrl = changeInfo.url || tab?.url || ''
      if (!currentUrl.startsWith(runtimeConfig.appOrigin)) return

      finish(async () => {
        const parsedUrl = new URL(currentUrl)
        if (parsedUrl.searchParams.get('oauth') === 'error') {
          const reason = parsedUrl.searchParams.get('reason')
          throw buildError(
            `Google sign-in failed${reason ? ` (${reason.replaceAll('_', ' ')})` : ''}.`,
            'GOOGLE_AUTH_FAILED',
          )
        }

        const result = await finishGoogleLogin()
        await tabsRemove(tabId).catch(() => null)
        resolve(result)
      })
    }

    addTabsUpdatedListener(onUpdated)
    addTabsRemovedListener(onRemoved)
  })
}

async function logout() {
  await fetchJson('/api/auth/logout', {
    method: 'POST',
    requireAuth: false,
  }).catch(() => null)

  await removeAuthCookie()
  await clearAuthState()
  return { authenticated: false }
}

async function openFullApp(pathname) {
  const destination = new URL(pathname.startsWith('/') ? pathname : `/${pathname}`, runtimeConfig.appOrigin).toString()
  await tabsCreate({ url: destination, active: true })
  return { opened: true }
}

function serializeError(error) {
  return {
    ok: false,
    code: error?.code || 'UNEXPECTED_ERROR',
    status: error?.status || 500,
    message: String(error?.message || error || 'Unexpected extension error.'),
  }
}

addRuntimeMessageListener(async (message) => {
  try {
    switch (message?.type) {
      case 'bootstrap':
        return { ok: true, data: await bootstrapSession() }
      case 'login':
        return { ok: true, data: await loginWithPassword(message.payload || {}) }
      case 'loginWithGoogle':
        return { ok: true, data: await loginWithGoogle() }
      case 'logout':
        return { ok: true, data: await logout() }
      case 'getConnectedAccounts':
        return {
          ok: true,
          data: await loadCachedOrFetch(SESSION_CACHE_KEYS.connectedAccounts, '/api/auth/connected-accounts', {
            force: Boolean(message?.payload?.force),
          }),
        }
      case 'getProfiles':
        return {
          ok: true,
          data: await loadCachedOrFetch(SESSION_CACHE_KEYS.profiles, '/api/applicant-profile/', {
            force: Boolean(message?.payload?.force),
          }),
        }
      case 'getProfile':
        return {
          ok: true,
          data: await loadCachedOrFetch(
            `${SESSION_CACHE_KEYS.profiles}:detail:${message?.payload?.profileId}`,
            `/api/applicant-profile/${message?.payload?.profileId}`,
            { force: Boolean(message?.payload?.force) },
          ),
        }
      case 'getResumes':
        return {
          ok: true,
          data: await loadCachedOrFetch(SESSION_CACHE_KEYS.resumes, '/api/resume/', {
            force: Boolean(message?.payload?.force),
          }),
        }
      case 'getResume':
        return {
          ok: true,
          data: await loadCachedOrFetch(
            `${SESSION_CACHE_KEYS.resumes}:detail:${message?.payload?.resumeId}`,
            `/api/resume/${message?.payload?.resumeId}`,
            { force: Boolean(message?.payload?.force) },
          ),
        }
      case 'openFullApp':
        return { ok: true, data: await openFullApp(message?.payload?.pathname || '/home') }
      default:
        return serializeError(buildError('Unknown extension message.', 'UNKNOWN_MESSAGE', 400))
    }
  } catch (error) {
    return serializeError(error)
  }
})
