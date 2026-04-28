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
                    <button class="submit-btn" type="button" :disabled="loading || !gmailConnected" @click="scanNow">
                        {{ loading ? 'Scanning…' : 'Run Gmail scan' }}
                    </button>
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
                </Card>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from "../components/Card.vue"
    import Application from "../components/Application.vue"
    import { getCurrentUser } from "../lib/auth.js";
    import { readGmailScanCache, runGmailScan, subscribeGmailUpdates, summarizeGmailResults } from "../lib/gmailUpdates.js"

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
            }))
            if (this.selectedStatusFilter === 'all') return mapped
            return mapped.filter((item) => String(item.status).toLowerCase() === this.selectedStatusFilter)
        }
    },
    mounted() {
        const cached = readGmailScanCache()
        if (cached) this.applyScanRecord(cached)
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
                const record = await runGmailScan()
                this.applyScanRecord(record)
                this.gmailConnected = true
            } catch (error) {
                this.error = error?.message || 'Could not scan Gmail updates.'
            } finally {
                this.loading = false
            }
        },
    },
        name: "ApplicationView"
    }
</script>

<style scoped src="./css/Home.css"></style>