const VALID_THEME_PREFERENCES = new Set(['system', 'light', 'dark'])

export function normalizeThemePreference(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return VALID_THEME_PREFERENCES.has(normalized) ? normalized : 'system'
}

export function resolveEffectiveTheme(preference, win = globalThis.window) {
  const normalized = normalizeThemePreference(preference)
  if (normalized === 'light') return 'light'
  if (normalized === 'dark') return 'dark'
  if (!win || typeof win.matchMedia !== 'function') return 'light'
  try {
    return win.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

export function applyDocumentTheme(effectiveTheme, doc = globalThis.document) {
  if (!doc?.documentElement) return
  doc.documentElement.dataset.theme = effectiveTheme
}
