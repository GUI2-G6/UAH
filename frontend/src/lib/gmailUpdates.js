import { authedFetch, getCurrentUser } from './auth.js'

const STORAGE_PREFIX = 'uah_gmail_scan_cache:'
const UPDATE_EVENT = 'uah-gmail-updates'

function storageKeyForCurrentUser() {
  const user = getCurrentUser()
  const userId = user?.id || user?.email || 'anonymous'
  return `${STORAGE_PREFIX}${String(userId)}`
}

function safeParse(value) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function normalizeStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'application_received') return 'applied'
  if (normalized === 'interview_invite') return 'interview'
  if (normalized === 'offer') return 'offer'
  if (normalized === 'rejection') return 'rejection'
  return 'unknown'
}

function sanitizeText(value, maxLen = 320) {
  const normalized = String(value ?? '').replace(/[\x00-\x1F\x7F]/g, ' ').trim()
  return normalized.slice(0, maxLen)
}

function normalizeDate(value) {
  const raw = sanitizeText(value ?? '', 120)
  if (!raw) return ''
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  return parsed.toISOString()
}

function normalizeResult(item = {}) {
  const status = normalizeStatus(item.detected_status)
  return {
    subject: sanitizeText(item.subject, 260),
    from: sanitizeText(item.from, 260),
    date: normalizeDate(item.date),
    detected_status: String(item.detected_status || 'unknown'),
    status_bucket: status,
    company_hint: sanitizeText(item.company_hint, 120) || null,
    snippet: sanitizeText(item.snippet, 420),
    ats_detected: item.ats_detected === true,
    matched_applied_job: item.matched_applied_job === true,
  }
}

export function summarizeGmailResults(results = []) {
  const summary = {
    total: 0,
    applied: 0,
    interview: 0,
    offer: 0,
    rejection: 0,
    unknown: 0,
    action_required: 0,
    upcoming: 0,
  }
  for (const raw of results) {
    const item = normalizeResult(raw)
    summary.total += 1
    summary[item.status_bucket] = Number(summary[item.status_bucket] || 0) + 1
  }
  summary.action_required = summary.interview + summary.offer
  summary.upcoming = summary.interview
  return summary
}

export function readGmailScanCache() {
  const cached = safeParse(localStorage.getItem(storageKeyForCurrentUser()))
  if (!cached || !Array.isArray(cached.results)) return null
  const normalizedResults = cached.results.slice(0, 250).map(normalizeResult)
  return {
    ...cached,
    results: normalizedResults,
    summary: summarizeGmailResults(normalizedResults),
  }
}

export function writeGmailScanCache(payload = {}) {
  const normalizedResults = Array.isArray(payload.results) ? payload.results.slice(0, 250).map(normalizeResult) : []
  const record = {
    fetched_at: payload.fetched_at || new Date().toISOString(),
    gmail_email: sanitizeText(payload.gmail_email, 255) || null,
    scan_scope: payload.scan_scope || null,
    results: normalizedResults,
  }
  localStorage.setItem(storageKeyForCurrentUser(), JSON.stringify(record))
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT, { detail: record }))
  return {
    ...record,
    summary: summarizeGmailResults(normalizedResults),
  }
}

export function subscribeGmailUpdates(onUpdate) {
  if (typeof onUpdate !== 'function') return () => {}
  const handler = (event) => {
    const detail = event?.detail || readGmailScanCache()
    onUpdate({
      ...(detail || {}),
      results: Array.isArray(detail?.results) ? detail.results.map(normalizeResult) : [],
      summary: summarizeGmailResults(Array.isArray(detail?.results) ? detail.results : []),
    })
  }
  window.addEventListener(UPDATE_EVENT, handler)
  return () => window.removeEventListener(UPDATE_EVENT, handler)
}

export async function runGmailScan() {
  const response = await authedFetch('/api/integrations/gmail/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail || `HTTP ${response.status}`)
  }
  return writeGmailScanCache({
    gmail_email: payload?.gmail_email || null,
    scan_scope: payload?.scan_scope || null,
    results: Array.isArray(payload?.results) ? payload.results : [],
    fetched_at: new Date().toISOString(),
  })
}
