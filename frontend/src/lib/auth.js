const ACCESS_TOKEN_KEY = 'uah_access_token'
const CURRENT_USER_KEY = 'uah_current_user'

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
    const token = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (token && isTokenExpired(token)) {
        clearAuth()
        return null
    }
    return token
}

export function setAccessToken(token) {
    if (token) localStorage.setItem(ACCESS_TOKEN_KEY, token)
    else localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getCurrentUser() {
    try {
        const raw = localStorage.getItem(CURRENT_USER_KEY)
        return raw ? JSON.parse(raw) : null
    } catch {
        return null
    }
}

export function setCurrentUser(user) {
    if (user) localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(CURRENT_USER_KEY)

    // Let mounted components update without a refresh.
    window.dispatchEvent(new Event('uah-user-updated'))
}

export function setAuth({ access_token, user } = {}) {
    if (access_token) setAccessToken(access_token)
    if (user) setCurrentUser(user)
}

export function clearAuth() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(CURRENT_USER_KEY)
    window.dispatchEvent(new Event('uah-user-updated'))
}

/**
 * Authenticated fetch with optional timeout (default 5 min for long parse ops).
 * Pass `options.timeout` in ms to override, or `options.signal` for your own AbortController.
 */
export async function authedFetch(url, options = {}) {
    const token = getAccessToken()
    if (!token) {
        throw new Error('Not authenticated')
    }

    const headers = new Headers(options.headers || {})
    headers.set('Authorization', `Bearer ${token}`)

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
