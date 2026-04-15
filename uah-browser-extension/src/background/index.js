import {
  addRuntimeMessageListener,
  addTabsActivatedListener,
  addTabsRemovedListener,
  addTabsUpdatedListener,
  cookiesGet,
  cookiesRemove,
  tabsGet,
  storageGet,
  storageRemove,
  storageSet,
  scriptingExecuteScript,
  tabsCreate,
  tabsQuery,
  tabsRemove,
  removeTabsRemovedListener,
  removeTabsUpdatedListener,
} from '@/lib/extensionApi'
import { sanitizeTokenMap } from '@/autofill/source'
import { DEFAULT_PINNED_UI_STATE, mergePinnedUiState, PINNED_UI_STATE_KEY } from '@/lib/pinnedUiState'
import { runtimeConfig } from '@/lib/runtimeConfig'

const LOCAL_AUTH_KEY = 'uah.extension.auth'
const SESSION_CACHE_PREFIX = 'uah.extension.cache.'
const dismissedPinnedTabs = new Set()

// Persist only the extension's auth token and its expiry across browser restarts.
// Everything else is cached in chrome.storage.session because it is non-sensitive
// display data that does not need long-term persistence.
const SESSION_CACHE_KEYS = {
  currentUser: `${SESSION_CACHE_PREFIX}current-user`,
  connectedAccounts: `${SESSION_CACHE_PREFIX}connected-accounts`,
  profiles: `${SESSION_CACHE_PREFIX}profiles`,
  resumes: `${SESSION_CACHE_PREFIX}resumes`,
}
const AUTOFILL_RESTRICTED_PREFIXES = ['chrome://', 'chrome-extension://', 'edge://', 'about:', 'moz-extension://']

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

async function readPinnedUiState() {
  const result = await storageGet('local', PINNED_UI_STATE_KEY)
  return {
    ...mergePinnedUiState(DEFAULT_PINNED_UI_STATE, result?.[PINNED_UI_STATE_KEY] || {}),
    // Resize unlock is a temporary convenience, not a sticky default.
    panelResizeUnlocked: false,
  }
}

