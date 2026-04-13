const EMAIL_PATTERN = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$/i
const PHONE_ALLOWED_PATTERN = /^[0-9+\-().\s]+$/
const PHONE_COUNTRY_CODES = [
  { prefix: '1', code: 'US', label: 'United States' },
  { prefix: '44', code: 'GB', label: 'United Kingdom' },
  { prefix: '49', code: 'DE', label: 'Germany' },
  { prefix: '61', code: 'AU', label: 'Australia' },
  { prefix: '81', code: 'JP', label: 'Japan' },
  { prefix: '91', code: 'IN', label: 'India' },
]

function getPhoneParts(value) {
  const raw = String(value || '').trim()
  if (!raw) {
    return { raw: '', digits: '', hasPlus: false }
  }

  if (!PHONE_ALLOWED_PATTERN.test(raw)) {
    throw new Error('Please enter a valid phone number')
  }

  const hasPlus = raw.startsWith('+')
  const digits = raw.replace(/\D/g, '')
  if (digits.length < 7 || digits.length > 15) {
    throw new Error('Please enter a valid phone number')
  }

  return { raw, digits, hasPlus }
}

export function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase()
}

export function isValidEmail(value) {
  const normalized = normalizeEmail(value)
  return EMAIL_PATTERN.test(normalized)
}

export function assertValidEmail(value, label = 'email') {
  const normalized = normalizeEmail(value)
  if (!normalized) {
    throw new Error(`Please enter your ${label}`)
  }
  if (!isValidEmail(normalized)) {
    throw new Error('Please enter a valid email address')
  }
  return normalized
}

export function normalizePhone(value) {
  const { digits, hasPlus } = getPhoneParts(value)
  if (!digits) return ''

  if (!hasPlus) {
    if (digits.length === 10) {
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
    }
    if (digits.length === 11 && digits.startsWith('1')) {
      return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`
    }
  }

  if (hasPlus) return `+${digits}`
  return digits
}

export function buildMailtoHref(value) {
  const normalized = normalizeEmail(value)
  if (!normalized || !isValidEmail(normalized)) return ''
  return `mailto:${normalized}`
}

export function buildPhoneHref(value) {
  try {
    const normalized = normalizePhone(value)
    if (!normalized) return ''

    if (normalized.startsWith('+')) {
      return `tel:${normalized}`
    }

    const digits = normalized.replace(/\D/g, '')
    if (digits.length === 10) {
      return `tel:+1${digits}`
    }
    if (digits.length === 11 && digits.startsWith('1')) {
      return `tel:+${digits}`
    }
    return `tel:${digits}`
  } catch {
    return ''
  }
}

export function inferPhoneCountry(value) {
  try {
    const { digits, hasPlus } = getPhoneParts(value)
    if (!digits) return null

    if (!hasPlus) {
      if (digits.length === 10 || (digits.length === 11 && digits.startsWith('1'))) {
        return { code: 'US', label: 'United States' }
      }
      return null
    }

    for (const candidate of PHONE_COUNTRY_CODES) {
      if (digits.startsWith(candidate.prefix)) {
        return {
          code: candidate.code,
          label: candidate.label,
        }
      }
    }

    return null
  } catch {
    return null
  }
}
