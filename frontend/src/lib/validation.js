const EMAIL_PATTERN = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$/i
const PHONE_ALLOWED_PATTERN = /^[0-9+\-().\s]+$/

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
  const raw = String(value || '').trim()
  if (!raw) return ''

  if (!PHONE_ALLOWED_PATTERN.test(raw)) {
    throw new Error('Please enter a valid phone number')
  }

  const hasPlus = raw.startsWith('+')
  const digits = raw.replace(/\D/g, '')
  if (digits.length < 7 || digits.length > 15) {
    throw new Error('Please enter a valid phone number')
  }

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
