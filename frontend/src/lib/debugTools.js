import { getAuthNamespace, getCurrentUser } from './auth.js'

const DEBUG_TOOLS_STORAGE_PREFIX = 'uah_debug_tools_enabled'
const DEBUG_TOOLS_EVENT = 'uah-debug-tools-updated'

function storageKey() {
  return `${DEBUG_TOOLS_STORAGE_PREFIX}:${getAuthNamespace()}`
}

function parseStoredBoolean(value) {
  if (value === null || value === undefined || value === '') return null
  const normalized = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return null
}

function dispatchDebugToolsEvent(state) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(DEBUG_TOOLS_EVENT, { detail: state }))
}

export function canAccessDebugTools(user = getCurrentUser()) {
  return user?.is_developer === true
}

export function isAdminUser(user = getCurrentUser()) {
  return user?.is_admin === true
}

export function getDebugToolsPreference(user = getCurrentUser()) {
  if (!canAccessDebugTools(user)) return false

  try {
    const stored = parseStoredBoolean(window.localStorage.getItem(storageKey()))
    return stored === null ? true : stored
  } catch {
    return true
  }
}

export function shouldShowDebugTools(user = getCurrentUser()) {
  return canAccessDebugTools(user) && getDebugToolsPreference(user)
}

export function getDebugToolsState(user = getCurrentUser()) {
  return {
    canAccessDebugTools: canAccessDebugTools(user),
    showDebugTools: shouldShowDebugTools(user),
  }
}

export function setDebugToolsPreference(enabled, user = getCurrentUser()) {
  const nextState = {
    canAccessDebugTools: canAccessDebugTools(user),
    showDebugTools: false,
  }

  try {
    if (!nextState.canAccessDebugTools) {
      window.localStorage.removeItem(storageKey())
      dispatchDebugToolsEvent(nextState)
      return nextState
    }

    window.localStorage.setItem(storageKey(), enabled ? 'true' : 'false')
    nextState.showDebugTools = enabled === true
    dispatchDebugToolsEvent(nextState)
    return nextState
  } catch {
    nextState.showDebugTools = enabled === true && nextState.canAccessDebugTools
    dispatchDebugToolsEvent(nextState)
    return nextState
  }
}

export function subscribeDebugTools(listener) {
  if (typeof window === 'undefined') {
    listener(getDebugToolsState())
    return () => {}
  }

  const emit = () => {
    listener(getDebugToolsState())
  }

  const onStorage = (event) => {
    if (event?.key && event.key !== storageKey()) return
    emit()
  }

  window.addEventListener(DEBUG_TOOLS_EVENT, emit)
  window.addEventListener('storage', onStorage)
  window.addEventListener('uah-user-updated', emit)
  emit()

  return () => {
    window.removeEventListener(DEBUG_TOOLS_EVENT, emit)
    window.removeEventListener('storage', onStorage)
    window.removeEventListener('uah-user-updated', emit)
  }
}
