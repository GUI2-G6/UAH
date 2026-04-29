import { authedFetch } from './auth.js'

export const ANALYTICS_EVENTS = Object.freeze({
  HOME_VIEWED: 'dashboard.home.viewed',
  SCAN_STARTED: 'dashboard.scan.started',
  SCAN_SUCCEEDED: 'dashboard.scan.succeeded',
  SCAN_FAILED: 'dashboard.scan.failed',
  QUICK_SCAN_CLICKED: 'dashboard.quick_action.scan_clicked',
  MARK_APPLIED_STARTED: 'dashboard.quick_action.mark_applied_started',
  MARK_APPLIED_COMPLETED: 'dashboard.quick_action.mark_applied_completed',
  TIMELINE_ITEM_OPENED: 'dashboard.timeline.item_opened',
  TIMELINE_ANALYTICS_EVENT_OPENED: 'dashboard.timeline.analytics_event_opened',
  EXPORT_STARTED: 'dashboard.export.started',
  EXPORT_AUTH_FAILED: 'dashboard.export.reauth_failed',
  EXPORT_COMPLETED: 'dashboard.export.completed',
  EXPORT_FAILED: 'dashboard.export.failed',
})

function sanitizePayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return {}
  const entries = Object.entries(payload).slice(0, 60)
  return Object.fromEntries(entries)
}

export async function trackEvent(eventType, payload = {}, sessionId = null) {
  const normalizedEventType = String(eventType || '').trim()
  if (!normalizedEventType) return { ok: false, dropped: 'missing_event_type' }

  try {
    const res = await authedFetch('/api/apply-sessions/analytics/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: normalizedEventType,
        payload: sanitizePayload(payload),
        session_id: Number.isFinite(Number(sessionId)) ? Number(sessionId) : null,
      }),
    })
    if (!res.ok) return { ok: false, dropped: `http_${res.status}` }
    const body = await res.json().catch(() => null)
    return { ok: true, body }
  } catch {
    return { ok: false, dropped: 'network' }
  }
}

