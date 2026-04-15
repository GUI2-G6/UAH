import { flattenResume } from './shared.js'

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function cleanTokenValue(value) {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const normalized = String(value ?? '').trim()
  return normalized || null
}

function sanitizeTokenValue(value) {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const normalized = value.trim()
    return normalized || null
  }
  if (Array.isArray(value) && value.every((item) => typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean')) {
    return cleanTokenValue(value.join(', '))
  }
  return null
}

export function sanitizeTokenMap(tokenMap = {}) {
  const sanitized = {}

  Object.entries(isObject(tokenMap) ? tokenMap : {}).forEach(([rawKey, rawValue]) => {
    const key = String(rawKey || '').trim()
    if (!key) return

    const normalizedValue = sanitizeTokenValue(rawValue)
    if (normalizedValue !== null) {
      sanitized[key] = normalizedValue
    }
  })

  return sanitized
}

export function buildProfileAutofillSource(profile = {}) {
  const baseTokenMap = sanitizeTokenMap(
    isObject(profile.token_map) && Object.keys(profile.token_map).length
      ? profile.token_map
      : flattenResume(isObject(profile.canonical_data) ? profile.canonical_data : {})
  )

  const extraTokens = {
    work_auth: cleanTokenValue(profile.work_auth),
    requires_sponsorship: cleanTokenValue(profile.requires_sponsorship),
    years_experience: cleanTokenValue(profile.years_experience),
    professional_links_text: cleanTokenValue(profile.professional_links_text),
  }

  Object.entries(extraTokens).forEach(([key, value]) => {
    if (value !== null) baseTokenMap[key] = value
  })

  const fallbackName = [profile.first_name, profile.last_name].filter(Boolean).join(' ').trim()
  const sourceName = String(profile.name || fallbackName || 'Selected profile').trim()

  return {
    source: {
      type: 'profile',
      profileId: typeof profile.id === 'number' ? profile.id : null,
      profileName: sourceName,
    },
    tokenMap: baseTokenMap,
    tokenCount: Object.keys(baseTokenMap).length,
  }
}
