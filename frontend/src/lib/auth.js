function normalizeNamespace(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_.-]/g, '_')
}

function isLoopbackHost(value) {
    const host = String(value || '').trim().toLowerCase()
    return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]'
}

function inferDefaultNamespace() {
    const host = String(window?.location?.hostname || '').trim().toLowerCase()

    if (isLoopbackHost(host)) {
        return 'dev'
    }
    if (host.startsWith('beta.')) return 'beta'
    if (host.startsWith('dev.')) return 'dev'

    return 'dev'
}

function resolveFrontendAuthMode() {
    const mode = String(import.meta?.env?.MODE || '')
        .trim()
        .toLowerCase()
    if (mode === 'backend' || mode === 'mock') return mode

    const explicit = String(import.meta?.env?.VITE_LOCAL_MODE || '')
        .trim()
        .toLowerCase()
    if (explicit === 'backend' || explicit === 'mock') return explicit

    const host = String(window?.location?.hostname || '').trim().toLowerCase()
    if (isLoopbackHost(host)) return 'mock'

    return 'backend'
}

const DEFAULT_NAMESPACE = inferDefaultNamespace()
const AUTH_NAMESPACE = normalizeNamespace(import.meta?.env?.VITE_AUTH_NAMESPACE) || DEFAULT_NAMESPACE
const FRONTEND_AUTH_MODE = resolveFrontendAuthMode()
// In backend mode the browser should trust the backend's HttpOnly cookie flow.
// Only mock mode keeps an access token in local storage for isolated UI work.
const SHOULD_PERSIST_ACCESS_TOKEN = FRONTEND_AUTH_MODE === 'mock'

const LEGACY_ACCESS_TOKEN_KEY = 'uah_access_token'
const LEGACY_CURRENT_USER_KEY = 'uah_current_user'
const ACCESS_TOKEN_KEY = `uah_access_token:${AUTH_NAMESPACE}`
const CURRENT_USER_KEY = `uah_current_user:${AUTH_NAMESPACE}`
// Limit legacy-key migration to loopback development so deployed environments
// do not unexpectedly inherit stale local-storage auth from older builds.
const SHOULD_MIGRATE_LEGACY_KEYS = isLoopbackHost(window?.location?.hostname)
const USER_SYNC_TTL_MS = 15_000

let currentUserSyncPromise = null
let lastCurrentUserSyncAt = 0

function parseTokenPayload(token) {
    try {
        return JSON.parse(atob(token.split('.')[1]))
    } catch { return null }
}

export function isTokenExpired(token) {
    if (!token) return true
    const payload = parseTokenPayload(token)
    if (!payload?.exp) return true
    return Date.now() / 1000 >= payload.exp
}

export function getAccessToken() {
    if (!SHOULD_PERSIST_ACCESS_TOKEN) {
        localStorage.removeItem(ACCESS_TOKEN_KEY)
        localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY)
        return null
    }
    let token = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (!token && SHOULD_MIGRATE_LEGACY_KEYS) {
        const legacy = localStorage.getItem(LEGACY_ACCESS_TOKEN_KEY)
        if (legacy) {
            token = legacy
            localStorage.setItem(ACCESS_TOKEN_KEY, legacy)
            localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY)
        }
    }
    if (token && isTokenExpired(token)) {
        clearAuth()
        return null
    }
    return token
}

export function getAuthNamespace() {
    return AUTH_NAMESPACE
}

export function setAccessToken(token) {
    if (!SHOULD_PERSIST_ACCESS_TOKEN) {
        localStorage.removeItem(ACCESS_TOKEN_KEY)
        localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY)
        return
    }
    if (token) localStorage.setItem(ACCESS_TOKEN_KEY, token)
    else localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getCurrentUser() {
    try {
        let raw = localStorage.getItem(CURRENT_USER_KEY)
        if (!raw && SHOULD_MIGRATE_LEGACY_KEYS) {
            const legacy = localStorage.getItem(LEGACY_CURRENT_USER_KEY)
            if (legacy) {
                raw = legacy
                localStorage.setItem(CURRENT_USER_KEY, legacy)
                localStorage.removeItem(LEGACY_CURRENT_USER_KEY)
            }
        }
        return raw ? JSON.parse(raw) : null
    } catch {
        return null
    }
}

export function setCurrentUser(user) {
    if (user) localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(CURRENT_USER_KEY)
    lastCurrentUserSyncAt = user ? Date.now() : 0

    // Let mounted components update without a refresh.
    window.dispatchEvent(new Event('uah-user-updated'))
}

export function setAuth({ access_token, user } = {}) {
    if (access_token) setAccessToken(access_token)
    else if (!SHOULD_PERSIST_ACCESS_TOKEN) setAccessToken(null)
    if (user) setCurrentUser(user)
}

export function clearAuth() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(CURRENT_USER_KEY)
    localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY)
    localStorage.removeItem(LEGACY_CURRENT_USER_KEY)
    lastCurrentUserSyncAt = 0
    window.dispatchEvent(new Event('uah-user-updated'))
}

export async function syncCurrentUser({ force = false } = {}) {
    const cachedUser = getCurrentUser()
    if (!force && cachedUser && Date.now() - lastCurrentUserSyncAt < USER_SYNC_TTL_MS) {
        return cachedUser
    }
    if (currentUserSyncPromise) {
        return currentUserSyncPromise
    }

    const token = getAccessToken()
    const headers = new Headers()
    if (token) {
        headers.set('Authorization', `Bearer ${token}`)
    }

    currentUserSyncPromise = (async () => {
        try {
            const res = await fetch('/api/auth/me', {
                headers,
                credentials: 'same-origin',
            })
            if (res.status === 401 || res.status === 404) {
                clearAuth()
                return null
            }
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`)
            }
            const user = await res.json()
            setCurrentUser(user)
            return user
        } finally {
            currentUserSyncPromise = null
        }
    })()

    return currentUserSyncPromise
}

export async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'same-origin',
        })
    } catch {
        // Local state should still clear even if backend logout cannot be reached.
    } finally {
        clearAuth()
    }
}

/**
 * Authenticated fetch with optional timeout (default 5 min for long parse ops).
 * Pass `options.timeout` in ms to override, or `options.signal` for your own AbortController.
 */
export async function authedFetch(url, options = {}) {
    const token = getAccessToken()
    const headers = new Headers(options.headers || {})
    if (token) {
        headers.set('Authorization', `Bearer ${token}`)
    }

    const timeoutMs = options.timeout ?? 300_000 // 5 minutes default
    let controller
    let timeoutId

    if (!options.signal) {
        controller = new AbortController()
        timeoutId = setTimeout(() => controller.abort(), timeoutMs)
    }

    try {
        const res = await fetch(url, {
            ...options,
            headers,
            credentials: options.credentials || 'same-origin',
            signal: options.signal || controller?.signal,
        })

        if (res.status === 401) {
            clearAuth()
            throw new Error('Session expired')
        }

        return res
    } catch (err) {
        if (err.name === 'AbortError') {
            const timeoutErr = new Error('Request timed out')
            timeoutErr.code = 'FETCH_TIMEOUT'
            throw timeoutErr
        }
        throw err
    } finally {
        if (timeoutId) clearTimeout(timeoutId)
    }
}
