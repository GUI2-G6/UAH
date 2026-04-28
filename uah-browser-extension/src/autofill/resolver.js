import { GOOD_MATCH_THRESHOLD, REVIEW_MATCH_THRESHOLD, normalizeText } from './shared.js'

const SENSITIVE_LABEL_MARKERS = [
  'ssn',
  'social security',
  'date of birth',
  'dob',
  'birth date',
  'veteran',
  'disability',
  'gender',
  'ethnicity',
  'race',
  'work authorization',
  'authorized to work',
  'sponsorship',
  'visa',
]

const SENSITIVE_PATH_MARKERS = [
  'work_auth',
  'requires_sponsorship',
  'demographic_',
  'veteran_status',
  'disability_status',
]

export function classifyConfidence(score) {
  const numeric = Number(score || 0)
  if (numeric >= 0.99) return 'exact'
  if (numeric >= GOOD_MATCH_THRESHOLD) return 'high'
  if (numeric >= REVIEW_MATCH_THRESHOLD) return 'review'
  return 'blocked'
}

export function isSensitiveField(field = {}, matchPath = '') {
  const label = normalizeText(field.labelNorm || field.label || '')
  const path = normalizeText(matchPath || '')
  if (!label && !path) return false
  if (SENSITIVE_LABEL_MARKERS.some((marker) => label.includes(normalizeText(marker)))) return true
  if (SENSITIVE_PATH_MARKERS.some((marker) => path.includes(normalizeText(marker)))) return true
  return false
}

export function resolveFieldPolicy(field = {}, { matchPath = null, matchScore = 0, reason = '' } = {}) {
  const confidenceClass = classifyConfidence(matchScore)
  const sensitive = isSensitiveField(field, matchPath || '')
  const requiresApproval = sensitive || confidenceClass === 'review' || confidenceClass === 'blocked'
  return {
    confidenceClass,
    sensitive,
    requiresApproval,
    reason: reason || (matchPath ? 'token-match' : 'no-match'),
  }
}
