import { showToast } from '@/services/toastService.js'

const RECOVERY_KEY_PREFIX = 'uah:chunk-recovery:'
const HANDLER_INSTALLED_KEY = '__uahChunkHandlersInstalled'

function getStorage() {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function normalizeErrorMessage(errorLike) {
  if (!errorLike) return ''
  if (typeof errorLike === 'string') return errorLike
  if (typeof errorLike?.message === 'string') return errorLike.message
  if (typeof errorLike?.reason?.message === 'string') return errorLike.reason.message
  return String(errorLike)
}

export function isChunkLoadFailure(errorLike) {
  const message = normalizeErrorMessage(errorLike).toLowerCase()
  return (
    message.includes('failed to fetch dynamically imported module')
    || message.includes('chunkloaderror')
    || message.includes('loading chunk')
  )
}

export function getChunkRecoveryAction(routePath = '') {
  const normalizedPath = String(routePath || window?.location?.pathname || '/').trim() || '/'
  const storage = getStorage()
  const key = `${RECOVERY_KEY_PREFIX}${normalizedPath}`
  if (!storage) return { action: 'reload', key }

  const alreadyTried = storage.getItem(key) === '1'
  if (alreadyTried) {
    return { action: 'notify', key }
  }
  storage.setItem(key, '1')
  return { action: 'reload', key }
}

function reportChunkFailure(stage, metadata = {}) {
  const payload = {
    stage,
    source: String(metadata.source || 'unknown'),
    route_path: String(metadata.routePath || window?.location?.pathname || ''),
    message: String(metadata.message || '').slice(0, 400),
    href: String(window?.location?.href || ''),
  }
  try {
    fetch('/api/apply-sessions/analytics/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      keepalive: true,
      body: JSON.stringify({
        event_type: 'app.runtime.chunk_load_failure',
        payload,
      }),
    }).catch(() => {})
  } catch {
    // Ignore telemetry failures
  }
}

export function handleChunkLoadFailure(errorLike, { source = 'unknown', routePath = '' } = {}) {
  if (!isChunkLoadFailure(errorLike)) return false

  const message = normalizeErrorMessage(errorLike)
  const outcome = getChunkRecoveryAction(routePath)
  reportChunkFailure('detected', { source, routePath, message })

  if (outcome.action === 'reload') {
    reportChunkFailure('reload_attempted', { source, routePath, message })
    window.location.reload()
    return true
  }

  reportChunkFailure('fallback_notice_shown', { source, routePath, message })
  showToast('A new app version is available. Please hard refresh this page.', 'error')
  return true
}

export function installGlobalChunkErrorHandlers() {
  if (window[HANDLER_INSTALLED_KEY] === true) return
  window[HANDLER_INSTALLED_KEY] = true

  window.addEventListener('error', (event) => {
    handleChunkLoadFailure(event?.error || event?.message, {
      source: 'window.error',
      routePath: window?.location?.pathname || '/',
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    handleChunkLoadFailure(event?.reason, {
      source: 'window.unhandledrejection',
      routePath: window?.location?.pathname || '/',
    })
  })
}

