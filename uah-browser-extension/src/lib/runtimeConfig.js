function normalizeNamespace(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]/g, '_')
}

function requireHttpsOrigin(rawValue, name) {
  const value = String(rawValue || '').trim()
  if (!value) {
    throw new Error(`${name} is required`)
  }

  let parsed
  try {
    parsed = new URL(value)
  } catch {
    throw new Error(`${name} must be a valid HTTPS origin`)
  }

  if (parsed.protocol !== 'https:') {
    throw new Error(`${name} must use HTTPS`)
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw new Error(`${name} must be an origin only`)
  }

  return parsed.origin
}

const appOrigin = requireHttpsOrigin(import.meta.env.VITE_EXTENSION_APP_ORIGIN, 'VITE_EXTENSION_APP_ORIGIN')
const apiOrigin = requireHttpsOrigin(import.meta.env.VITE_EXTENSION_API_ORIGIN, 'VITE_EXTENSION_API_ORIGIN')
const namespace = normalizeNamespace(import.meta.env.VITE_EXTENSION_AUTH_NAMESPACE)
const authCookieName = String(import.meta.env.VITE_EXTENSION_AUTH_COOKIE_NAME || '').trim()
  || (namespace ? `uah_auth_${namespace}` : '')

if (!authCookieName) {
  throw new Error('Set VITE_EXTENSION_AUTH_COOKIE_NAME or VITE_EXTENSION_AUTH_NAMESPACE before building the extension.')
}

export const runtimeConfig = {
  appOrigin,
  apiOrigin,
  authCookieName,
}
