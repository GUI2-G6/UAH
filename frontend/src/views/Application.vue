<template>
  <div class="page">
    <div class="greeting application-hero">
      <div>
        <h1>Applications</h1>
        <p>Hi {{ displayName }}. Keep your job-search updates organized and easy to review.</p>
      </div>
      <div class="hero-copy">
        <p>Scan your Gmail updates, choose the entries you care about, and keep a clean tracked list with update badges.</p>
      </div>
    </div>

    <div class="dashboard">
      <Card class="home-card home-stat-card">
        <template #header><h2>Applied</h2></template>
        <p id="applied" class="kpi-value">{{ summary.applied }}</p>
      </Card>
      <Card class="home-card home-stat-card">
        <template #header><h2>Interviews</h2></template>
        <p id="interviews" class="kpi-value">{{ summary.interview }}</p>
      </Card>
      <Card class="home-card home-stat-card">
        <template #header><h2>Offers</h2></template>
        <p id="offers" class="kpi-value">{{ summary.offer }}</p>
      </Card>
      <Card class="home-card home-stat-card">
        <template #header><h2>Not moving forward</h2></template>
        <p id="rejected" class="kpi-value">{{ summary.rejection }}</p>
      </Card>

      <Card class="home-card home-card--wide application-scan-card">
        <template #header>
          <h2 id="tracked-applications">Scan for updates</h2>
          <p class="scan-meta">Last scan: {{ lastRefreshed ? formatTimestamp(lastRefreshed) : 'Not scanned yet' }}</p>
          <p v-if="submittedSessionCount !== null" class="scan-meta">Saved sessions available for analytics: {{ submittedSessionCount }}</p>
          <p v-if="scanDiagnostics" class="scan-meta">
            Included ATS: {{ scanDiagnostics.included_by_ats }} · LinkedIn apply: {{ scanDiagnostics.included_by_linkedin_apply }} · Excluded non-career: {{ scanDiagnostics.excluded_by_noncareer_source }} · Excluded promo/news: {{ scanDiagnostics.excluded_by_negative_intent }}
          </p>
        </template>

        <div class="scan-primary-actions section-block">
          <button class="submit-btn is-primary" type="button" :disabled="loading || !gmailConnected" @click="scanNow('new')">
            {{ loading && scanMode === 'new' ? 'Scanning…' : 'Scan new updates' }}
          </button>
          <button class="submit-btn is-primary" type="button" :disabled="loading || !gmailConnected" @click="scanNow('saved')">
            {{ loading && scanMode === 'saved' ? 'Scanning…' : 'Scan saved tracked applications' }}
          </button>
          <button class="submit-btn" type="button" :disabled="trackingBusy || !selectedVisibleCount" @click="saveSelectedTracked">
            {{ trackingBusy ? 'Saving…' : `Save selected for tracking (${selectedVisibleCount})` }}
          </button>
          <button class="submit-btn is-ghost" type="button" @click="showAdvancedOptions = !showAdvancedOptions">
            {{ showAdvancedOptions ? 'Hide advanced scan options' : 'Show advanced scan options' }}
          </button>
        </div>

        <p v-if="!gmailConnected" class="empty-state-copy">
          Connect Gmail in Settings to run scans.
          <button class="submit-btn" type="button" @click="$router.push('/settings')">Open Settings</button>
        </p>
        <p v-else-if="error" class="empty-state-copy">{{ error }}</p>

        <section v-if="showAdvancedOptions" class="advanced-options-panel">
          <div class="advanced-field">
            <label for="scan-query">Keyword search</label>
            <input id="scan-query" v-model.trim="scanQuery" type="text" placeholder="Try: interview OR offer OR application" class="scan-input" :disabled="!gmailConnected">
          </div>
          <div class="advanced-field">
            <label for="scan-window">Time window</label>
            <select id="scan-window" v-model.number="scanNewerThanDays" class="scan-input" :disabled="!gmailConnected">
              <option :value="14">Last 14 days</option>
              <option :value="30">Last 30 days</option>
              <option :value="45">Last 45 days</option>
              <option :value="90">Last 90 days</option>
              <option :value="180">Last 180 days</option>
              <option :value="365">Last 365 days</option>
              <option :value="730">Last 2 years</option>
              <option :value="1825">Last 5 years</option>
              <option :value="3650">Last 10 years</option>
            </select>
          </div>
          <div class="advanced-field">
            <label for="scan-custom-days">Custom days</label>
            <input id="scan-custom-days" v-model.number="scanCustomDays" type="number" min="1" max="36500" class="scan-input" placeholder="Any number of days" :disabled="!gmailConnected">
          </div>
          <div class="advanced-field">
            <label for="scan-max-results">Max results</label>
            <select id="scan-max-results" v-model.number="scanMaxResults" class="scan-input" :disabled="!gmailConnected">
              <option :value="10">10 results</option>
              <option :value="20">20 results</option>
              <option :value="50">50 results</option>
              <option :value="100">100 results</option>
            </select>
          </div>
          <div class="advanced-field">
            <label for="source-strictness">Source strictness</label>
            <select id="source-strictness" v-model="sourceStrictness" class="scan-input" :disabled="!gmailConnected">
              <option value="strict_career_domains">Strict career domains</option>
              <option value="hybrid_job_language">Hybrid (allow strong job language)</option>
            </select>
          </div>
          <div class="advanced-field">
            <label for="linkedin-mode">LinkedIn handling</label>
            <select id="linkedin-mode" v-model="linkedinMode" class="scan-input" :disabled="!gmailConnected">
              <option value="linkedin_apply_only">LinkedIn application emails only</option>
              <option value="linkedin_all_jobish">Most LinkedIn job-ish emails</option>
              <option value="linkedin_off">Exclude LinkedIn</option>
            </select>
          </div>
        </section>
      </Card>

      <Card class="home-card home-card--wide application-results-card">
        <template #header>
          <h2>Candidate updates</h2>
          <p class="scan-meta">{{ feedItems.length }} update{{ feedItems.length === 1 ? '' : 's' }} in this view</p>
        </template>

        <div class="results-toolbar section-block">
          <select id="app-filter" v-model="selectedStatusFilter">
            <option value="interview">Interview</option>
            <option value="offer">Offer</option>
            <option value="rejection">Not moving forward</option>
            <option value="applied">Applied</option>
            <option value="unknown">Needs review</option>
          </select>
          <div class="toolbar-actions">
            <button class="submit-btn is-ghost" type="button" :disabled="!feedItems.length" @click="selectAllVisible">Select all visible</button>
            <button class="submit-btn is-ghost" type="button" :disabled="!selectedCount" @click="clearSelection">Clear selection</button>
          </div>
        </div>

        <p v-if="loading" class="empty-state-copy">Running scan...</p>
        <p v-else-if="!feedItems.length" class="empty-state-copy">No updates in this filter yet.</p>

        <Card
          v-for="(app, index) in feedItems"
          :key="`${app.subject}-${index}`"
          variant="minimal"
          class="home-application-card"
        >
          <label class="candidate-checkbox">
            <input type="checkbox" :checked="isSelected(app.selection_key)" @change="toggleSelection(app.selection_key)">
            <span>Select for tracking</span>
          </label>
          <Application :application="app" />
          <div class="suppression-actions">
            <button type="button" class="submit-btn is-primary" @click="openMostRecentEmail(app)">Open email</button>
            <button type="button" class="submit-btn" @click="suppressMessage(app)">Hide this update</button>
            <button type="button" class="submit-btn" @click="suppressThread(app)">Hide similar emails</button>
          </div>
        </Card>
      </Card>

      <Card class="home-card home-card--wide tracked-panel">
        <template #header>
          <h2>Saved tracked applications</h2>
          <p class="scan-meta">These stay saved and will show update badges after refresh.</p>
          <button class="submit-btn is-ghost" type="button" :disabled="trackingBusy" @click="loadTrackedApplications">Refresh list</button>
        </template>

        <p v-if="!trackedApplications.length" class="empty-state-copy">You have not saved any tracked applications yet.</p>
        <article v-for="row in trackedApplications" :key="`tracked-${row.id}`" class="tracked-row">
          <div>
            <p class="tracked-title">{{ row.job_title || 'Untitled role' }} · {{ row.company || 'Unknown company' }}</p>
            <p class="tracked-meta">{{ row.source_type }} · {{ row.latest_status || 'needs review' }}</p>
          </div>
          <div class="tracked-actions">
            <span v-if="row.has_new_update" class="update-tick">New update</span>
            <button v-if="row?.metadata?.gmail_open_url_direct || row?.metadata?.gmail_open_url_fallback" type="button" class="submit-btn is-primary" @click="openMostRecentEmail(row.metadata)">Open email</button>
            <button type="button" class="submit-btn" @click="markTrackedSeen(row.id)">Mark as reviewed</button>
            <button type="button" class="submit-btn is-danger" @click="untrack(row.id)">Remove from tracked</button>
          </div>
        </article>
      </Card>

      <Card class="home-card home-card--wide suppression-panel">
        <template #header>
          <h2>Manage hidden updates</h2>
          <p class="scan-meta">Use this if you want to restore something you previously hid.</p>
        </template>
        <button type="button" class="submit-btn is-ghost" @click="toggleSuppressions">
          {{ suppressionsOpen ? 'Hide hidden updates list' : 'Show hidden updates list' }}
        </button>
        <div v-if="suppressionsOpen" class="suppression-list">
          <p v-if="!suppressions.length" class="empty-state-copy">No hidden updates.</p>
          <article v-for="row in suppressions" :key="row.id" class="suppression-row">
            <p>{{ row.scope }} · {{ row.subject_key || row.source_id || 'suppression' }}</p>
            <button type="button" class="submit-btn" @click="unsuppress(row.id)">Restore</button>
          </article>
        </div>
      </Card>
    </div>
  </div>
