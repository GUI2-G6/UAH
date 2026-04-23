/**
 * Shared appearance preference for main app and landing (same origin = same localStorage).
 * Persisted: light | dark | system. Document always gets data-theme light | dark (resolved).
 */

export const THEME_STORAGE_KEY = 'uah-theme-preference'

const VALID = new Set(['light', 'dark', 'system'])

/** @returns {'light'|'dark'|'system'|null} */
export function getStoredPreference() {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY)
    if (raw == null || raw === '') return null
    const v = String(raw).trim().toLowerCase()
    return VALID.has(v) ? /** @type {'light'|'dark'|'system'} */ (v) : null
  } catch {
    return null
  }
}

/** @param {'light'|'dark'|'system'} pref */
export function setStoredPreference(pref) {
  if (!VALID.has(pref)) return
  try {
    localStorage.setItem(THEME_STORAGE_KEY, pref)
  } catch {
    /* ignore */
  }
}

/** @param {'light'|'dark'|'system'|null} pref */
export function resolveEffectiveTheme(pref) {
  if (pref === 'light') return 'light'
  if (pref === 'dark') return 'dark'
  if (typeof window !== 'undefined' && window.matchMedia) {
    try {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    } catch {
      return 'light'
    }
  }
  return 'light'
}

/** @param {'light'|'dark'} effective */
export function applyDocumentTheme(effective) {
  if (typeof document === 'undefined') return
  document.documentElement.dataset.theme = effective
  syncMetaThemeColor(effective)
}

/** Apply from storage + system (call on load and when preference changes). */
export function applyThemeFromStorage() {
  const pref = getStoredPreference()
  const effective = resolveEffectiveTheme(pref ?? 'system')
  applyDocumentTheme(effective)
  return { pref: pref ?? 'system', effective }
}

export function initThemeListeners() {
  if (typeof window === 'undefined') return () => {}

  const onStorage = (e) => {
    if (e.key === THEME_STORAGE_KEY || e.key === null) {
      applyThemeFromStorage()
    }
  }
  window.addEventListener('storage', onStorage)
  const removeStorage = () => window.removeEventListener('storage', onStorage)

  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const onMedia = () => {
    const pref = getStoredPreference() ?? 'system'
    if (pref === 'system') {
      applyDocumentTheme(resolveEffectiveTheme('system'))
    }
  }
  let removeMedia = () => {}
  if (typeof mq.addEventListener === 'function') {
    mq.addEventListener('change', onMedia)
    removeMedia = () => mq.removeEventListener('change', onMedia)
  } else {
    mq.addListener(onMedia)
    removeMedia = () => mq.removeListener(onMedia)
  }

  return () => {
    removeMedia()
    removeStorage()
  }
}

/** @param {'light'|'dark'} effective */
function syncMetaThemeColor(effective) {
  const meta = document.querySelector('meta[name="theme-color"]')
  if (!meta) return
  meta.setAttribute('content', effective === 'dark' ? '#0f172a' : '#1f5c99')
}

/**
 * @param {'light'|'dark'|'system'} pref
 * @returns {{ pref: 'light'|'dark'|'system', effective: 'light'|'dark' }}
 */
export function setPreferenceAndApply(pref) {
  setStoredPreference(pref)
  const effective = resolveEffectiveTheme(pref)
  applyDocumentTheme(effective)
  if (typeof window !== 'undefined') {
    try {
      window.dispatchEvent(new CustomEvent('uah-theme-changed', { detail: { pref, effective } }))
    } catch {
      /* ignore */
    }
  }
  return { pref, effective }
}

const CYCLE_ORDER = /** @type {const} */ (['system', 'light', 'dark'])

/** @param {'light'|'dark'|'system'} current */
export function nextThemePreference(current) {
  const i = CYCLE_ORDER.indexOf(current)
  const next = CYCLE_ORDER[(i === -1 ? 0 : i + 1) % CYCLE_ORDER.length]
  return next
}

/** @param {'light'|'dark'|'system'} pref */
export function themePreferenceLabel(pref) {
  if (pref === 'light') return 'Light'
  if (pref === 'dark') return 'Dark'
  return 'System'
}
