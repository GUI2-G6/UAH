import { URL } from 'node:url'

function normalizeNamespace(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]/g, '_')
}

function requireHttpsOrigin(rawValue, envName) {
  const value = String(rawValue || '').trim()
  if (!value) {
    throw new Error(`${envName} is required`)
  }

  let parsed
  try {
    parsed = new URL(value)
  } catch {
    throw new Error(`${envName} must be a valid HTTPS origin`)
  }

  if (parsed.protocol !== 'https:') {
    throw new Error(`${envName} must use HTTPS`)
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw new Error(`${envName} must be an origin only, without a path, query, or hash`)
  }

  return parsed.origin
}

export function resolveExtensionBuildConfig(rawEnv) {
  const appOrigin = requireHttpsOrigin(rawEnv.VITE_EXTENSION_APP_ORIGIN, 'VITE_EXTENSION_APP_ORIGIN')
  const apiOrigin = requireHttpsOrigin(rawEnv.VITE_EXTENSION_API_ORIGIN, 'VITE_EXTENSION_API_ORIGIN')
  const namespace = normalizeNamespace(rawEnv.VITE_EXTENSION_AUTH_NAMESPACE)
  const authCookieName = String(rawEnv.VITE_EXTENSION_AUTH_COOKIE_NAME || '').trim()
    || (namespace ? `uah_auth_${namespace}` : '')

  if (!authCookieName) {
    throw new Error(
      'Set VITE_EXTENSION_AUTH_COOKIE_NAME or VITE_EXTENSION_AUTH_NAMESPACE so the extension knows which auth cookie to read.'
    )
  }

  return {
    appOrigin,
    apiOrigin,
    apiHostPermission: `${apiOrigin}/*`,
    authCookieName,
  }
}

export function buildManifest(rawEnv) {
  const config = resolveExtensionBuildConfig(rawEnv)

  return {
    manifest_version: 3,
    name: 'UAH Browser Extension',
    version: '0.1.0',
    description: 'Quick access to UAH applicant profiles and resume data from your browser toolbar.',
    action: {
      default_title: 'UAH',
      default_popup: 'popup.html',
    },
    background: {
      service_worker: 'background.js',
      type: 'module',
    },
    // `storage`: persists extension auth metadata across browser restarts and
    // keeps non-sensitive per-session caches in chrome.storage.session.
    // `cookies`: reads and clears the backend auth cookie for Google sign-in
    // bridge support and explicit logout cleanup.
    // `tabs`: opens UAH pages in a new tab and watches the Google OAuth tab
    // until it lands back on the configured UAH app origin.
    // `activeTab` + `scripting`: enable the manual profile-driven scan/fill
    // workflow on the current tab only.
    permissions: ['storage', 'cookies', 'tabs', 'activeTab', 'scripting'],
    // Restrict all backend access to the configured UAH HTTPS origin only.
    host_permissions: [config.apiHostPermission],
    web_accessible_resources: [
      {
        resources: ['popup.html', 'assets/*'],
        matches: ['<all_urls>'],
      },
    ],
    content_security_policy: {
      extension_pages: "script-src 'self'; object-src 'self';",
    },
  }
}
