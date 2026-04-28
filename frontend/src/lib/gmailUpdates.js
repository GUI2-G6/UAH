import { authedFetch, getCurrentUser } from './auth.js'

const STORAGE_PREFIX = 'uah_gmail_scan_cache:'
const UPDATE_EVENT = 'uah-gmail-updates'
const GMAIL_STATUS_TTL_MS = 15_000

let cachedGmailConnected = null
let cachedGmailConnectedAt = 0

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

function normalizeNotificationState(item = {}) {
  const state = sanitizeText(item.state, 40).toLowerCase()
  const sourceId = sanitizeText(item.source_id, 255)
  const snoozedUntilRaw = sanitizeText(item.snoozed_until, 120)
  const snoozedUntil = normalizeDate(snoozedUntilRaw)
  return {
    id: Number.isFinite(Number(item.id)) ? Number(item.id) : null,
    source_id: sourceId,
    state: state === 'dismissed' ? 'dismissed' : (state === 'snoozed' ? 'snoozed' : ''),
    snoozed_until: snoozedUntil || '',
  }
}

function normalizeResult(item = {}) {
  const status = normalizeStatus(item.detected_status)
  return {
    source_id: sanitizeText(item.source_id, 255),
    subject: sanitizeText(item.subject, 260),
    from: sanitizeText(item.from, 260),
    date: normalizeDate(item.date),
    detected_status: String(item.detected_status || 'unknown'),
    status_bucket: status,
    company_hint: sanitizeText(item.company_hint, 120) || null,
    snippet: sanitizeText(item.snippet, 420),
    body_preview: sanitizeText(item.body_preview, 1600),
    ats_detected: item.ats_detected === true,
    job_update_detected: item.job_update_detected === true,
    matched_applied_job: item.matched_applied_job === true,
    tracking_source: sanitizeText(item.tracking_source, 40) || 'gmail',
    confidence: sanitizeText(item.confidence, 24) || 'high',
    sender_domain: sanitizeText(item.sender_domain, 255),
    subject_key: sanitizeText(item.subject_key, 160),
    company_key: sanitizeText(item.company_key, 120),
    thread_key: sanitizeText(item.thread_key, 380),
    gmail_open_url_direct: sanitizeText(item.gmail_open_url_direct, 500),
    gmail_open_url_fallback: sanitizeText(item.gmail_open_url_fallback, 500),
    tracked_id: Number.isFinite(Number(item.tracked_id)) ? Number(item.tracked_id) : null,
    has_new_update: item.has_new_update === true,
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

export function filterResultsByNotificationStates(results = [], notificationStates = []) {
  const now = Date.now()
  const stateBySourceId = new Map()
  for (const rawState of notificationStates) {
    const state = normalizeNotificationState(rawState)
    if (!state.source_id || !state.state) continue
    stateBySourceId.set(state.source_id, state)
  }
  return (Array.isArray(results) ? results : []).filter((rawItem) => {
    const item = normalizeResult(rawItem)
    const state = stateBySourceId.get(item.source_id)
    if (!state) return true
    if (state.state === 'dismissed') return false
    if (state.state === 'snoozed') {
      const untilMs = Date.parse(state.snoozed_until || '')
      return Number.isNaN(untilMs) || untilMs <= now
    }
    return true
  })
}

export function readGmailScanCache() {
  const cached = safeParse(localStorage.getItem(storageKeyForCurrentUser()))
  if (!cached) return null
  const results = Array.isArray(cached.results)
    ? cached.results
    : [
      ...(Array.isArray(cached.matched_results) ? cached.matched_results : []),
      ...(Array.isArray(cached.provisional_results) ? cached.provisional_results : []),
    ]
  const normalizedResults = results.slice(0, 250).map(normalizeResult)
  return {
    ...cached,
    results: normalizedResults,
    summary: summarizeGmailResults(normalizedResults),
  }
}

export function writeGmailScanCache(payload = {}) {
  const normalizedResults = Array.isArray(payload.results)
    ? payload.results.slice(0, 250).map(normalizeResult)
    : (Array.isArray(payload.matched_results)
      ? payload.matched_results.slice(0, 250).map(normalizeResult)
      : [])
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

function normalizeScanOptions(options = {}) {
  const newerThanRaw = Number(options?.newer_than_days)
  const maxResultsRaw = Number(options?.max_results)
  const rawMode = String(options?.scan_mode || 'new').trim().toLowerCase()
  const scanMode = rawMode === 'saved' ? 'saved' : 'new'
  const sourceStrictness = String(options?.source_strictness || 'strict_career_domains').trim().toLowerCase() === 'hybrid_job_language'
    ? 'hybrid_job_language'
    : 'strict_career_domains'
  const linkedinModeRaw = String(options?.linkedin_mode || 'linkedin_apply_only').trim().toLowerCase()
  const linkedinMode = ['linkedin_apply_only', 'linkedin_all_jobish', 'linkedin_off'].includes(linkedinModeRaw)
    ? linkedinModeRaw
    : 'linkedin_apply_only'
  return {
    scan_mode: scanMode,
    source_strictness: sourceStrictness,
    linkedin_mode: linkedinMode,
    query: sanitizeText(options?.query, 280) || null,
    newer_than_days: Number.isFinite(newerThanRaw) ? Math.min(36500, Math.max(1, Math.round(newerThanRaw))) : 45,
    max_results: Number.isFinite(maxResultsRaw) ? Math.min(100, Math.max(1, Math.round(maxResultsRaw))) : 20,
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

export async function resolveGmailConnectionStatus(fallbackConnected = false, options = {}) {
  const force = options?.force === true
  const now = Date.now()
  if (!force && cachedGmailConnected !== null && (now - cachedGmailConnectedAt) < GMAIL_STATUS_TTL_MS) {
    return cachedGmailConnected
  }

  try {
    const response = await authedFetch('/api/integrations/services/gmail')
    const payload = await response.json().catch(() => null)
    if (response.ok) {
      const connected = payload?.connected === true || String(payload?.status || '').toLowerCase() === 'connected'
      cachedGmailConnected = connected
      cachedGmailConnectedAt = Date.now()
      return connected
    }
  } catch {
    // Fall back to local user metadata when service status cannot be fetched.
  }

  const fallbackUserConnected = Boolean(getCurrentUser()?.gmail_refresh_token)
  const connected = fallbackUserConnected || Boolean(fallbackConnected)
  cachedGmailConnected = connected
  cachedGmailConnectedAt = Date.now()
  return connected
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
    const detail = String(payload?.detail || '')
    if (detail.toLowerCase().includes('gmail not connected')) {
      throw new Error('Gmail is not connected. Open Settings > Service Connections > Gmail Updates.')
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return writeGmailScanCache({
    gmail_email: payload?.gmail_email || null,
    scan_scope: payload?.scan_scope || null,
    results: Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload?.matched_results) ? payload.matched_results : []),
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

export async function createGmailFeedback(data = {}) {
  const response = await authedFetch('/api/integrations/gmail/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return payload?.feedback || null
}

export async function listGmailFeedback() {
  const response = await authedFetch('/api/integrations/gmail/feedback')
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return Array.isArray(payload?.feedback) ? payload.feedback : []
}

export async function listGmailNotificationStates() {
  const response = await authedFetch('/api/integrations/gmail/notification-states')
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  const rows = Array.isArray(payload?.notification_states) ? payload.notification_states : []
  return rows.map(normalizeNotificationState).filter((row) => row.source_id && row.state)
}

export async function upsertGmailNotificationState(data = {}) {
  const response = await authedFetch('/api/integrations/gmail/notification-states', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return normalizeNotificationState(payload?.notification_state || {})
}

export async function removeGmailNotificationState(sourceId) {
  const response = await authedFetch(`/api/integrations/gmail/notification-states/${encodeURIComponent(String(sourceId || ''))}`, {
    method: 'DELETE',
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
  return payload
}
