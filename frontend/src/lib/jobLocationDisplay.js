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

function normalizeComparableText(value) {
  return normalizeText(value)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function buildCountryAliases(countryCode, countryName, displayCountryName) {
  const aliases = new Set()

  for (const value of [countryCode, countryName, displayCountryName]) {
    const normalized = normalizeComparableText(value)
    if (normalized) aliases.add(normalized)
  }

  if (countryCode === 'US') {
    aliases.add('united states of america')
    aliases.add('usa')
  }

  if (countryCode === 'GB') {
    aliases.add('uk')
    aliases.add('great britain')
  }

  return aliases
}

function stripDuplicateCountrySuffix(rawLocation, aliases) {
  let cleaned = normalizeText(rawLocation)
  if (!cleaned || !aliases.size) return cleaned

  const parentheticalMatch = cleaned.match(/^(.*)\(([^()]*)\)\s*$/)
  if (parentheticalMatch && aliases.has(normalizeComparableText(parentheticalMatch[2]))) {
    cleaned = normalizeText(parentheticalMatch[1])
  }

  const commaParts = cleaned.split(',').map((part) => normalizeText(part)).filter(Boolean)
  if (commaParts.length > 1) {
    while (commaParts.length > 1 && aliases.has(normalizeComparableText(commaParts[commaParts.length - 1]))) {
      commaParts.pop()
    }
    cleaned = commaParts.join(', ')
  }

  return cleaned
}

export function formatJobLocationDisplay(job = {}) {
  const originalRawLocation = normalizeText(job?.location || job?.locations?.[0] || '')
  const countryCode = normalizeCountryCode(job?.location_country_code)
  const countryName = normalizeText(job?.location_country_name)
  const displayCountryName = isDisplayableCountryName(countryName) ? countryName : ''
  const flag = countryCodeToFlagEmoji(countryCode)
  const countryAliases = buildCountryAliases(countryCode, countryName, displayCountryName)
  const rawLocation = stripDuplicateCountrySuffix(originalRawLocation, countryAliases)

  const baseLabel = rawLocation || displayCountryName || countryName || 'Unknown location'
  const label = flag && baseLabel !== 'Unknown location'
    ? `${baseLabel} ${flag}`
    : baseLabel

  let title = ''
  if (rawLocation && displayCountryName) {
    title = `${rawLocation} · ${displayCountryName}`
  } else if (displayCountryName) {
    title = displayCountryName
  } else if (rawLocation && countryName && normalizeComparableText(rawLocation) !== normalizeComparableText(countryName)) {
    title = `${rawLocation} · ${countryName}`
  } else if (countryCode === 'XU' && rawLocation) {
    title = rawLocation
  }

  return {
    label,
    title,
    rawLocation,
    originalRawLocation,
    countryCode,
    countryName,
    flag,
  }
}
