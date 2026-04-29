<template>
  <div class="page home-page">
    <div class="greeting">
      <h1>Home</h1>
      <p>{{ greetingLine }}</p>
      <p class="scan-meta">Dashboard updated {{ relativeTime(homeRefreshedAt) }}</p>
    </div>

    <div class="dashboard">
      <Card v-for="metric in kpiCards" :key="metric.key" class="home-card home-stat-card">
        <template #header><h2>{{ metric.title }}</h2></template>
        <template #tab><h3>{{ metric.brief }}</h3></template>
        <p :id="metric.key" class="kpi-value">{{ metric.value }}</p>
      </Card>

      <Card class="home-card home-card--quick-actions">
        <template #header><h2>Quick Actions</h2></template>
        <div class="quick-actions">
          <button type="button" class="submit-btn" :disabled="quickActionBusy || !gmailConnected" @click="runQuickScan">
            {{ quickActionBusy ? 'Scanning…' : 'Run Gmail Scan' }}
          </button>
          <button type="button" class="submit-btn" @click="openRoute('/application')">Open Application Feed</button>
          <button type="button" class="submit-btn" @click="openRoute('/settings')">
            {{ gmailConnected ? 'Manage Gmail Connection' : 'Connect Gmail' }}
          </button>
        </div>
        <p v-if="!gmailConnected" class="empty-state-copy">Gmail scan is disabled until Gmail is linked in Settings.</p>
      </Card>

      <Card class="home-card home-card--insights">
        <template #header><h2>Insights</h2></template>
        <ul class="brief-list">
          <li v-for="item in insights" :key="item">{{ item }}</li>
        </ul>
      </Card>

      <Card class="home-card home-card--health">
        <template #header><h2>Health</h2></template>
        <article class="health-row">
          <h3>Gmail Link</h3>
          <p>{{ gmailConnected ? 'Connected and ready for scans.' : 'Not connected. Scan actions are unavailable.' }}</p>
        </article>
        <article class="health-row">
          <h3>API Status</h3>
          <p>{{ backendHealthBrief }}</p>
        </article>
      </Card>

      <Card class="home-card home-card--wide">
        <template #header>
          <div class="timeline-header-row">
            <h2 id="tracked-applications">Recent Timeline</h2>
            <button
              v-if="timelineCanExpand"
              type="button"
              class="submit-btn timeline-toggle"
              @click="timelineExpanded = !timelineExpanded"
            >
              {{ timelineExpanded ? 'Show less' : `Show ${timelineItems.length - 3} more` }}
            </button>
          </div>
          <p class="scan-meta">Showing brief updates only (latest {{ timelineItems.length }})</p>
        </template>
        <p v-if="!timelineItems.length" class="empty-state-copy">No recent activity yet.</p>
        <article
          v-for="(entry, index) in visibleTimelineItems"
          :key="`${entry.type}-${entry.id || index}`"
          class="timeline-row"
        >
          <div>
            <p class="timeline-title">{{ entry.title }}</p>
            <p class="timeline-meta">{{ entry.brief }}</p>
          </div>
          <button type="button" class="submit-btn" @click="openTimelineEntry(entry)">Open</button>
        </article>
      </Card>
    </div>
  </div>
</template>

<script>
import Card from "../components/Card.vue"
import { authedFetch, getCurrentUser } from "../lib/auth.js"
import { readGmailScanCache, resolveGmailConnectionStatus, runGmailScan, subscribeGmailUpdates, summarizeGmailResults } from "../lib/gmailUpdates.js"