async function writePinnedUiState(patch = {}) {
  const nextState = mergePinnedUiState(await readPinnedUiState(), patch)
  await storageSet('local', { [PINNED_UI_STATE_KEY]: nextState })
  return nextState
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

function normalizeAutofillExecutionError(error) {
  const message = String(error?.message || error || 'Autofill could not run on the active tab.')
  const normalizedMessage = message.toLowerCase()

  if (normalizedMessage.includes('cannot access') || normalizedMessage.includes('cannot be scripted')) {
    return buildError(
      'UAH autofill only runs on normal web pages. Open a job application tab and try again.',
      'AUTOFILL_TAB_UNSUPPORTED',
      400,
    )
  }

  return buildError(message, 'AUTOFILL_EXECUTION_FAILED', 500)
}

function normalizePinnedPanelExecutionError(error) {
  const message = String(error?.message || error || 'UAH panel could not run on the active tab.')
  const normalizedMessage = message.toLowerCase()

  if (normalizedMessage.includes('cannot access') || normalizedMessage.includes('cannot be scripted')) {
    return buildError(
      'The pinned UAH panel only runs on normal web pages. Your pin preference was saved and it will appear on supported tabs.',
      'PINNED_PANEL_TAB_UNSUPPORTED',
      400,
    )
  }

  return buildError(message, 'PINNED_PANEL_EXECUTION_FAILED', 500)
}

function assertInjectableTab(tab) {
  if (typeof tab?.id !== 'number') {
    throw buildError('Open a job application tab before running UAH autofill.', 'AUTOFILL_TAB_NOT_FOUND', 400)
  }

  const url = String(tab.url || '')
  if (!url || AUTOFILL_RESTRICTED_PREFIXES.some((prefix) => url.startsWith(prefix))) {
    throw buildError(
      'UAH autofill only runs on normal web pages. Open a job application tab and try again.',
      'AUTOFILL_TAB_UNSUPPORTED',
      400,
    )
  }
}

function isInjectableTab(tab) {
  if (typeof tab?.id !== 'number') return false
  const url = String(tab.url || '')
  return Boolean(url) && !AUTOFILL_RESTRICTED_PREFIXES.some((prefix) => url.startsWith(prefix))
}

async function getCurrentActiveTab() {
  const tabs = await tabsQuery({ active: true, currentWindow: true })
  return Array.isArray(tabs) ? tabs[0] || null : null
}

async function getActiveTab() {
  const tab = await getCurrentActiveTab()
  assertInjectableTab(tab)
  return tab
}

async function ensureAutofillRuntime(tabId) {
  try {
    await scriptingExecuteScript({
      target: { tabId },
      files: ['autofill-content.js'],
    })
  } catch (error) {
    throw normalizeAutofillExecutionError(error)
  }
}

async function ensurePinnedPanelRuntime(tabId) {
  try {
    await scriptingExecuteScript({
      target: { tabId },
      files: ['pinned-panel.js'],
    })
  } catch (error) {
    throw normalizePinnedPanelExecutionError(error)
  }
}

async function invokePinnedPanelRuntime(tabId, action, payload = undefined) {
  try {
    const results = await scriptingExecuteScript({
      target: { tabId },
      func: (nextAction, nextPayload) => {
        const api = globalThis.window?.__UAH_PINNED_PANEL__
        if (!api || typeof api[nextAction] !== 'function') {
          return { error: 'UAH pinned panel runtime is unavailable on this page.' }
        }
        return api[nextAction](nextPayload)
      },
      args: [action, payload],
    })
    const result = Array.isArray(results) ? results[0]?.result : null
    if (result?.error) {
      throw buildError(result.error, 'PINNED_PANEL_RUNTIME_UNAVAILABLE', 500)
    }
    return result ?? null
  } catch (error) {
    if (error?.code) throw error
    throw normalizePinnedPanelExecutionError(error)
  }
}

async function invokeAutofillRuntime(tabId, action, payload, uiState = {}) {
  try {
    const results = await scriptingExecuteScript({
      target: { tabId },
      func: (nextAction, nextPayload, nextUiState) => {
        const api = globalThis.window?.__UAH_RESUME_TESTER__
        if (!api || typeof api[nextAction] !== 'function') {
          return { error: 'UAH autofill runtime is unavailable on this page.' }
        }
        if (typeof api.configure === 'function') {
          api.configure(nextUiState)
        }
        return api[nextAction](nextPayload)
      },
      args: [action, payload, uiState],
    })
    const result = Array.isArray(results) ? results[0]?.result : null
    if (result?.error) {
      throw buildError(result.error, 'AUTOFILL_RUNTIME_UNAVAILABLE', 500)
    }
    return result ?? null
  } catch (error) {
    if (error?.code) throw error
    throw normalizeAutofillExecutionError(error)
  }
}

async function hidePinnedPanelOnTab(tabId) {
  if (typeof tabId !== 'number') return null

  try {
    const results = await scriptingExecuteScript({
      target: { tabId },
      func: () => {
        const api = globalThis.window?.__UAH_PINNED_PANEL__
        if (api && typeof api.hide === 'function') {
          return api.hide()
        }
        return { ok: true }
      },
    })
    return Array.isArray(results) ? results[0]?.result ?? null : null
  } catch {
    return null
  }
}

async function hidePinnedPanelEverywhere() {
  const tabs = await tabsQuery({})
  const candidates = Array.isArray(tabs) ? tabs.filter(isInjectableTab) : []
  await Promise.all(candidates.map((tab) => hidePinnedPanelOnTab(tab.id)))
}

async function showPinnedPanelOnTab(tab, options = {}) {
  const { quietUnsupported = false } = options

  if (!isInjectableTab(tab)) {
    if (quietUnsupported) return { shown: false, reason: 'unsupported' }
    assertInjectableTab(tab)
  }

  const uiState = await readPinnedUiState()

  try {
    await ensurePinnedPanelRuntime(tab.id)
    await invokePinnedPanelRuntime(tab.id, 'show', {
      pinEnabled: uiState.pinEnabled,
      panelPosition: uiState.panelPosition,
      panelSize: uiState.panelSize,
      panelResizeUnlocked: uiState.panelResizeUnlocked,
    })
    return { shown: true, tabId: tab.id }
  } catch (error) {
    if (quietUnsupported && error?.code === 'PINNED_PANEL_TAB_UNSUPPORTED') {
      return { shown: false, reason: 'unsupported' }
    }
    throw error
  }
}

async function maybeShowPinnedPanelForTab(tabId) {
  if (dismissedPinnedTabs.has(tabId)) return null

  const uiState = await readPinnedUiState()
  if (!uiState.pinEnabled) return null

  const tab = await tabsGet(tabId).catch(() => null)
  if (!tab || !isInjectableTab(tab)) return null
  return showPinnedPanelOnTab(tab, { quietUnsupported: true })
}

async function setPinnedUiState(patch = {}) {
  const previousState = await readPinnedUiState()
  const nextState = await writePinnedUiState(patch)

  if (typeof patch?.pinEnabled === 'boolean' && patch.pinEnabled !== previousState.pinEnabled) {
    dismissedPinnedTabs.clear()

    if (nextState.pinEnabled) {
      const currentTab = await getCurrentActiveTab()
      if (currentTab) {
        await showPinnedPanelOnTab(currentTab, { quietUnsupported: true })
      }
    } else {
      await hidePinnedPanelEverywhere()
    }
  }

  return nextState
}

async function dismissPinnedPanel(sender) {
  const tabId = sender?.tab?.id
  if (typeof tabId === 'number') {
    dismissedPinnedTabs.add(tabId)
  }
  return { dismissed: typeof tabId === 'number', tabId: tabId ?? null }
}

async function runAutofillAction(action, payload = {}) {
  const tab = await getActiveTab()
  await ensureAutofillRuntime(tab.id)

  let argument = undefined
  if (action === 'scan' || action === 'fill') {
    const tokenMap = sanitizeTokenMap(payload.tokenMap)
    if (!Object.keys(tokenMap).length) {
      throw buildError('A prepared autofill token map is required.', 'AUTOFILL_SOURCE_REQUIRED', 400)
    }
    argument = tokenMap
  }

  const uiState = await readPinnedUiState()
  const data = await invokeAutofillRuntime(tab.id, action, argument, {
    debugPosition: uiState.debugPosition,
  })
  return {
    ...(isObject(data) ? data : { value: data }),
    source: isObject(payload.source) ? payload.source : null,
    tabUrl: String(tab.url || ''),
  }
}

async function runPageNavigationAction(direction) {
  const tab = await getActiveTab()

  try {
    const results = await scriptingExecuteScript({
      target: { tabId: tab.id },
      func: (nextDirection) => {
        const normalize = (value) => String(value || '').trim().toLowerCase().replace(/\s+/g, ' ')
        const isVisible = (element) => {
          if (!element || element.disabled) return false
          const rect = typeof element.getBoundingClientRect === 'function'
            ? element.getBoundingClientRect()
            : { width: 0, height: 0 }
          return rect.width > 0 || rect.height > 0 || element.offsetParent !== null
        }

        const candidates = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]'))
          .filter(isVisible)

        const previousLabels = ['back', 'previous', 'prev', 'go back']
        const nextLabels = ['next', 'continue', 'review', 'submit', 'save and continue']
        const labels = nextDirection === 'previous' ? previousLabels : nextLabels

        const match = candidates.find((element) => {
          const aria = normalize(element.getAttribute?.('aria-label'))
          const title = normalize(element.getAttribute?.('title'))
          const value = normalize(element.value)
          const text = normalize(element.innerText || element.textContent)
          const haystacks = [aria, title, value, text].filter(Boolean)
          return haystacks.some((haystack) => labels.some((label) => haystack === label || haystack.startsWith(`${label} `)))
        })

        if (match) {
          match.click?.()
          return {
            clicked: true,
            method: 'dom',
            label: normalize(match.innerText || match.textContent || match.value || match.getAttribute?.('aria-label')),
            usedHistory: false,
          }
        }

        if (nextDirection === 'previous' && globalThis.history?.length > 1) {
          globalThis.history.back()
          return {
            clicked: true,
            method: 'history',
            label: 'history.back',
            usedHistory: true,
          }
        }

        return {
          clicked: false,
          method: 'none',
          usedHistory: false,
        }
      },
      args: [direction],
    })

    const result = Array.isArray(results) ? results[0]?.result : null
    if (!result?.clicked) {
      throw buildError(
        `Could not find a ${direction === 'previous' ? 'previous' : 'next'} page button on this application page.`,
        'PAGE_NAVIGATION_NOT_FOUND',
        404,
      )
    }

    return {
      direction,
      ...result,
      tabUrl: String(tab.url || ''),
    }
  } catch (error) {
    if (error?.code) throw error
    throw normalizeAutofillExecutionError(error)
  }
}

