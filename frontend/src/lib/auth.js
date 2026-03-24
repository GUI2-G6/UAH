const ACCESS_TOKEN_KEY = 'uah_access_token'
const CURRENT_USER_KEY = 'uah_current_user'

export function getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
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

export async function authedFetch(url, options = {}) {
    const token = getAccessToken()
    if (!token) {
        throw new Error('Not authenticated')
    }

    const headers = new Headers(options.headers || {})
    headers.set('Authorization', `Bearer ${token}`)

    return fetch(url, {
        ...options,
        headers,
    })
}