</template>

<script>
    import Card from "../components/Card.vue"
    import Application from "../components/Application.vue"
    import { authedFetch, getCurrentUser } from "../lib/auth.js";
    import { readGmailScanCache, resolveGmailConnectionStatus, runGmailScan, subscribeGmailUpdates, summarizeGmailResults, listGmailSuppressions, createGmailSuppression, removeGmailSuppression } from "../lib/gmailUpdates.js"
    import { showToast } from "../services/toastService";

    export default{
        data() {
            return {
                user: getCurrentUser(),
                summary: summarizeGmailResults([]),
                loading: false,
                error: '',
                lastRefreshed: '',
                gmailConnected: Boolean(getCurrentUser()?.gmail_refresh_token),
                unsubscribeUpdates: null,
                selectedStatusFilter: 'unknown',
                applications: [],
                submittedSessionCount: null,
                scanDiagnostics: null,
                scanQuery: '',
                scanNewerThanDays: 45,
                scanMaxResults: 20,
                scanCustomDays: null,
                sourceStrictness: 'strict_career_domains',
                linkedinMode: 'linkedin_apply_only',
                suppressions: [],
                suppressionsOpen: false,
                selectedKeys: {},
                trackingBusy: false,
                trackedApplications: [],
                showAdvancedOptions: false,
                scanMode: 'new',
                onUserUpdated: null,
            }
        },
        components: {
            Card,
            Application
        },
    computed: {
        displayName() {
            const first = this.user?.first_name || this.user?.firstName || ""
            const last = this.user?.last_name || this.user?.lastName || ""

            const full = `${first} ${last}`.trim()

            return full || this.user?.email || "User"
        },
        feedItems() {
            const mapped = (this.applications || []).map((item) => ({
                company: item.company_hint || 'Unknown company',
                role: item.subject || 'Untitled update',
                from: item.from || '',
                date: item.date || '',
                snippet: item.snippet || '',
                status: item.status_bucket || item.detected_status || 'unknown',
                detected_status: item.detected_status || 'unknown',
                subject: item.subject || '',
                source_id: item.source_id || '',
                selection_key: item.source_id ? `gmail:${item.source_id}` : `thread:${item.thread_key || `${item.subject}|${item.from}`}`,
                company_hint: item.company_hint || '',
                sender_domain: item.sender_domain || '',
                subject_key: item.subject_key || '',
                company_key: item.company_key || '',
                thread_key: item.thread_key || '',
                gmail_open_url_direct: item.gmail_open_url_direct || '',
                gmail_open_url_fallback: item.gmail_open_url_fallback || '',
                tracking_source: item.tracking_source || 'matched',
                confidence: item.confidence || 'high',
            }))
            return mapped.filter((item) => String(item.status).toLowerCase() === this.selectedStatusFilter)
        },
        selectedVisibleCount() {
            return this.feedItems.filter((row) => this.isSelected(row.selection_key)).length
        },
        selectedCount() {
            return Object.values(this.selectedKeys).filter(Boolean).length
        },
    },
    mounted() {
        this.onUserUpdated = async () => {
            this.user = getCurrentUser()
            await this.refreshGmailConnected()
        }
        window.addEventListener('uah-user-updated', this.onUserUpdated)
        const cached = readGmailScanCache()
        if (cached) {
            this.applyScanRecord(cached)
            this.gmailConnected = this.gmailConnected || Boolean(cached.gmail_email)
        }
        this.refreshGmailConnected()
        this.loadSuppressions()
        this.loadTrackedApplications()
        this.unsubscribeUpdates = subscribeGmailUpdates((record) => {
            this.applyScanRecord(record)
        })
    },
    beforeUnmount() {
        if (typeof this.unsubscribeUpdates === 'function') {
            this.unsubscribeUpdates()
        }
        if (this.onUserUpdated) {
            window.removeEventListener('uah-user-updated', this.onUserUpdated)
        }
    },
    methods: {
        async refreshGmailConnected(force = false) {
            this.gmailConnected = await resolveGmailConnectionStatus(this.gmailConnected, { force })
        },
        applyScanRecord(record = {}) {
            const results = Array.isArray(record.results) ? record.results : []
            this.summary = summarizeGmailResults(results)
            this.lastRefreshed = record.fetched_at || this.lastRefreshed
            this.applications = results
            this.submittedSessionCount = Number.isFinite(Number(record?.scan_scope?.applied_job_candidates))
                ? Number(record.scan_scope.applied_job_candidates)
                : null
            this.scanDiagnostics = record?.scan_scope && typeof record.scan_scope === 'object'
                ? {
                    included_by_ats: Number(record.scan_scope.included_by_ats || 0),
                    included_by_linkedin_apply: Number(record.scan_scope.included_by_linkedin_apply || 0),
                    excluded_by_noncareer_source: Number(record.scan_scope.excluded_by_noncareer_source || 0),
                    excluded_by_negative_intent: Number(record.scan_scope.excluded_by_negative_intent || 0),
                }
                : null
        },
        formatTimestamp(value) {
            if (!value) return 'Unknown'
            const date = new Date(value)
            return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
        },
        async scanNow(mode = 'new') {
            if (!this.gmailConnected) {
                this.error = 'Gmail is not connected. Open Settings > Service Connections > Gmail Updates.'
                return
            }
            this.scanMode = mode === 'saved' ? 'saved' : 'new'
            this.loading = true
            this.error = ''
            await this.emitAnalyticsEvent('dashboard.scan.started')
            try {
                const record = await runGmailScan({
                    scan_mode: this.scanMode,
                    source_strictness: this.sourceStrictness,
                    linkedin_mode: this.linkedinMode,
                    query: this.scanQuery,
                    newer_than_days: Number(this.scanCustomDays || this.scanNewerThanDays || 45),
                    max_results: this.scanMaxResults,
                })
                this.applyScanRecord(record)
                this.gmailConnected = true
                await this.loadTrackedApplications()
                await this.emitAnalyticsEvent('dashboard.scan.succeeded', {
                    result_count: Number(record?.results?.length || 0),
                })
            } catch (error) {
                const message = String(error?.message || '')
                this.error = message.includes('Gmail not connected')
                    ? 'Gmail is not connected. Open Settings > Service Connections > Gmail Updates.'
                    : (message || 'Could not scan Gmail updates.')
                await this.emitAnalyticsEvent('dashboard.scan.failed', {
                    error: this.error,
                })
            } finally {
                this.loading = false
            }
        },
        async emitAnalyticsEvent(eventType, payload = {}) {
            if (!this.hasSessionAnalyticsContext()) return
            try {
                await authedFetch('/api/apply-sessions/analytics/events', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        event_type: eventType,
                        payload,
                    }),
                })
            } catch {
                // Analytics should never block user workflows
            }
        },
        hasSessionAnalyticsContext() {
            if (Number(this.submittedSessionCount || 0) > 0) return true
            return (this.trackedApplications || []).some((row) => Number(row?.apply_session_id || 0) > 0)
        },
        async loadSuppressions() {
            try {
                this.suppressions = await listGmailSuppressions()
            } catch (error) {
                console.error("Failed loading suppressions", error)
            }
        },
        toggleSuppressions() {
            this.suppressionsOpen = !this.suppressionsOpen
            if (this.suppressionsOpen) this.loadSuppressions()
        },
        async suppressMessage(item) {
            const snapshot = [...this.applications]
            this.removeApplicationBySourceId(item.source_id)
            try {
                await createGmailSuppression({
                    scope: 'message',
                    source_id: item.source_id || null,
                    note: 'Suppressed from Applications view',
                })
                showToast('Update hidden from future scans.', 'success')
                await this.loadSuppressions()
            } catch (error) {
                this.applications = snapshot
                showToast(error?.message || 'Could not hide this update.', 'error')
            }
        },
        async suppressThread(item) {
            const snapshot = [...this.applications]
            this.removeApplicationsByThread(item)
            try {
                await createGmailSuppression({
                    scope: 'thread',
                    from_header: item.from,
                    subject: item.subject,
                    company_hint: item.company_hint || item.company,
                    note: 'Suppressed chain from Applications view',
                })
                showToast('Apply chain hidden from future scans.', 'success')
                await this.loadSuppressions()
            } catch (error) {
                this.applications = snapshot
                showToast(error?.message || 'Could not hide this chain.', 'error')
            }
        },
        async unsuppress(id) {
            try {
                await removeGmailSuppression(id)
                showToast('Suppression removed.', 'success')
                await this.loadSuppressions()
            } catch (error) {
                showToast(error?.message || 'Could not remove suppression.', 'error')
            }
        },
        isSelected(key) {
            return this.selectedKeys[String(key || "")] === true
        },
        toggleSelection(key) {
            const normalized = String(key || '')
            if (!normalized) return
            this.selectedKeys = {
                ...this.selectedKeys,
                [normalized]: !this.selectedKeys[normalized],
            }
        },
        selectAllVisible() {
            const next = { ...this.selectedKeys }
            for (const item of this.feedItems) {
                next[String(item.selection_key)] = true
            }
            this.selectedKeys = next
        },
        clearSelection() {
            this.selectedKeys = {}
        },
        async saveSelectedTracked() {
            const chosenGmail = this.feedItems.filter((row) => this.isSelected(row.selection_key))
            if (!chosenGmail.length) {
                showToast('Select at least one candidate to save.', 'error')
                return
            }
            this.trackingBusy = true
            try {
                const selections = [
                    ...chosenGmail.map((row) => ({
                        source_type: 'gmail',
                        source_ref: row.source_id || row.thread_key,
                        thread_key: row.thread_key || null,
                        company: row.company || row.company_hint || null,
                        job_title: row.role || row.subject || null,
                        latest_status: row.detected_status || row.status || null,
                        metadata: {
                            from: row.from,
                            gmail_open_url_direct: row.gmail_open_url_direct,
                            gmail_open_url_fallback: row.gmail_open_url_fallback,
                        },
                    })),
                ]
                const res = await authedFetch('/api/applications/tracked/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ selections }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.selectedKeys = {}
                showToast(`Tracked applications saved (${Number(data?.created || 0) + Number(data?.updated || 0)}).`, 'success')
                await this.loadTrackedApplications()
            } catch (error) {
                showToast(error?.message || 'Could not save tracked selections.', 'error')
            } finally {
                this.trackingBusy = false
            }
        },
        async loadTrackedApplications() {
            try {
                const res = await authedFetch('/api/applications/tracked')
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.trackedApplications = Array.isArray(data?.tracked_applications) ? data.tracked_applications : []
            } catch (error) {
                console.error('Failed to load tracked applications', error)
                this.trackedApplications = []
            }
        },
        async markTrackedSeen(id) {
            try {
                const res = await authedFetch(`/api/applications/tracked/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'mark_seen' }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                await this.loadTrackedApplications()
            } catch (error) {
                showToast(error?.message || 'Could not mark tracked item as seen.', 'error')
            }
        },
        async untrack(id) {
            try {
                const res = await authedFetch(`/api/applications/tracked/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'untrack' }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                await this.loadTrackedApplications()
            } catch (error) {
                showToast(error?.message || 'Could not untrack item.', 'error')
            }
        },
        removeApplicationBySourceId(sourceId) {
            const id = String(sourceId || '').trim()
            if (!id) return
            this.applications = (this.applications || []).filter((row) => String(row.source_id || '').trim() !== id)
        },
        removeApplicationsByThread(item) {
            const senderDomain = String(item.sender_domain || '').trim()
            const subjectKey = String(item.subject_key || '').trim()
            const companyKey = String(item.company_key || '').trim()
            if (!senderDomain || !subjectKey) return
            this.applications = (this.applications || []).filter((row) => (
                String(row.sender_domain || '').trim() !== senderDomain
                || String(row.subject_key || '').trim() !== subjectKey
                || String(row.company_key || '').trim() !== companyKey
            ))
        },
        openMostRecentEmail(item) {
            const direct = String(item.gmail_open_url_direct || '').trim()
            const fallback = String(item.gmail_open_url_fallback || '').trim()
            const target = direct || fallback
            if (!target) {
                showToast('No email link available for this update yet.', 'error')
                return
            }
            try {
                const opened = window.open(target, '_blank', 'noopener')
                if (!opened && fallback && fallback !== target) {
                    window.open(fallback, '_blank', 'noopener')
                }
            } catch {
                if (fallback) window.open(fallback, '_blank', 'noopener')
            }
        },
    },
        name: "ApplicationView"
    }
</script>

<style scoped src="./css/Home.css"></style>