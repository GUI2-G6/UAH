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
                    </select>
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
                    <Application :application="app" />
                    <div class="suppression-actions">
                        <button type="button" class="submit-btn" @click="suppressMessage(app)">Hide this update</button>
                        <button type="button" class="submit-btn" @click="suppressThread(app)">Hide this chain</button>
                    </div>
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
    import { getCurrentUser } from "../lib/auth.js";
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
                suppressions: [],
                suppressionsOpen: false,
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
                company_hint: item.company_hint || '',
                tracking_source: item.tracking_source || 'matched',
                confidence: item.confidence || 'high',
            }))
            if (this.selectedStatusFilter === 'all') return mapped
            return mapped.filter((item) => String(item.status).toLowerCase() === this.selectedStatusFilter)
        }
    },
    mounted() {
        const cached = readGmailScanCache()
        if (cached) {
            this.applyScanRecord(cached)
            this.gmailConnected = this.gmailConnected || Boolean(cached.gmail_email)
        }
        this.loadSuppressions()
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
                    newer_than_days: this.scanNewerThanDays,
                    max_results: this.scanMaxResults,
                    include_provisional: this.scanIncludeProvisional,
                })
                this.applyScanRecord(record)
                this.gmailConnected = true
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
            try {
                await createGmailSuppression({
                    scope: 'message',
                    source_id: item.source_id || null,
                    note: 'Suppressed from Applications view',
                })
                showToast('Update hidden from future scans.', 'success')
                await this.loadSuppressions()
            } catch (error) {
                showToast(error?.message || 'Could not hide this update.', 'error')
            }
        },
        async suppressThread(item) {
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
    },
        name: "ApplicationView"
    }
</script>

<style scoped src="./css/Home.css"></style>