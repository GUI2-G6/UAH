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
  const trackingSource = sanitizeText(item.tracking_source, 40) || (item.matched_applied_job ? 'matched' : 'gmail_provisional')
  const confidence = sanitizeText(item.confidence, 24) || (trackingSource === 'matched' ? 'high' : 'medium')
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
    tracking_source: trackingSource,
    confidence,
  }
}

export function summarizeGmailResults(results = []) {
  const summary = {
    total: 0,
    matched_total: 0,
    provisional_total: 0,
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
    if (item.tracking_source === 'gmail_provisional') {
      summary.provisional_total += 1
    } else {
      summary.matched_total += 1
    }
    summary[item.status_bucket] = Number(summary[item.status_bucket] || 0) + 1
  }
  summary.action_required = summary.interview + summary.offer
  summary.upcoming = summary.interview
  return summary
}

export function readGmailScanCache() {
  const cached = safeParse(localStorage.getItem(storageKeyForCurrentUser()))
  if (!cached) return null
  const matched = Array.isArray(cached.matched_results) ? cached.matched_results : (Array.isArray(cached.results) ? cached.results : [])
  const provisional = Array.isArray(cached.provisional_results) ? cached.provisional_results : []
  const normalizedMatched = matched.slice(0, 250).map(normalizeResult)
  const normalizedProvisional = provisional.slice(0, 250).map(normalizeResult)
  const normalizedResults = [...normalizedMatched, ...normalizedProvisional]
  return {
    ...cached,
    matched_results: normalizedMatched,
    provisional_results: normalizedProvisional,
    results: normalizedResults,
    summary: summarizeGmailResults(normalizedResults),
  }
}

export function writeGmailScanCache(payload = {}) {
  const normalizedMatched = Array.isArray(payload.matched_results)
    ? payload.matched_results.slice(0, 250).map(normalizeResult)
    : (Array.isArray(payload.results) ? payload.results.slice(0, 250).map(normalizeResult) : [])
  const normalizedProvisional = Array.isArray(payload.provisional_results)
    ? payload.provisional_results.slice(0, 250).map(normalizeResult)
    : []
  const normalizedResults = [...normalizedMatched, ...normalizedProvisional]
  const record = {
    fetched_at: payload.fetched_at || new Date().toISOString(),
    gmail_email: sanitizeText(payload.gmail_email, 255) || null,
    scan_scope: payload.scan_scope || null,
    matched_results: normalizedMatched,
    provisional_results: normalizedProvisional,
    results: normalizedResults,
  }
  localStorage.setItem(storageKeyForCurrentUser(), JSON.stringify(record))
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT, { detail: record }))
  return {
    ...record,
    summary: summarizeGmailResults(normalizedResults),
  }
}

function normalizeScanOptions(options = {}) {
  const newerThanRaw = Number(options?.newer_than_days)
  const maxResultsRaw = Number(options?.max_results)
  return {
    query: sanitizeText(options?.query, 280) || null,
    newer_than_days: Number.isFinite(newerThanRaw) ? Math.min(365, Math.max(1, Math.round(newerThanRaw))) : 45,
    max_results: Number.isFinite(maxResultsRaw) ? Math.min(100, Math.max(1, Math.round(maxResultsRaw))) : 20,
    include_provisional: options?.include_provisional !== false,
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

export async function runGmailScan(options = {}) {
  const scanOptions = normalizeScanOptions(options)
  const response = await authedFetch('/api/integrations/gmail/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scanOptions),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail || `HTTP ${response.status}`)
  }
  return writeGmailScanCache({
    gmail_email: payload?.gmail_email || null,
    scan_scope: payload?.scan_scope || null,
    matched_results: Array.isArray(payload?.matched_results) ? payload.matched_results : (Array.isArray(payload?.results) ? payload.results : []),
    provisional_results: Array.isArray(payload?.provisional_results) ? payload.provisional_results : [],
    fetched_at: new Date().toISOString(),
  })
}

export async function listGmailSuppressions() {
  const response = await authedFetch('/api/integrations/gmail/suppressions')
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return Array.isArray(payload?.suppressions) ? payload.suppressions : []
}

export async function createGmailSuppression(data = {}) {
  const response = await authedFetch('/api/integrations/gmail/suppressions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return payload?.suppression || null
}

export async function removeGmailSuppression(id) {
  const response = await authedFetch(`/api/integrations/gmail/suppressions/${encodeURIComponent(String(id || ''))}`, {
    method: 'DELETE',
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return payload
}
