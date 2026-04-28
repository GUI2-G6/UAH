<template>
    <div class="page">
        <div class="greeting">
            <h1>Application</h1>
            <p>Good afternoon, {{displayName}}! Review ATS updates matched to your submitted applications.</p>
        </div>
        <div class="dashboard">
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Applications</h2>
                </template>
                <p id="applied">{{ summary.applied }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Interviews</h2>
                </template>
                <p id="interviews">{{ summary.interview }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Offers</h2>
                </template>
                <p id="offers">{{ summary.offer }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Rejected</h2>
                </template>
                <p id="rejected">{{ summary.rejection }}</p>
            </Card>
            <Card class="home-card home-card--wide">
                <template #header>
                    <h2 id="tracked-applications">Tracked Applications</h2>
                    <p v-if="lastRefreshed" class="scan-meta">Last scan: {{ formatTimestamp(lastRefreshed) }}</p>
                    <p v-if="submittedSessionCount !== null" class="scan-meta">Submitted sessions available for matching: {{ submittedSessionCount }}</p>
                    <button class="submit-btn" type="button" :disabled="loading" @click="scanNow">
                        {{ loading ? 'Scanning…' : 'Run Gmail scan' }}
                    </button>
                    <input v-model.trim="scanQuery" type="text" placeholder="Keyword query override" class="scan-input">
                    <select v-model.number="scanNewerThanDays" class="scan-input">
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
                    <input v-model.number="scanCustomDays" type="number" min="1" max="36500" class="scan-input" placeholder="Custom days">
                    <select v-model.number="scanMaxResults" class="scan-input">
                        <option :value="10">10 results</option>
                        <option :value="20">20 results</option>
                        <option :value="50">50 results</option>
                        <option :value="100">100 results</option>
                    </select>
                    <label class="scan-toggle">
                        <input v-model="scanIncludeProvisional" type="checkbox">
                        Include provisional ATS updates
                    </label>
                    <select id="app-filter" v-model="selectedStatusFilter">
                        <option value="all">All statuses</option>
                        <option value="interview">Interview</option>
                        <option value="offer">Offer</option>
                        <option value="rejection">Rejection</option>
                        <option value="applied">Applied</option>
                        <option value="unknown">Unknown</option>
                    </select>
                    <button class="submit-btn" type="button" :disabled="trackingBusy || !selectedCount" @click="saveSelectedTracked">
                        {{ trackingBusy ? 'Saving…' : `Save selected (${selectedCount})` }}
                    </button>
                </template>

                <p v-if="!gmailConnected" class="empty-state-copy">Connect Gmail in Settings to view matched ATS updates here.</p>
                <p v-else-if="loading" class="empty-state-copy">Running Gmail scan...</p>
                <p v-else-if="error" class="empty-state-copy">{{ error }}</p>
                <p v-else-if="!feedItems.length" class="empty-state-copy">No matched ATS updates yet for this filter.</p>

                <Card 
                    v-for="(app, index) in feedItems"
                    :key="`${app.subject}-${index}`"
                    variant="minimal"
                    class="home-application-card"
                >
                    <label class="candidate-checkbox">
                        <input type="checkbox" :checked="isSelected(app.selection_key)" @change="toggleSelection(app.selection_key)">
                        <span>Select candidate</span>
                    </label>
                    <Application :application="app" />
                    <div class="suppression-actions">
                        <button type="button" class="submit-btn" @click="openMostRecentEmail(app)">Open email</button>
                        <button type="button" class="submit-btn" @click="suppressMessage(app)">Hide this update</button>
                        <button type="button" class="submit-btn" @click="suppressThread(app)">Hide this chain</button>
                    </div>
                </Card>
                <div class="saved-candidate-panel">
                    <h3>Saved Job Candidates</h3>
                    <p class="scan-meta">Select saved jobs to include in tracked applications.</p>
                    <article v-for="row in savedJobCandidates" :key="`saved-candidate-${row.saved_job_id || row.id}`" class="saved-candidate-row">
                        <label class="candidate-checkbox">
                            <input type="checkbox" :checked="isSelected(`saved:${row.saved_job_id || row.id}`)" @change="toggleSelection(`saved:${row.saved_job_id || row.id}`)">
                            <span>{{ row.title || row.name || 'Untitled role' }} · {{ row.company || 'Unknown company' }}</span>
                        </label>
                    </article>
                    <p v-if="!savedJobCandidates.length" class="empty-state-copy">No saved jobs available yet.</p>
                </div>
                <Card class="home-card home-card--wide">
                    <template #header>
                        <h2>Saved Tracked Applications</h2>
                        <p class="scan-meta">Selections persist across refresh and devices.</p>
                        <button class="submit-btn" type="button" :disabled="trackingBusy" @click="loadTrackedApplications">
                            Refresh tracked list
                        </button>
                    </template>
                    <p v-if="!trackedApplications.length" class="empty-state-copy">No tracked applications saved yet.</p>
                    <article v-for="row in trackedApplications" :key="`tracked-${row.id}`" class="tracked-row">
                        <div>
                            <p class="tracked-title">{{ row.job_title || 'Untitled role' }} · {{ row.company || 'Unknown company' }}</p>
                            <p class="tracked-meta">{{ row.source_type }} · {{ row.latest_status || 'unknown' }}</p>
                        </div>
                        <div class="tracked-actions">
                            <span v-if="row.has_new_update" class="update-tick">Updated</span>
                            <button v-if="row?.metadata?.gmail_open_url_direct || row?.metadata?.gmail_open_url_fallback" type="button" class="submit-btn" @click="openMostRecentEmail(row.metadata)">Open email</button>
                            <button type="button" class="submit-btn" @click="markTrackedSeen(row.id)">Mark seen</button>
                            <button type="button" class="submit-btn" @click="untrack(row.id)">Untrack</button>
                        </div>
                    </article>
                </Card>
                <div class="suppression-manager">
                    <button type="button" class="submit-btn" @click="toggleSuppressions">
                        {{ suppressionsOpen ? 'Hide suppressed updates' : 'View suppressed updates' }}
                    </button>
                    <div v-if="suppressionsOpen" class="suppression-list">
                        <p v-if="!suppressions.length" class="empty-state-copy">No suppressed updates yet.</p>
                        <article v-for="row in suppressions" :key="row.id" class="suppression-row">
                            <p>{{ row.scope }} · {{ row.subject_key || row.source_id || 'suppression' }}</p>
                            <button type="button" class="submit-btn" @click="unsuppress(row.id)">Unhide</button>
                        </article>
                    </div>
                </div>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from "../components/Card.vue"
    import Application from "../components/Application.vue"
    import { authedFetch, getCurrentUser } from "../lib/auth.js";
    import { readGmailScanCache, runGmailScan, subscribeGmailUpdates, summarizeGmailResults, listGmailSuppressions, createGmailSuppression, removeGmailSuppression } from "../lib/gmailUpdates.js"
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
                selectedStatusFilter: 'all',
                applications: [],
                submittedSessionCount: null,
                scanQuery: '',
                scanNewerThanDays: 45,
                scanMaxResults: 20,
                scanIncludeProvisional: true,
                scanCustomDays: null,
                suppressions: [],
                suppressionsOpen: false,
                selectedKeys: {},
                trackingBusy: false,
                trackedApplications: [],
                savedJobCandidates: [],
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
            if (this.selectedStatusFilter === 'all') return mapped
            return mapped.filter((item) => String(item.status).toLowerCase() === this.selectedStatusFilter)
        },
        selectedCount() {
            return Object.values(this.selectedKeys).filter(Boolean).length
        },
    },
    mounted() {
        const cached = readGmailScanCache()
        if (cached) {
            this.applyScanRecord(cached)
            this.gmailConnected = this.gmailConnected || Boolean(cached.gmail_email)
        }
        this.loadSuppressions()
        this.loadSavedJobCandidates()
        this.loadTrackedApplications()
        this.unsubscribeUpdates = subscribeGmailUpdates((record) => {
            this.applyScanRecord(record)
        })
    },
    beforeUnmount() {
        if (typeof this.unsubscribeUpdates === 'function') {
            this.unsubscribeUpdates()
        }
    },
    methods: {
        applyScanRecord(record = {}) {
            const results = Array.isArray(record.results) ? record.results : []
            this.summary = summarizeGmailResults(results)
            this.lastRefreshed = record.fetched_at || this.lastRefreshed
            this.applications = results
            this.submittedSessionCount = Number.isFinite(Number(record?.scan_scope?.applied_job_candidates))
                ? Number(record.scan_scope.applied_job_candidates)
                : null
        },
        formatTimestamp(value) {
            if (!value) return 'Unknown'
            const date = new Date(value)
            return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
        },
        async scanNow() {
            this.loading = true
            this.error = ''
            try {
                const record = await runGmailScan({
                    query: this.scanQuery,
                    newer_than_days: Number(this.scanCustomDays || this.scanNewerThanDays || 45),
                    max_results: this.scanMaxResults,
                    include_provisional: this.scanIncludeProvisional,
                })
                this.applyScanRecord(record)
                this.gmailConnected = true
                await this.loadTrackedApplications()
            } catch (error) {
                this.error = error?.message || 'Could not scan Gmail updates.'
            } finally {
                this.loading = false
            }
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
        async loadSavedJobCandidates() {
            try {
                const res = await authedFetch('/api/jobs/saved?page=1&page_size=100')
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.savedJobCandidates = Array.isArray(data?.saved_jobs) ? data.saved_jobs : []
            } catch (error) {
                console.error('Failed to load saved job candidates', error)
                this.savedJobCandidates = []
            }
        },
        async saveSelectedTracked() {
            const chosenGmail = this.feedItems.filter((row) => this.isSelected(row.selection_key))
            const chosenSaved = (this.savedJobCandidates || []).filter((row) => this.isSelected(`saved:${row.saved_job_id || row.id}`))
            if (!chosenGmail.length && !chosenSaved.length) {
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
                    ...chosenSaved.map((row) => ({
                        source_type: 'saved_job',
                        source_ref: String(row.saved_job_id || row.id),
                        thread_key: null,
                        company: row.company || null,
                        job_title: row.title || row.name || null,
                        latest_status: 'saved',
                        metadata: {
                            saved_job_id: row.saved_job_id || row.id,
                            provider: row.provider || '',
                            provider_job_id: row.provider_job_id || '',
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