function serializeError(error) {
  return {
    ok: false,
    code: error?.code || 'UNEXPECTED_ERROR',
    status: error?.status || 500,
    message: String(error?.message || error || 'Unexpected extension error.'),
  }
}

addTabsActivatedListener(({ tabId }) => {
  maybeShowPinnedPanelForTab(tabId).catch(() => null)
})

addTabsUpdatedListener((tabId, changeInfo) => {
  if (typeof changeInfo?.url === 'string' || changeInfo?.status === 'loading') {
    dismissedPinnedTabs.delete(tabId)
  }

  if (changeInfo?.status === 'complete') {
    maybeShowPinnedPanelForTab(tabId).catch(() => null)
  }
})

addTabsRemovedListener((tabId) => {
  dismissedPinnedTabs.delete(tabId)
})

addRuntimeMessageListener(async (message, sender) => {
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
      case 'autofillScan':
        return { ok: true, data: await runAutofillAction('scan', message.payload || {}) }
      case 'autofillFill':
        return { ok: true, data: await runAutofillAction('fill', message.payload || {}) }
      case 'autofillRemove':
        return { ok: true, data: await runAutofillAction('remove', message.payload || {}) }
      case 'autofillGetStats':
        return { ok: true, data: await runAutofillAction('getStats', message.payload || {}) }
      case 'navigatePreviousPage':
        return { ok: true, data: await runPageNavigationAction('previous') }
      case 'navigateNextPage':
        return { ok: true, data: await runPageNavigationAction('next') }
      case 'getPinnedUiState':
        return { ok: true, data: await readPinnedUiState() }
      case 'setPinnedUiState':
        return { ok: true, data: await setPinnedUiState(message.payload || {}) }
      case 'showPinnedPanel': {
        const tab = await getCurrentActiveTab()
        if (typeof tab?.id === 'number') {
          dismissedPinnedTabs.delete(tab.id)
        }
        return { ok: true, data: tab ? await showPinnedPanelOnTab(tab, { quietUnsupported: true }) : { shown: false } }
      }
      case 'hidePinnedPanel': {
        const tab = await getCurrentActiveTab()
        if (typeof tab?.id === 'number') {
          dismissedPinnedTabs.add(tab.id)
          await hidePinnedPanelOnTab(tab.id)
        }
        return { ok: true, data: { hidden: true, tabId: tab?.id ?? null } }
      }
      case 'dismissPinnedPanel':
        return { ok: true, data: await dismissPinnedPanel(sender) }
      case 'openFullApp':
        return { ok: true, data: await openFullApp(message?.payload?.pathname || '/home') }
      default:
        return serializeError(buildError('Unknown extension message.', 'UNKNOWN_MESSAGE', 400))
    }
  } catch (error) {
    return serializeError(error)
  }
})
