const NON_FLAG_COUNTRY_CODES = new Set(['XX', 'XU', 'ALL'])
const SENTINEL_COUNTRY_NAMES = new Set(['Remote / Global', 'Uncertain'])

function normalizeText(value) {
  return String(value || '').trim().replace(/\s+/g, ' ')
}

export function normalizeCountryCode(value) {
  return normalizeText(value).toUpperCase()
}

export function isFlaggableCountryCode(value) {
  const normalized = normalizeCountryCode(value)
  return /^[A-Z]{2}$/.test(normalized) && !NON_FLAG_COUNTRY_CODES.has(normalized)
}

export function countryCodeToFlagEmoji(value) {
  const normalized = normalizeCountryCode(value)
  if (!isFlaggableCountryCode(normalized)) return ''

  return [...normalized]
    .map((char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
    .join('')
}

function isDisplayableCountryName(value) {
  const normalized = normalizeText(value)
  return Boolean(normalized) && !SENTINEL_COUNTRY_NAMES.has(normalized)
}

export function formatJobLocationDisplay(job = {}) {
  const rawLocation = normalizeText(job?.location || job?.locations?.[0] || '')
  const countryCode = normalizeCountryCode(job?.location_country_code)
  const countryName = normalizeText(job?.location_country_name)
  const displayCountryName = isDisplayableCountryName(countryName) ? countryName : ''
  const flag = countryCodeToFlagEmoji(countryCode)

  const baseLabel = rawLocation || displayCountryName || countryName || 'Unknown location'
  const label = flag && baseLabel !== 'Unknown location'
    ? `${baseLabel} ${flag}`
    : baseLabel

  let title = ''
  if (rawLocation && displayCountryName) {
    title = `${rawLocation} · ${displayCountryName}`
  } else if (displayCountryName) {
    title = displayCountryName
  } else if (countryCode === 'XU' && rawLocation) {
    title = rawLocation
  }

  return {
    label,
    title,
    rawLocation,
    countryCode,
    countryName,
    flag,
  }
}