export default{
  data() {
    return {
      user: getCurrentUser(),
      gmailConnected: Boolean(getCurrentUser()?.gmail_refresh_token),
      gmailResults: [],
      gmailSummary: summarizeGmailResults([]),
      trackedApplications: [],
      analyticsSummary: null,
      backendStatus: null,
      homeRefreshedAt: new Date().toISOString(),
      lastScanAt: null,
      quickActionBusy: false,
      timelineExpanded: false,
      unsubscribeUpdates: null,
      onUserUpdated: null,
    }
  },
  components: {
    Card,
  },
    computed: {
      displayName() {
        const first = this.user?.first_name || this.user?.firstName || ""
        const last = this.user?.last_name || this.user?.lastName || ""
        const full = `${first} ${last}`.trim()
        return full || this.user?.email || "User"
      },
      greetingLine() {
        const pending = Number(this.analyticsSummary?.stale_submissions_count || 0)
        const updates = Number(this.analyticsSummary?.tracked_updates_count || 0)
        return `Welcome back, ${this.displayName}. ${updates} tracked updates and ${pending} follow-up reminders are waiting.`
      },
      kpiCards() {
        return [
          {
            key: "action-required",
            title: "Action Required",
            value: Number(this.gmailSummary.action_required || 0),
            brief: "Updates that need a follow-up",
          },
          {
            key: "new-updates",
            title: "New Updates",
            value: Number(this.analyticsSummary?.tracked_updates_count || 0),
            brief: "Tracked roles with unseen changes",
          },
          {
            key: "last-scan",
            title: "Time Since Last Scan",
            value: this.lastScanAt ? this.relativeTime(this.lastScanAt) : "Never scanned",
            brief: this.lastScanAt ? this.formatTimestamp(this.lastScanAt) : "Run your first Gmail scan",
          },
        ]
      },
      insights() {
        const items = []
        const actionRequired = Number(this.gmailSummary.action_required || 0)
        const stale = Number(this.analyticsSummary?.stale_submissions_count || 0)
        const trackedUpdates = Number(this.analyticsSummary?.tracked_updates_count || 0)
        if (actionRequired > 0) items.push(`${actionRequired} updates need action from your inbox feed.`)
        if (stale > 0) items.push(`${stale} submitted applications have had no recent follow-up.`)
        if (trackedUpdates > 0) items.push(`${trackedUpdates} tracked roles have unseen updates.`)
        if (!items.length) items.push("No urgent items right now. Keep scans running weekly for new signals.")
        return items.slice(0, 4)
      },
      timelineItems() {
        const allowedTimelineEvents = new Set([
          "dashboard.scan.started",
          "dashboard.scan.succeeded",
          "dashboard.scan.failed",
          "dashboard.quick_action.scan_clicked",
          "dashboard.quick_action.mark_applied_started",
          "dashboard.quick_action.mark_applied_completed",
        ])
        const tracked = (this.trackedApplications || []).slice(0, 6).map((row) => ({
          type: "tracked",
          id: row.id,
          title: `${row.company || "Unknown company"} - ${row.job_title || "Untitled role"}`,
          brief: `${row.latest_status || "unknown"} · ${this.relativeTime(row.updated_at || row.last_update_at)}`,
          route: "/application",
          eventType: "dashboard.timeline.item_opened",
          sessionId: row.apply_session_id || null,
        }))
        const events = Array.isArray(this.analyticsSummary?.recent_events)
          ? this.analyticsSummary.recent_events
              .filter((row) => allowedTimelineEvents.has(String(row?.event_type || "")))
              .map((row) => ({
              type: "event",
              id: row.id,
              title: String(row.event_type || "event").replaceAll(".", " "),
              brief: this.relativeTime(row.created_at),
              route: "/analytics",
              eventType: "dashboard.timeline.analytics_event_opened",
              sessionId: Number(row.payload?.session_id || 0) || null,
            }))
          : []
        return [...tracked, ...events].slice(0, 8)
      },
      visibleTimelineItems() {
        if (this.timelineExpanded) return this.timelineItems
        return this.timelineItems.slice(0, 3)
      },
      timelineCanExpand() {
        return this.timelineItems.length > 3
      },
      backendHealthBrief() {
        const status = String(this.backendStatus?.overall || this.backendStatus?.status || "unknown")
        if (status === "healthy" || status === "ok") return "Backend services are healthy."
        if (status === "degraded") return "Backend is degraded. Expect slower updates."
        if (status === "error") return "Backend reported errors. Retry scans later."
        return "Backend health not available yet."
      },
    },
  async mounted() {
    this.onUserUpdated = async () => {
      this.user = getCurrentUser()
      await this.refreshGmailConnected()
      this.homeRefreshedAt = new Date().toISOString()
    }
    window.addEventListener("uah-user-updated", this.onUserUpdated)
    const cached = readGmailScanCache()
    if (cached) {
      this.gmailConnected = this.gmailConnected || Boolean(cached.gmail_email)
      this.gmailResults = Array.isArray(cached.results) ? cached.results : []
      this.gmailSummary = summarizeGmailResults(this.gmailResults)
      this.lastScanAt = cached.fetched_at || null
    }
    await this.refreshGmailConnected()
    await Promise.all([
      this.loadTrackedApplications(),
      this.loadAnalyticsSummary(),
      this.loadBackendStatus(),
    ])
    this.unsubscribeUpdates = subscribeGmailUpdates((record = {}) => {
      this.gmailResults = Array.isArray(record.results) ? record.results : []
      this.gmailSummary = summarizeGmailResults(this.gmailResults)
      this.gmailConnected = this.gmailConnected || Boolean(record.gmail_email)
      this.lastScanAt = record.fetched_at || this.lastScanAt
      this.homeRefreshedAt = new Date().toISOString()
    })
    this.emitAnalyticsEvent("dashboard.home.viewed")
  },
  beforeUnmount() {
    if (typeof this.unsubscribeUpdates === "function") this.unsubscribeUpdates()
    if (this.onUserUpdated) window.removeEventListener("uah-user-updated", this.onUserUpdated)
  },
  methods: {
    async refreshGmailConnected(force = false) {
      this.gmailConnected = await resolveGmailConnectionStatus(this.gmailConnected, { force })
    },
    async loadTrackedApplications() {
      try {
        const res = await authedFetch("/api/applications/tracked")
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
        this.trackedApplications = Array.isArray(data?.tracked_applications) ? data.tracked_applications : []
      } catch {
        this.trackedApplications = []
      }
      this.homeRefreshedAt = new Date().toISOString()
    },
    async loadAnalyticsSummary() {
      try {
        const res = await authedFetch("/api/apply-sessions/analytics/summary")
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
        this.analyticsSummary = data || null
      } catch {
        this.analyticsSummary = null
      }
      this.homeRefreshedAt = new Date().toISOString()
    },
    async loadBackendStatus() {
      try {
        const res = await fetch("/api/status")
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error("status fetch failed")
        this.backendStatus = data
      } catch {
        this.backendStatus = null
      }
      this.homeRefreshedAt = new Date().toISOString()
    },
    async runQuickScan() {
      if (!this.gmailConnected) return
      this.quickActionBusy = true
      await this.emitAnalyticsEvent("dashboard.quick_action.scan_clicked")
      try {
        const record = await runGmailScan()
        this.gmailResults = Array.isArray(record.results) ? record.results : []
        this.gmailSummary = summarizeGmailResults(this.gmailResults)
        this.gmailConnected = true
        this.lastScanAt = record.fetched_at || new Date().toISOString()
        await Promise.all([this.loadTrackedApplications(), this.loadAnalyticsSummary()])
      } finally {
        this.quickActionBusy = false
        this.homeRefreshedAt = new Date().toISOString()
      }
    },
    async openRoute(path) {
      this.$router.push(path)
    },
    async openTimelineEntry(entry) {
      if (!entry) return
      this.$router.push(entry.route || "/application")
    },
    async emitAnalyticsEvent(eventType, payload = {}, sessionId = null) {
      if (!sessionId && !this.hasSessionAnalyticsContext()) return
      try {
        await authedFetch("/api/apply-sessions/analytics/events", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            event_type: eventType,
            payload: payload || {},
            session_id: sessionId,
          }),
        })
      } catch {
        // Non-blocking analytics path
      }
    },
    hasSessionAnalyticsContext() {
      const counts = this.analyticsSummary?.status_counts || {}
      const total = Number(counts.started || 0)
        + Number(counts.in_progress || 0)
        + Number(counts.submitted || 0)
        + Number(counts.abandoned || 0)
      return total > 0
    },
    relativeTime(value) {
      if (!value) return "just now"
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return "recently"
      const deltaMs = Date.now() - date.getTime()
      const minutes = Math.round(deltaMs / 60000)
      if (minutes <= 1) return "just now"
      if (minutes < 60) return `${minutes} min ago`
      const hours = Math.round(minutes / 60)
      if (hours < 24) return `${hours} hr ago`
      const days = Math.round(hours / 24)
      return `${days} day${days === 1 ? "" : "s"} ago`
    },
    formatTimestamp(value) {
      if (!value) return "Unknown"
      const parsed = new Date(value)
      return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString()
    },
  },
  name: "Home",
}
</script>

<style scoped src="./css/Home.css"></style>