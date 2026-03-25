const MAX_REQUEST_LOGS = 30

const state = {
  route: {
    path: "",
    name: "",
    params: {},
    query: {},
  },
  routeKey: "",
  pageDiagnosticsByRoute: {},
  recentRequests: [],
  updatedAt: new Date().toISOString(),
}

const listeners = new Set()
let fetchTrackerInstalled = false

function routeKeyFromRoute(route) {
  if (!route) return "unknown"
  return String(route.name || route.path || "unknown")
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function redactSensitive(value, depth = 0) {
  if (depth > 6) return "[Truncated]"
  if (value === null || value === undefined) return value

  if (Array.isArray(value)) {
    return value.map((item) => redactSensitive(item, depth + 1))
  }

  if (typeof value === "object") {
    const redacted = {}
    for (const [key, raw] of Object.entries(value)) {
      const lower = key.toLowerCase()
      if (lower.includes("token") || lower.includes("password") || lower.includes("authorization") || lower.includes("secret")) {
        redacted[key] = "[Redacted]"
      } else {
        redacted[key] = redactSensitive(raw, depth + 1)
      }
    }
    return redacted
  }

  if (typeof value === "string" && value.length > 1200) {
    return `${value.slice(0, 1200)}...[truncated]`
  }

  return value
}

function getSnapshot() {
  const key = state.routeKey || "unknown"
  const pageDiagnostics = state.pageDiagnosticsByRoute[key] || {}

  return {
    generatedAt: new Date().toISOString(),
    route: clone(state.route),
    routeKey: key,
    pageDiagnostics: clone(pageDiagnostics),
    recentRequests: clone(state.recentRequests),
    environment: {
      location: globalThis.location ? globalThis.location.href : "",
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    },
  }
}

function notify() {
  state.updatedAt = new Date().toISOString()
  const snapshot = getSnapshot()
  for (const listener of listeners) {
    listener(snapshot)
  }
}

export function subscribeDebugState(listener) {
  listeners.add(listener)
  listener(getSnapshot())
  return () => {
    listeners.delete(listener)
  }
}

export function setDebugRouteSnapshot(route) {
  state.route = {
    path: route?.path || "",
    name: route?.name ? String(route.name) : "",
    params: redactSensitive(route?.params || {}),
    query: redactSensitive(route?.query || {}),
  }
  state.routeKey = routeKeyFromRoute(route)
  notify()
}

export function publishCurrentPageDiagnostics(payload) {
  const key = state.routeKey || "unknown"
  state.pageDiagnosticsByRoute[key] = redactSensitive(payload || {})
  notify()
}

export function publishPageDiagnosticsForRoute(routeKey, payload) {
  if (!routeKey) return
  state.pageDiagnosticsByRoute[String(routeKey)] = redactSensitive(payload || {})
  notify()
}

export function clearCurrentPageDiagnostics() {
  const key = state.routeKey || "unknown"
  delete state.pageDiagnosticsByRoute[key]
  notify()
}

export function installDebugFetchTracker() {
  if (fetchTrackerInstalled || typeof window === "undefined") return
  fetchTrackerInstalled = true

  const nativeFetch = window.fetch.bind(window)
  window.fetch = async (input, init = {}) => {
    const method = String(init?.method || "GET").toUpperCase()
    const url = typeof input === "string" ? input : input?.url || "unknown"
    const startedAt = performance.now()

    try {
      const response = await nativeFetch(input, init)
      const durationMs = Math.round(performance.now() - startedAt)
      state.recentRequests.unshift({
        method,
        url,
        status: response.status,
        ok: response.ok,
        durationMs,
        at: new Date().toISOString(),
      })
      state.recentRequests = state.recentRequests.slice(0, MAX_REQUEST_LOGS)
      notify()
      return response
    } catch (error) {
      const durationMs = Math.round(performance.now() - startedAt)
      state.recentRequests.unshift({
        method,
        url,
        status: "network-error",
        ok: false,
        durationMs,
        at: new Date().toISOString(),
        error: String(error?.message || error),
      })
      state.recentRequests = state.recentRequests.slice(0, MAX_REQUEST_LOGS)
      notify()
      throw error
    }
  }
}
